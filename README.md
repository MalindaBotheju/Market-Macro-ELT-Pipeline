# Market vs. Macro — ELT Pipeline

Two free sources → Supabase Postgres (raw) → dbt (curated star schema) →
Metabase dashboard. Orchestrated by a daily GitHub Actions cron, running the
same Docker image locally and in CI.

```
yfinance ──┐
           ├─► raw_stock_prices / raw_macro_indicators  (raw, untouched)
FRED    ───┘                │
                             ▼  dbt run + dbt test
              dim_ticker, dim_date, fact_stock_price, fact_macro_indicator
                             │
                             ▼
                          Metabase
```

## BI layer: Metabase, not Power BI

The original plan called for Power BI. In practice, Power BI Desktop only
runs on Windows, and connecting Power BI Service to a self-hosted Postgres
database (like Supabase) requires an On-premises Data Gateway — which is
*also* Windows-only software. Since this project runs on Linux, that would
have meant standing up a Windows VM just to view a dashboard.

Metabase is free, open-source, connects to Postgres natively with no
gateway, and runs as a single Docker container — a better fit for this
stack than fighting an OS mismatch. The architecture is otherwise unchanged:
the curated star schema is the deliverable, and any BI tool (Power BI,
Metabase, Looker Studio) can sit on top of it equally well.

## 1. One-time setup

### Supabase (data warehouse)
1. Create a free project at supabase.com.
2. **Use the Session Pooler connection, not the direct connection.** Go to
   Project Settings → Database → Connect → Connection String, and select
   **Session pooler** under Connection Method. The direct connection
   (`db.<ref>.supabase.co:5432`) is IPv6-only, and most home networks and
   Docker setups don't have IPv6 egress — you'll get a
   `Network is unreachable` error if you try it. The pooler host looks like
   `aws-0-<region>.pooler.supabase.com`, the username is
   `postgres.<project-ref>` (note the dot), and the port shown will be
   whatever the Session pooler tab displays (commonly 5432 on the pooler
   host — different from the direct connection's 5432).
3. Note the host, port, user, password, and dbname separately — dbt's
   `profiles.yml` wants them split out (see `.env.example`).

### FRED (macro data)
1. Free key, instant: https://fred.stlouisfed.org/docs/api/api_key.html

### Local `.env`
```bash
cp .env.example .env
# fill in FRED_API_KEY, SUPABASE_DB_URL (the pooler URI), and the split
# SUPABASE_DB_* vars — all using the pooler host, not the direct one
```

### GitHub Actions secrets
In your repo: Settings → Secrets and variables → Actions → New repository
secret. Add all of: `FRED_API_KEY`, `SUPABASE_DB_URL`, `SUPABASE_DB_HOST`,
`SUPABASE_DB_PORT`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`,
`SUPABASE_DB_NAME` — same pooler-based values as your local `.env`.

`LOOKBACK_DAYS` does **not** need to be a secret — it's not sensitive, and
the default of `45` is already hardcoded in `extract_load/config.py`.

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

Push this repo to GitHub with the secrets set — `.github/workflows/daily_pipeline.yml`
runs at 07:00 UTC daily and is also triggerable manually from the Actions tab
(`workflow_dispatch`). Nothing else to schedule; there's no separate
orchestrator.

**Two things to know about GitHub's cron**, not this pipeline's fault:
- Scheduled workflows can run a few minutes late during high load — fine for
  a daily job.
- GitHub disables scheduled workflows automatically after 60 days of *repo*
  inactivity (no pushes/commits). Push something occasionally, or trigger
  `workflow_dispatch` manually, to keep it alive.

## 4. Connect Metabase

```bash
docker run -d -p 3000:3000 --name metabase metabase/metabase
```

Open `http://localhost:3000`, walk through the setup wizard, and when
prompted to add a database choose **PostgreSQL**:
- Host/port/dbname/user/password: the same **Session pooler** values from
  your `.env`
- **Turn on "Use a secure connection (SSL)"** with SSL mode `require` —
  Supabase requires SSL, and leaving this off will hang or fail the
  connection.

Once connected, browse to the `public` schema (not `auth`, `extensions`,
`realtime`, `storage`, or `vault` — those are Supabase's internal system
schemas, not yours) and confirm all 6 tables are visible.

**Only build charts on the curated tables**: `dim_ticker`, `dim_date`,
`fact_stock_price`, `fact_macro_indicator`. Never build on the `raw_*`
tables — they're an internal staging area, not meant for BI consumption.
If you want to enforce this in the tool itself rather than by convention,
go to Admin → Table Metadata, open each `raw_*` table, and mark it Hidden.

**Note on Metabase's cached filter values**: Metabase snapshots the list of
distinct values for filter dropdowns when it first scans your database. If
you add new tickers or FRED series later, the filter picker won't show them
until you re-scan. Fix: Admin → Databases → your database → "Sync database
schema" then "Re-scan field values."

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

The loader is also idempotent: both raw tables have a unique constraint on
their natural key (`ticker, price_date` and `series_id, observation_date`),
and the loader uses `ON CONFLICT ... DO UPDATE`. Re-running the pipeline, or
widening the lookback window so it re-pulls overlapping dates, never
produces duplicate rows — it just refreshes the existing ones.

## Extending it

- **New ticker**: add it to `TICKERS` in `extract_load/config.py`.
- **New FRED series**: add its series ID to `FRED_SERIES` in the same file.
  Note the cadence — daily series (like `FEDFUNDS`) show up within days;
  monthly series (like `UNRATE`, `CPIAUCSL`) can lag their period end by
  several weeks, which is why `LOOKBACK_DAYS` defaults to 45 rather than a
  tighter window.
- **New mart**: add a `.sql` file under `models/marts/`, and a corresponding
  entry in `models/marts/schema.yml` if you want it tested.

No schema migration is needed for new tickers/series — the raw tables are
generic (`ticker`/`series_id` as plain text columns), so `dbt run` just picks
up the new rows on the next scheduled run.

## Watch out for scale mismatches in charts

`^GSPC` (the S&P 500 index, trading in the thousands) and the individual
stock tickers (trading in the hundreds) don't share a readable axis — same
issue affects `CPIAUCSL` (an index around 330) versus `UNRATE`/`FEDFUNDS`
(percentages around 4-5). Metabase's "split y-axis when necessary" setting
doesn't reliably auto-split more than two series. The practical fix used
throughout this project's dashboard: filter mismatched-scale series into
separate single-metric charts rather than forcing them onto one shared axis.

## Free-tier limits (confirmed, not a concern at this scale)

- Supabase: 500 MB DB cap (this project uses single-digit MB even after
  years of daily runs, and a one-time full-year backfill via a temporarily
  widened `LOOKBACK_DAYS` still stays under 1 MB); 7-day inactivity
  auto-pause (avoided as long as the daily Action keeps running — see the
  60-day GitHub caveat above); 5 GB/month egress (this pipeline uses
  KB/day).
- FRED: generous published rate limits, far beyond what a handful of daily
  series pulls need.

## Dashboard

The finished Metabase dashboard ("Market vs Macro Overview") includes:
- KPI cards: latest SPY close, Fed Funds rate, unemployment rate, CPI
- A multi-ticker closing-price line chart (AAPL, MSFT, SPY — `^GSPC`
  excluded from this one specifically due to the scale mismatch above)
- Individual trend lines for Fed Funds rate, unemployment rate, and CPI
- A bar chart and pie chart comparing average trading volume across tickers
  (also excluding `^GSPC` for the same scale reason)

*(Add a screenshot of the finished dashboard here.)*