select
    reading_id,
    contract_id,
    reading_date,
    period_start,
    period_end,
    kwh,
    reading_type
from {{ source('raw_energie', 'releves') }}
