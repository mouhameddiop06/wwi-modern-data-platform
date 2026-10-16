-- Règle métier : HT + TVA = TTC (tolérance d'un centime)
select invoice_line_id, amount_excluding_tax, tax_amount, amount_including_tax
from {{ ref('fact_sales') }}
where abs(amount_excluding_tax + tax_amount - amount_including_tax) > 0.01
