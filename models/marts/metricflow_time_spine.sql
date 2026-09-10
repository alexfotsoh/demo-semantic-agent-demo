{{ config(materialized='table') }}

with dates as (
    select dateadd(day, seq4(), '2023-01-01'::date) as date_day
    from table(generator(rowcount => 2000))
)
select date_day
from dates
where date_day <= '2028-12-31'