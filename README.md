# Market vs. Macro — Lightweight ELT Pipeline

A minimal, single-script ELT pipeline that extracts market and economic data, loads raw records into Supabase PostgreSQL, runs SQL transformations directly in the database, and serves data for Metabase reporting.

yfinance ──┐
├─► raw_stock_prices / raw_macro_indicators (Supabase)
FRED     ──┘                  │
▼ transformations.sql
dim_ticker, dim_date, fact_stock_price, fact_macro_indicator
│
▼
Metabase


## Setup & Prerequisites

1. **Supabase Setup**:
   * Create a free project on [Supabase](https://supabase.com).
   * Go to **Project Settings → Database → Connect** and copy the **Session Pooler** string (Port `5432`). Do not use the direct IPv6 connection string.
2. **FRED API Key**:
   * Request a free API key from the [St. Louis Fed API page](https://fred.stlouisfed.org/docs/api/api_key.html).

3. **Environment Configuration**:
   * Copy environment values into your `.env` file:
     ```bash
     FRED_API_KEY=your_key
     SUPABASE_DB_URL=postgresql://postgres.ref:password@aws-0-region.pooler.supabase.com:5432/postgres
     LOOKBACK_DAYS=45
     ```

## Execution

Install dependencies and run the pipeline:

```bash
pip install -r requirements.txt
python pipeline.py
Connecting Metabase
Run Metabase locally:

Bash
docker run -d -p 3000:3000 --name metabase metabase/metabase
Open http://localhost:3000 and add PostgreSQL database using your Session Pooler credentials. Enable SSL mode require.

Build dashboards using curated mart tables (dim_ticker, dim_date, fact_stock_price, fact_macro_indicator). Avoid charting raw tables directly.