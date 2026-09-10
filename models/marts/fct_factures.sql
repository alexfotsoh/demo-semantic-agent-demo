{{ config(materialized='table') }}

select
    f.invoice_id,
    f.contract_id,
    c.customer_id,
    c.offer_code,
    c.region,
    c.is_internal,
    f.invoice_type,
    f.issue_date,
    f.period_start,
    f.period_end,
    f.amount_ht,
    f.amount_ttc,
    f.related_invoice_id
from {{ ref('stg_factures') }} f
left join {{ ref('stg_contrats') }} c
    on f.contract_id = c.contract_id
