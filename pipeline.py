import datetime as dt
import os
import warnings
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras
import requests
import yfinance as yf
from dotenv import load_dotenv


warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

# --- 1. CONFIGURATION ---
load_dotenv()

TICKERS = ["AAPL", "MSFT", "SPY", "^GSPC"]
FRED_SERIES = ["FEDFUNDS", "CPIAUCSL", "UNRATE"]
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "45"))
START_DATE = (dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()

FRED_API_KEY = os.getenv("FRED_API_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
SQL_FILE = Path(__file__).parent / "transformations.sql"


# --- 2. SQL PARSER ---
def load_sql_blocks(path: Path) -> dict[str, str]:
    """Parse SQL file into named blocks using '-- @@ block_name' markers."""
    blocks, name = {}, None
    for line in path.read_text().splitlines():
        if line.startswith("-- @@ "):
            name = line[len("-- @@ ") :].strip()
            blocks[name] = []
        elif name:
            blocks[name].append(line)
    return {k: "\n".join(v) for k, v in blocks.items()}


# --- 3. EXTRACT FUNCTIONS ---
def extract_stocks() -> list[tuple]:
    stock_rows = []
    for ticker in TICKERS:
        history = yf.Ticker(ticker).history(start=START_DATE, interval="1d")
        for date, row in history.iterrows():
            stock_rows.append(
                (
                    ticker,
                    date.date().isoformat(),
                    None if pd.isna(row["Open"]) else float(row["Open"]),
                    None if pd.isna(row["High"]) else float(row["High"]),
                    None if pd.isna(row["Low"]) else float(row["Low"]),
                    None if pd.isna(row["Close"]) else float(row["Close"]),
                    None if pd.isna(row["Volume"]) else int(row["Volume"]),
                    "yfinance",
                )
            )
    return stock_rows


def extract_macro() -> list[tuple]:
    fred_url = "https://api.stlouisfed.org/fred/series/observations"
    macro_rows = []
    for series_id in FRED_SERIES:
        resp = requests.get(
            fred_url,
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "observation_start": START_DATE,
            },
            timeout=30,
        )
        resp.raise_for_status()
        for obs in resp.json().get("observations", []):
            val = obs["value"]
            macro_rows.append(
                (
                    series_id,
                    obs["date"],
                    None if val == "." else float(val),
                    "fred",
                )
            )
    return macro_rows


# --- 4. MAIN PIPELINE EXECUTION ---
def main():
    if not SUPABASE_DB_URL:
        raise ValueError("SUPABASE_DB_URL environment variable is missing.")

    sql_blocks = load_sql_blocks(SQL_FILE)

    print(f"Pulling data since: {START_DATE}")
    print("Extracting stock price data...")
    stock_rows = extract_stocks()
    print(f"Extracted {len(stock_rows)} stock rows.")

    print("Extracting FRED macroeconomic data...")
    macro_rows = extract_macro()
    print(f"Extracted {len(macro_rows)} macro rows.")

    # Idempotent UPSERT SQL
    stock_sql = """
        INSERT INTO raw_stock_prices (ticker, price_date, open, high, low, close, volume, source)
        VALUES %s
        ON CONFLICT (ticker, price_date) DO UPDATE SET
            open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
            close = EXCLUDED.close, volume = EXCLUDED.volume, source = EXCLUDED.source,
            ingested_at = NOW();
    """

    macro_sql = """
        INSERT INTO raw_macro_indicators (series_id, observation_date, value, source)
        VALUES %s
        ON CONFLICT (series_id, observation_date) DO UPDATE SET
            value = EXCLUDED.value, source = EXCLUDED.source, ingested_at = NOW();
    """

    print("Connecting to Supabase and executing ELT operations...")
    with psycopg2.connect(SUPABASE_DB_URL) as conn:
        with conn.cursor() as cur:
            # Create raw landing tables
            cur.execute(sql_blocks["raw_tables"])

            # Load raw extracted data
            if stock_rows:
                psycopg2.extras.execute_values(cur, stock_sql, stock_rows)
            if macro_rows:
                psycopg2.extras.execute_values(cur, macro_sql, macro_rows)

            # In-database transformations
            cur.execute(sql_blocks["staging"])
            cur.execute(sql_blocks["marts"])

    print("Data loaded and transformed into star schema.")

    # Data Quality Validation
    print("Running quality checks...")
    with psycopg2.connect(SUPABASE_DB_URL) as conn:
        checks = pd.read_sql(sql_blocks["checks"], conn)
        failed = checks[checks["bad_rows"] > 0]
        if not failed.empty:
            raise ValueError(f"Data check(s) failed:\n{failed.to_string(index=False)}")

    print(f"All {len(checks)} quality checks passed! Pipeline complete.")


if __name__ == "__main__":
    main()