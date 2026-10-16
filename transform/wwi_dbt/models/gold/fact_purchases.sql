-- Grain : une ligne de bon de commande fournisseur
select
    pol.purchase_order_line_id,
    pol.purchase_order_id,
    po.order_date,
    po.expected_delivery_date,
    po.supplier_id,
    pol.stock_item_id,
    dm.delivery_method_name                                   as delivery_method,
    pol.ordered_outers,
    pol.received_outers,
    pol.ordered_outers * coalesce(si.quantity_per_outer, 1)   as ordered_quantity,
    pol.received_outers * coalesce(si.quantity_per_outer, 1)  as received_quantity,
    pol.expected_unit_price_per_outer,
    cast(pol.ordered_outers * pol.expected_unit_price_per_outer as number(18, 2)) as expected_amount,
    pol.last_receipt_date,
    pol.is_order_line_finalized                               as is_finalized
from {{ ref('slv_purchase_order_lines') }} pol
join {{ ref('slv_purchase_orders') }} po on po.purchase_order_id = pol.purchase_order_id
left join {{ ref('slv_stock_items') }} si on si.stock_item_id = pol.stock_item_id
left join {{ ref('slv_delivery_methods') }} dm on dm.delivery_method_id = po.delivery_method_id
