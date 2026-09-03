"""
Entrypoint for the E and L of ELT. Called by:
  - local dev:      python extract_load/run_extract_load.py
  - Docker:         CMD in Dockerfile
  - GitHub Actions: daily cron workflow

Does NOT call dbt. Transform is a separate, explicit step (see Dockerfile /
workflow), which is the whole point of keeping extract+load and transform
decoupled under ELT.
"""
import logging
import sys

from config import require_env
from extract_stock_prices import extract_stock_prices
from extract_macro_indicators import extract_macro_indicators
from load_to_supabase import (
    ensure_raw_tables_exist,
    load_stock_prices,
    load_macro_indicators,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    require_env()
    ensure_raw_tables_exist()

    stock_rows = extract_stock_prices()
    load_stock_prices(stock_rows)

    macro_rows = extract_macro_indicators()
    load_macro_indicators(macro_rows)

    logger.info("Extract+load complete: %d stock rows, %d macro rows",
                len(stock_rows), len(macro_rows))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Extract+load failed")
        sys.exit(1)
