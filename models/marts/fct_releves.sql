{{ config(materialized='table') }}

select
    r.reading_id,
    r.contract_id,
    c.offer_code,
    c.region,
    c.is_internal,
    r.reading_date,
    r.period_start,
    r.reading_type,
    r.kwh
from {{ ref('stg_releves') }} r
left join {{ ref('stg_contrats') }} c
    on r.contract_id = c.contract_id