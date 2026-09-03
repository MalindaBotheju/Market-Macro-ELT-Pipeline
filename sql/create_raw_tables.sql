-- Raw layer: untouched API output, loaded as-is. No cleaning, no types beyond
-- what's needed to store the payload. This is intentional under ELT: raw
-- tables are the audit trail, transforms happen downstream in dbt.

create table if not exists raw_stock_prices (
    id              bigserial primary key,
    ticker          text not null,
    price_date      date not null,
    open            numeric,
    high            numeric,
    low             numeric,
    close           numeric,
    volume          bigint,
    source          text not null default 'yfinance',
    ingested_at     timestamptz not null default now(),
    unique (ticker, price_date)
);

create table if not exists raw_macro_indicators (
    id              bigserial primary key,
    series_id       text not null,       -- e.g. FEDFUNDS, CPIAUCSL, UNRATE
    observation_date date not null,
    value           numeric,             -- FRED sends "." for missing; loader stores NULL
    source          text not null default 'fred',
    ingested_at     timestamptz not null default now(),
    unique (series_id, observation_date)
);

-- Index to make dbt's incremental / date-range reads on raw fast.
create index if not exists idx_raw_stock_prices_date on raw_stock_prices (price_date);
create index if not exists idx_raw_macro_indicators_date on raw_macro_indicators (observation_date);
