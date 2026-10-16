select
    stock_item_id,
    quantity_on_hand,
    {{ clean_text('bin_location') }}   as bin_location,
    last_stocktake_quantity,
    {{ to_amount('last_cost_price') }} as last_cost_price,
    reorder_level,
    target_stock_level,
    last_edited_when
from {{ source('bronze', 'warehouse_stock_item_holdings') }}
{{ dedup('stock_item_id', 'last_edited_when') }}
