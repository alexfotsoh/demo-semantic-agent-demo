select
    invoice_id,
    contract_id,
    invoice_type,
    issue_date,
    period_start,
    period_end,
    amount_ht,
    vat_amount,
    amount_ttc,
    related_invoice_id
from {{ source('raw_energie', 'factures') }}