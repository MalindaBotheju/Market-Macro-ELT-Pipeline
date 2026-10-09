# Market & Macroeconomic ELT Pipeline

[![Daily ELT Pipeline](https://github.com/MalindaBotheju/Market-Macro-ELT-Pipeline/actions/workflows/daily_elt.yml/badge.svg)](https://github.com/MalindaBotheju/Market-Macro-ELT-Pipeline/actions/workflows/daily_elt.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=flat&logo=postgresql&logoColor=white)](https://supabase.com/)
[![Metabase](https://img.shields.io/badge/Metabase-BI%20Dashboard-509EE3?style=flat&logo=metabase&logoColor=white)](https://www.metabase.com/)

An automated, cloud-hosted ELT (Extract, Load, Transform) data pipeline that extracts daily market equities and macroeconomic indicators, transforms raw data into a Star Schema data warehouse on **Supabase (PostgreSQL)**, and presents live financial analytics through an interactive **Metabase** BI dashboard.

---

## 📊 Live Dashboard Preview

| Top Section: Key Metrics & Equities | Bottom Section: Index & Macro Trends |
| :---: | :---: |
| ![Dashboard Top Panel](docs/dashboard_1.png) | ![Dashboard Bottom Panel](docs/dashboard_2.png) |

---

## 🏗️ Architecture & Data Flow


```

┌─────────────────────────┐      ┌──────────────────────────┐      ┌──────────────────────────┐
│  Data Sources           │      │  GitHub Actions          │      │  Supabase (PostgreSQL)   │
│  • Yahoo Finance (Stocks)│ ────►│  • Orchestration Runner  │ ────►│  • Raw Landing Tables    │
│  • FRED API (Macro)     │      │  • Scheduled Cron Run    │      │  • Staging Views         │
└─────────────────────────┘      └──────────────────────────┘      │  • Star Schema Marts     │
└────────────┬─────────────┘
│
▼
┌──────────────────────────┐
│  Metabase BI Dashboard   │
│  • Interactive Analytics │
│  • Scalar KPI Cards      │
└──────────────────────────┘

```

1. **Extract & Load**: Python pipeline (`yfinance`, FRED API) extracts market metrics (`^GSPC`, `SPY`, `AAPL`, `MSFT`) and macro indicators (`FEDFUNDS`, `UNRATE`) and loads raw payloads into Supabase landing tables.
2. **Transform**: SQL staging views and DDL build a dimensional Star Schema (`fact_stock_price`, `fact_macro_indicator`, `dim_ticker`, `dim_date`).
3. **Orchestrate**: GitHub Actions triggers automated execution daily at market close using encrypted repository secrets.
4. **Data Quality**: Automated SQL data checks verify key integrity and detect null fields post-transformation.
5. **Visualize**: Metabase executes targeted SQL queries to power scalar KPI cards and asset trend charts.

---

## 🗄️ Data Warehouse Architecture (Star Schema)

### Dimension Tables
* **`dim_ticker`**: Holds unique asset identifiers (`ticker_key`, `ticker_name`).
* **`dim_date`**: Calendar reference dimensions (`date_key`, `year`, `month`, `day`, `quarter`).

### Fact Tables
* **`fact_stock_price`**: Daily market transactions (`ticker_key`, `date_key`, `open`, `high`, `low`, `close`, `volume`, `source`).
* **`fact_macro_indicator`**: Macroeconomic observation metrics (`series_id`, `date_key`, `value`, `source`).

---

## 📁 Project Structure

```text
Market-Macro-ELT-Pipeline/
├── .github/
│   └── workflows/
│       └── daily_elt.yml        # GitHub Actions scheduled workflow
├── docs/
│   ├── dashboard_1.png          # Top panel dashboard screenshot
│   └── dashboard_2.png          # Bottom panel dashboard screenshot
├── pipeline.py                  # Extraction & ingestion Python script
├── transform.sql                # Staging, dimensional modeling, & DQ checks
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation

```

---

## 🚀 Local Setup & Pipeline Execution

### 1. Prerequisites

* Python 3.10+
* Supabase PostgreSQL database
* Docker Desktop
* Node.js / `npx` (for live public tunneling)

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
SUPABASE_DB_URL=postgresql://user:password@host:5432/postgres
FRED_API_KEY=your_fred_api_key

```

### 3. Run Pipeline

```bash
# Create virtual environment (if not created)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run full ELT pipeline
python pipeline.py

```

---

## 🖥️ Dashboard Hosting & Public Demos

### 1. Start Metabase via Docker

**First Time Setup:**
To create and launch a new Metabase container on port `3000`:

```bash
docker run -d -p 3000:3000 --name metabase metabase/metabase

```

**Starting an Existing Container:**
If you have already created the Metabase container, reuse your existing setup without losing dashboard configurations:

```bash
docker start metabase

```

Navigating to `http://localhost:3000` allows you to access the dashboard or connect to your Supabase instance.

### 2. Generate Live Public HTTPS Link (Cloudflare Tunnel)

To share the dashboard live with recruiters or interviewers without cloud hosting fees:

```bash
npx cloudflared tunnel --url http://localhost:3000

```

This generates a temporary HTTPS URL (e.g., `https://<random-subdomain>.trycloudflare.com`) that streams your local Metabase instance publicly while the terminal session remains open.

---

## 🔑 GitHub Actions Deployment

To automate execution, configure these two encrypted secrets in your repository under **Settings > Secrets and variables > Actions**:

* `SUPABASE_DB_URL`
* `FRED_API_KEY`