select
    purchase_order_id,
    supplier_id,
    order_date,
    expected_delivery_date,
    delivery_method_id,
    contact_person_id,
    {{ clean_text('supplier_reference') }} as supplier_reference,
    coalesce(is_order_finalized, false)    as is_order_finalized,
    last_edited_when
from {{ source('bronze', 'purchasing_purchase_orders') }}
{{ dedup('purchase_order_id', 'last_edited_when') }}
