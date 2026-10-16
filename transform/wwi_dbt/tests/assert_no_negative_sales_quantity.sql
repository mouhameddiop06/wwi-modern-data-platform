-- Les quantités vendues doivent être positives
select invoice_line_id, quantity
from {{ ref('fact_sales') }}
where quantity <= 0
