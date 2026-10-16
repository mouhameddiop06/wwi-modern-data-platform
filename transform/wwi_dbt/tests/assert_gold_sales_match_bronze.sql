-- Réconciliation : le CA TTC de la couche Gold égale celui de la couche Bronze
with bronze as (
    select sum(extended_price) as total from {{ source('bronze', 'sales_invoice_lines') }}
),
gold as (
    select sum(amount_including_tax) as total from {{ ref('fact_sales') }}
)
select bronze.total as bronze_total, gold.total as gold_total
from bronze, gold
where abs(bronze.total - gold.total) > 1
