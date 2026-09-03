"""
Load step: push raw rows into Supabase Postgres as-is.

Uses ON CONFLICT upsert on the natural key of each raw table so re-running
a day (or the lookback window overlapping a previous run) is idempotent —
safe to re-run, no duplicate rows, no manual dedupe logic needed here.
"""
import logging

import psycopg2
import psycopg2.extras

from config import SUPABASE_DB_URL

logger = logging.getLogger(__name__)


def _connect():
    return psycopg2.connect(SUPABASE_DB_URL)


def load_stock_prices(rows: list[dict]) -> int:
    if not rows:
        logger.info("No stock price rows to load")
        return 0

    sql = """
        insert into raw_stock_prices
            (ticker, price_date, open, high, low, close, volume, source)
        values %s
        on conflict (ticker, price_date) do update set
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume,
            source = excluded.source,
            ingested_at = now()
    """
    values = [
        (r["ticker"], r["price_date"], r["open"], r["high"], r["low"],
         r["close"], r["volume"], r["source"])
        for r in rows
    ]
    with _connect() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, values)
        conn.commit()

    logger.info("Loaded/upserted %d stock price rows", len(rows))
    return len(rows)


def load_macro_indicators(rows: list[dict]) -> int:
    if not rows:
        logger.info("No macro indicator rows to load")
        return 0

    sql = """
        insert into raw_macro_indicators
            (series_id, observation_date, value, source)
        values %s
        on conflict (series_id, observation_date) do update set
            value = excluded.value,
            source = excluded.source,
            ingested_at = now()
    """
    values = [
        (r["series_id"], r["observation_date"], r["value"], r["source"])
        for r in rows
    ]
    with _connect() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, values)
        conn.commit()

    logger.info("Loaded/upserted %d macro indicator rows", len(rows))
    return len(rows)


def ensure_raw_tables_exist():
    """Runs the raw DDL. Safe to call every time (all statements are
    CREATE TABLE/INDEX IF NOT EXISTS)."""
    with open("sql/create_raw_tables.sql") as f:
        ddl = f.read()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    logger.info("Ensured raw tables exist")
