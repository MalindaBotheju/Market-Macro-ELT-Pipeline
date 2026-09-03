-- Staging: light cleaning only. Cast types, drop dupes, standardize casing.
-- No business logic, no joins, no aggregation — that belongs in marts.

with source as (
    select * from {{ source('raw', 'raw_stock_prices') }}
),

deduped as (
    select
        upper(trim(ticker))        as ticker,
        price_date::date           as price_date,
        open::numeric              as open,
        high::numeric              as high,
        low::numeric               as low,
        close::numeric             as close,
        volume::bigint             as volume,
        ingested_at,
        row_number() over (
            partition by ticker, price_date
            order by ingested_at desc
        ) as rn
    from source
)

select
    ticker,
    price_date,
    open,
    high,
    low,
    close,
    volume,
    ingested_at
from deduped
where rn = 1
