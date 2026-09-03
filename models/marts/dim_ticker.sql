-- One row per ticker. Static metadata lives here so BI can filter/label
-- without re-deriving it from the fact table every time.

with tickers as (
    select distinct ticker
    from {{ ref('stg_stock_prices') }}
)

select
    ticker as ticker_key,   -- ticker itself is a natural key, no surrogate needed
    ticker,
    case
        when ticker like '^%' then 'Index'
        else 'Equity'
    end as instrument_type
from tickers
