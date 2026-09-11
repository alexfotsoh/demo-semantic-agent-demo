{{ config(materialized='table') }}

with mois as (
    select distinct date_trunc('month', date_day)::date as mois
    from {{ ref('metricflow_time_spine') }}
),

borne as (
    select date_trunc('month', max(period_end))::date as dernier_mois
    from {{ ref('fct_factures') }}
),

contrats as (
    select contract_id, start_date, end_date
    from {{ ref('dim_contrats') }}
)

select
    c.contract_id::varchar || '-' || to_char(m.mois, 'YYYY-MM') as contract_month_id,
    c.contract_id,
    m.mois
from contrats c
cross join borne b
join mois m
    on  m.mois >= date_trunc('month', c.start_date)
    and m.mois <= date_trunc('month', coalesce(c.end_date, b.dernier_mois))
where m.mois <= b.dernier_mois