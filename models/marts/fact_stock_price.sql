-- Grain: one row per ticker per trading day.

select
    p.ticker                       as ticker_key,
    p.price_date                   as date_key,
    p.open,
    p.high,
    p.low,
    p.close,
    p.volume,
    p.close - p.open                              as intraday_change,
    round(((p.close - p.open) / nullif(p.open, 0)) * 100, 4) as intraday_change_pct
from {{ ref('stg_stock_prices') }} p
