import os

# --- What we pull -----------------------------------------------------------
# Keep this small and editable. Adding a ticker or series later is a
# one-line change here, no schema change required (raw tables are generic).

TICKERS = ["AAPL", "MSFT", "SPY", "^GSPC"]

FRED_SERIES = {
    "FEDFUNDS": "Effective Federal Funds Rate",
    "CPIAUCSL": "CPI, All Urban Consumers (inflation)",
    "UNRATE": "Unemployment Rate",
}

# How many days back to pull on each run. A daily cron only needs a small
# lookback (covers weekends/holidays/late-arriving revisions); the raw
# tables' unique constraints make re-pulling overlapping days a safe no-op
# upsert, not a duplicate.
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "10"))

# --- Secrets / connection ----------------------------------------------------
# All read from environment. Locally: a .env file (see .env.example).
# In CI: GitHub Actions repo secrets. Never hardcode these.

FRED_API_KEY = os.environ.get("FRED_API_KEY")
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL")  # postgres connection string

def require_env():
    missing = [name for name, val in [
        ("FRED_API_KEY", FRED_API_KEY),
        ("SUPABASE_DB_URL", SUPABASE_DB_URL),
    ] if not val]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in .env locally or as GitHub Actions secrets in CI."
        )
