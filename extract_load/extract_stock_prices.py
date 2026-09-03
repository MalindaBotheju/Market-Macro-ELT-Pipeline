"""
Extract step: pull raw daily OHLCV from yfinance for each configured ticker.

Deliberately does NOT clean, rename, or reshape anything beyond flattening
yfinance's dataframe into row dicts. That's the point of ELT: this step's
only job is "get the API's data into our hands," not "make it analysis-ready."
"""
import datetime as dt
import logging

import pandas as pd
import yfinance as yf

from config import TICKERS, LOOKBACK_DAYS

logger = logging.getLogger(__name__)


def extract_stock_prices(tickers=None, lookback_days=None) -> list[dict]:
    tickers = tickers or TICKERS
    lookback_days = lookback_days or LOOKBACK_DAYS

    start = (dt.date.today() - dt.timedelta(days=lookback_days)).isoformat()
    rows: list[dict] = []

    for ticker in tickers:
        logger.info("Pulling %s from yfinance since %s", ticker, start)
        hist = yf.Ticker(ticker).history(start=start, interval="1d")

        if hist.empty:
            logger.warning("No data returned for %s", ticker)
            continue

        for idx, r in hist.iterrows():
            def _num(v):
                return None if pd.isna(v) else float(v)

            rows.append({
                "ticker": ticker,
                "price_date": idx.date().isoformat(),
                "open": _num(r["Open"]),
                "high": _num(r["High"]),
                "low": _num(r["Low"]),
                "close": _num(r["Close"]),
                "volume": None if pd.isna(r["Volume"]) else int(r["Volume"]),
                "source": "yfinance",
            })

    logger.info("Extracted %d raw stock price rows", len(rows))
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = extract_stock_prices()
    print(f"{len(data)} rows extracted")
    if data:
        print(data[0])
