-- One row per calendar day covering the full range seen across both sources.
-- Built with generate_series so it has no gaps, even on days a source
-- didn't publish (e.g. weekends for stocks, monthly cadence for some FRED
-- series) -- Power BI can still join and show blanks rather than missing rows.

with bounds as (
    select
        least(
            (select min(price_date) from {{ ref('stg_stock_prices') }}),
            (select min(observation_date) from {{ ref('stg_macro_indicators') }})
        ) as min_date,
        greatest(
            (select max(price_date) from {{ ref('stg_stock_prices') }}),
            (select max(observation_date) from {{ ref('stg_macro_indicators') }})
        ) as max_date
),

spine as (
    select generate_series(min_date, max_date, interval '1 day')::date as date_day
    from bounds
)

select
    date_day                                  as date_key,
    date_day,
    extract(year from date_day)::int          as year,
    extract(month from date_day)::int         as month,
    extract(day from date_day)::int           as day,
    extract(isodow from date_day)::int        as iso_day_of_week,
    (extract(isodow from date_day) < 6)       as is_weekday
from spine
