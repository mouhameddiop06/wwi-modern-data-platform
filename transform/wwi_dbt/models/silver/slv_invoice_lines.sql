-- Règles métier :
--   extended_price = montant TTC de la ligne
--   montant HT     = quantité x prix unitaire
select
    invoice_line_id,
    invoice_id,
    stock_item_id,
    package_type_id,
    {{ clean_text('description') }}          as description,
    quantity,
    {{ to_amount('unit_price') }}            as unit_price,
    cast(tax_rate as number(5, 3))           as tax_rate,
    {{ to_amount('quantity * unit_price') }} as amount_excluding_tax,
    {{ to_amount('tax_amount') }}            as tax_amount,
    {{ to_amount('extended_price') }}        as amount_including_tax,
    {{ to_amount('line_profit') }}           as line_profit,
    last_edited_when
from {{ source('bronze', 'sales_invoice_lines') }}
{{ dedup('invoice_line_id', 'last_edited_when') }}
