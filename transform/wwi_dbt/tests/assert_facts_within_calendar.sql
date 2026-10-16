-- Toutes les dates de ventes et de commandes doivent être couvertes par dim_date
select 'fact_sales' as source, min(invoice_date) as min_date, max(invoice_date) as max_date
from {{ ref('fact_sales') }}
having min(invoice_date) < (select min(date_day) from {{ ref('dim_date') }})
    or max(invoice_date) > (select max(date_day) from {{ ref('dim_date') }})
