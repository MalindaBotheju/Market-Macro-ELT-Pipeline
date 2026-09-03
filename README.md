# Market vs. Macro — ELT Pipeline

Two free sources → Supabase Postgres (raw) → dbt (curated star schema) →
Power BI. Orchestrated by a daily GitHub Actions cron, running the same
Docker image locally and in CI.

```
yfinance ──┐
           ├─► raw_stock_prices / raw_macro_indicators  (raw, untouched)
FRED    ───┘                │
                             ▼  dbt run + dbt test
              dim_ticker, dim_date, fact_stock_price, fact_macro_indicator
                             │
                             ▼
                          Power BI
```

## 1. One-time setup

### Supabase (data warehouse)
1. Create a free project at supabase.com.
2. Project Settings → Database → Connection string → copy the URI. That's
   your `SUPABASE_DB_URL`. Also note the host/user/password/port/dbname
   separately — dbt's `profiles.yml` wants them split out (see `.env.example`).

### FRED (macro data)
1. Free key, instant: https://fred.stlouisfed.org/docs/api/api_key.html

### Local `.env`
```bash
cp .env.example .env
# fill in FRED_API_KEY, SUPABASE_DB_URL, and the split SUPABASE_DB_* vars
```

### GitHub Actions secrets
In your repo: Settings → Secrets and variables → Actions → New repository
secret. Add all of: `FRED_API_KEY`, `SUPABASE_DB_URL`, `SUPABASE_DB_HOST`,
`SUPABASE_DB_PORT`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`,
`SUPABASE_DB_NAME`.

## 2. Run it locally

```bash
docker build -t market-macro-pipeline .
docker run --rm --env-file .env market-macro-pipeline
```

This runs, in order: extract+load (Python) → `dbt run` → `dbt test`, exactly
as the GitHub Actions job does. If you'd rather run without Docker:

```bash
pip install -r requirements.txt
export $(cat .env | xargs)   # or use direnv/dotenv
python extract_load/run_extract_load.py
dbt run --profiles-dir .
dbt test --profiles-dir .
```

## 3. Turn on the daily cron

Just push this repo to GitHub with the secrets set — `.github/workflows/daily_pipeline.yml`
runs at 07:00 UTC daily and is also triggerable manually from the Actions tab
(`workflow_dispatch`). Nothing else to schedule; there's no separate
orchestrator.

**Two things to know about GitHub's cron**, not this pipeline's fault:
- Scheduled workflows can run a few minutes late during high load — fine for
  a daily job.
- GitHub disables scheduled workflows automatically after 60 days of *repo*
  inactivity (no pushes/commits). Push something occasionally, or trigger
  `workflow_dispatch` manually, to keep it alive.

## 4. Connect Power BI

Power BI Desktop → Get Data → PostgreSQL database → same host/port/dbname as
above, use the Supabase connection details. **Only pick up the curated
tables**: `dim_ticker`, `dim_date`, `fact_stock_price`, `fact_macro_indicator`.
Never point Power BI at the `raw_*` tables — they're an internal staging
area, not meant for BI consumption, and can contain unresolved duplicates
or bad values that `stg_*`/marts have already cleaned up.

Model it as a standard star: both fact tables join to `dim_date` on
`date_key`; `fact_stock_price` also joins to `dim_ticker` on `ticker_key`.

## Why ELT, not ETL

The two extract scripts (`extract_stock_prices.py`, `extract_macro_indicators.py`)
do zero cleaning — they hand back exactly what the API returned, and the
loader drops that straight into `raw_stock_prices` / `raw_macro_indicators`.
All cleaning, deduping, typing, and reshaping into a star schema happens
downstream in dbt (`models/staging` → `models/marts`), against data that's
already landed in the warehouse. That split is the actual point of this
project: previous versions of this stack transformed data *before* loading
it, in Python; here transformation is a distinct, re-runnable,
version-controlled SQL layer that can be tested (`dbt test`) independently
of the extract/load code.

## Extending it

- **New ticker**: add it to `TICKERS` in `extract_load/config.py`.
- **New FRED series**: add its series ID to `FRED_SERIES` in the same file.
- **New mart**: add a `.sql` file under `models/marts/`, and a corresponding
  entry in `models/marts/schema.yml` if you want it tested.

No schema migration is needed for new tickers/series — the raw tables are
generic (`ticker`/`series_id` as plain text columns), so `dbt run` just picks
up the new rows on the next scheduled run.

## Free-tier limits (confirmed, not a concern at this scale)

- Supabase: 500 MB DB cap (this project uses single-digit MB even after
  years of daily runs); 7-day inactivity auto-pause (avoided as long as the
  daily Action keeps running — see the 60-day GitHub caveat above); 5 GB/month
  egress (this pipeline uses KB/day).
- FRED: generous published rate limits, far beyond what 3 daily series pulls need.
