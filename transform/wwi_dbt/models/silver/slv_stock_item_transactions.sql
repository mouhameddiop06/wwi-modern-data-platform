select
    stock_item_transaction_id,
    stock_item_id,
    transaction_type_id,
    customer_id,
    invoice_id,
    supplier_id,
    purchase_order_id,
    transaction_occurred_when,
    cast(transaction_occurred_when as date) as transaction_date,
    cast(quantity as number(18, 3))         as quantity,
    last_edited_when
from {{ source('bronze', 'warehouse_stock_item_transactions') }}
{{ dedup('stock_item_transaction_id', 'last_edited_when') }}
