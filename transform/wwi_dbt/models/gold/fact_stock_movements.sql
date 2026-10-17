{{ config(
    materialized='incremental',
    unique_key='stock_item_transaction_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns'
) }}

-- Grain : un mouvement de stock (entrée fournisseur, sortie client, ajustement)
select
    sit.stock_item_transaction_id,
    sit.transaction_date,
    sit.stock_item_id,
    sit.customer_id,
    sit.supplier_id,
    sit.invoice_id,
    sit.purchase_order_id,
    tt.transaction_type_name   as movement_type,
    sit.quantity,
    case when sit.quantity >= 0 then 'Entrée' else 'Sortie' end as direction,
    sit.last_edited_when
from {{ ref('slv_stock_item_transactions') }} sit
left join {{ ref('slv_transaction_types') }} tt on tt.transaction_type_id = sit.transaction_type_id
{{ incremental_filter('sit.last_edited_when') }}
