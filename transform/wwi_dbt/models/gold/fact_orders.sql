{{ config(
    materialized='incremental',
    unique_key='order_line_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns'
) }}

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
    cast(ol.picking_completed_when as date) as picking_completed_date,
    greatest(ol.last_edited_when, o.last_edited_when) as last_edited_when
from {{ ref('slv_order_lines') }} ol
join {{ ref('slv_orders') }} o on o.order_id = ol.order_id
{% if is_incremental() %}
where greatest(ol.last_edited_when, o.last_edited_when) >
      (select coalesce(max(last_edited_when), '1900-01-01'::timestamp_ntz) from {{ this }})
{% endif %}
