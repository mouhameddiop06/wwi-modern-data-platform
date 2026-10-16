-- Grain : une ligne de commande client
select
    ol.order_line_id,
    ol.order_id,
    o.order_date,
    o.expected_delivery_date,
    o.customer_id,
    ol.stock_item_id,
    o.salesperson_person_id               as salesperson_id,
    ol.quantity,
    ol.picked_quantity,
    ol.unit_price,
    ol.tax_rate,
    ol.amount_excluding_tax,
    o.is_undersupply_backordered,
    o.backorder_order_id is not null      as has_backorder,
    cast(ol.picking_completed_when as date) as picking_completed_date
from {{ ref('slv_order_lines') }} ol
join {{ ref('slv_orders') }} o on o.order_id = ol.order_id
