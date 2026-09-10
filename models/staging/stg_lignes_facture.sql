select
    line_id,
    invoice_id,
    line_type,
    kwh,
    unit_price,
    amount_ht
from {{ source('raw_energie', 'lignes_facture') }}