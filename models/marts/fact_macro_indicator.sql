-- Grain: one row per macro series per observation day. Kept "long" (series_id
-- as a column, not pivoted into one column per indicator) so adding a new
-- FRED series later needs zero schema change -- Power BI pivots it if needed.

select
    m.observation_date             as date_key,
    m.series_id,
    m.value
from {{ ref('stg_macro_indicators') }} m
