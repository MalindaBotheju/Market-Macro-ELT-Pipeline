with source as (
    select * from {{ source('raw', 'raw_macro_indicators') }}
),

deduped as (
    select
        upper(trim(series_id))         as series_id,
        observation_date::date         as observation_date,
        value::numeric                 as value,
        ingested_at,
        row_number() over (
            partition by series_id, observation_date
            order by ingested_at desc
        ) as rn
    from source
)

select
    series_id,
    observation_date,
    value,
    ingested_at
from deduped
where rn = 1
