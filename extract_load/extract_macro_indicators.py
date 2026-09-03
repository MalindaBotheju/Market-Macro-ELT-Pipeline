"""
Extract step: pull raw observations from the FRED API for each configured
series. Same philosophy as the stock extractor: hand back what FRED gave us,
values and all (including FRED's own "." missing-value sentinel converted to
None so it round-trips into a numeric column, nothing fancier than that).
"""
import datetime as dt
import logging

import requests

from config import FRED_SERIES, FRED_API_KEY, LOOKBACK_DAYS

logger = logging.getLogger(__name__)

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def extract_macro_indicators(series_ids=None, lookback_days=None) -> list[dict]:
    series_ids = series_ids or list(FRED_SERIES.keys())
    lookback_days = lookback_days or LOOKBACK_DAYS
    start = (dt.date.today() - dt.timedelta(days=lookback_days)).isoformat()

    rows: list[dict] = []

    for series_id in series_ids:
        logger.info("Pulling %s from FRED since %s", series_id, start)
        resp = requests.get(FRED_URL, params={
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "observation_start": start,
        }, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        for obs in payload.get("observations", []):
            value = obs["value"]
            rows.append({
                "series_id": series_id,
                "observation_date": obs["date"],
                "value": None if value == "." else float(value),
                "source": "fred",
            })

    logger.info("Extracted %d raw macro indicator rows", len(rows))
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = extract_macro_indicators()
    print(f"{len(data)} rows extracted")
    if data:
        print(data[0])
