-- @@ raw_tables
CREATE TABLE IF NOT EXISTS raw_stock_prices (
    ticker VARCHAR(10) NOT NULL,
    price_date DATE NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    source VARCHAR(20),
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (ticker, price_date)
);

CREATE TABLE IF NOT EXISTS raw_macro_indicators (
    series_id VARCHAR(20) NOT NULL,
    observation_date DATE NOT NULL,
    value NUMERIC,
    source VARCHAR(20),
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (series_id, observation_date)
);

-- @@ staging
DROP VIEW IF EXISTS stg_stock_prices CASCADE;
DROP VIEW IF EXISTS stg_macro_indicators CASCADE;

CREATE VIEW stg_stock_prices AS
SELECT
    UPPER(TRIM(ticker)) AS ticker,
    price_date,
    open,
    high,
    low,
    close,
    volume,
    source
FROM raw_stock_prices
WHERE price_date IS NOT NULL AND ticker IS NOT NULL;

CREATE VIEW stg_macro_indicators AS
SELECT
    UPPER(TRIM(series_id)) AS series_id,
    observation_date,
    value,
    source
FROM raw_macro_indicators
WHERE observation_date IS NOT NULL AND series_id IS NOT NULL;

-- @@ marts
DROP TABLE IF EXISTS fact_stock_price CASCADE;
DROP TABLE IF EXISTS fact_macro_indicator CASCADE;
DROP TABLE IF EXISTS dim_ticker CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;

CREATE TABLE dim_ticker (
    ticker_key VARCHAR(10) PRIMARY KEY,
    ticker_name VARCHAR(50)
);

INSERT INTO dim_ticker (ticker_key, ticker_name)
VALUES
    ('AAPL', 'Apple Inc.'),
    ('MSFT', 'Microsoft Corporation'),
    ('SPY', 'SPDR S&P 500 ETF Trust'),
    ('^GSPC', 'S&P 500 Index')
ON CONFLICT (ticker_key) DO NOTHING;

CREATE TABLE dim_date (
    date_key DATE PRIMARY KEY,
    year INT,
    month INT,
    day INT,
    quarter INT
);

INSERT INTO dim_date (date_key, year, month, day, quarter)
SELECT DISTINCT
    price_date AS date_key,
    EXTRACT(YEAR FROM price_date) AS year,
    EXTRACT(MONTH FROM price_date) AS month,
    EXTRACT(DAY FROM price_date) AS day,
    EXTRACT(QUARTER FROM price_date) AS quarter
FROM stg_stock_prices
ON CONFLICT (date_key) DO NOTHING;

INSERT INTO dim_date (date_key, year, month, day, quarter)
SELECT DISTINCT
    observation_date AS date_key,
    EXTRACT(YEAR FROM observation_date) AS year,
    EXTRACT(MONTH FROM observation_date) AS month,
    EXTRACT(DAY FROM observation_date) AS day,
    EXTRACT(QUARTER FROM observation_date) AS quarter
FROM stg_macro_indicators
ON CONFLICT (date_key) DO NOTHING;

CREATE TABLE fact_stock_price (
    ticker_key VARCHAR(10) REFERENCES dim_ticker(ticker_key),
    date_key DATE REFERENCES dim_date(date_key),
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    source VARCHAR(20),
    PRIMARY KEY (ticker_key, date_key)
);

INSERT INTO fact_stock_price (ticker_key, date_key, open, high, low, close, volume, source)
SELECT ticker, price_date, open, high, low, close, volume, source
FROM stg_stock_prices
ON CONFLICT (ticker_key, date_key) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume,
    source = EXCLUDED.source;

CREATE TABLE fact_macro_indicator (
    series_id VARCHAR(20),
    date_key DATE REFERENCES dim_date(date_key),
    value NUMERIC,
    source VARCHAR(20),
    PRIMARY KEY (series_id, date_key)
);

INSERT INTO fact_macro_indicator (series_id, date_key, value, source)
SELECT series_id, observation_date, value, source
FROM stg_macro_indicators
ON CONFLICT (series_id, date_key) DO UPDATE SET
    value = EXCLUDED.value,
    source = EXCLUDED.source;

-- @@ checks
SELECT 'null_tickers' AS check_name, COUNT(*) AS bad_rows FROM fact_stock_price WHERE ticker_key IS NULL
UNION ALL
SELECT 'null_stock_dates', COUNT(*) FROM fact_stock_price WHERE date_key IS NULL
UNION ALL
SELECT 'null_macro_dates', COUNT(*) FROM fact_macro_indicator WHERE date_key IS NULL;