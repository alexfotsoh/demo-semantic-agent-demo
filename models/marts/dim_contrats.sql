{{ config(materialized='table') }}

select
    contract_id,
    customer_id,
    offer_code,
    region,
    start_date,
    end_date,
    estimated_annual_kwh,
    is_internal
from {{ ref('stg_contrats') }}
