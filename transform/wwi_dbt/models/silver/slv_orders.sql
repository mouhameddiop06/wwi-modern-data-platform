select
    order_id,
    customer_id,
    salesperson_person_id,
    picked_by_person_id,
    contact_person_id,
    backorder_order_id,
    order_date,
    expected_delivery_date,
    coalesce(is_undersupply_backordered, false) as is_undersupply_backordered,
    picking_completed_when,
    last_edited_when
from {{ source('bronze', 'sales_orders') }}
{{ dedup('order_id', 'last_edited_when') }}
