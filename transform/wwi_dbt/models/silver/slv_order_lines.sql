select
    order_line_id,
    order_id,
    stock_item_id,
    package_type_id,
    {{ clean_text('description') }}          as description,
    quantity,
    coalesce(picked_quantity, 0)             as picked_quantity,
    {{ to_amount('unit_price') }}            as unit_price,
    cast(tax_rate as number(5, 3))           as tax_rate,
    {{ to_amount('quantity * unit_price') }} as amount_excluding_tax,
    picking_completed_when,
    last_edited_when
from {{ source('bronze', 'sales_order_lines') }}
{{ dedup('order_line_id', 'last_edited_when') }}
