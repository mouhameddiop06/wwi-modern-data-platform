-- Grain : un article (photo du stock actuel)
select
    h.stock_item_id,
    h.quantity_on_hand,
    h.bin_location,
    h.last_stocktake_quantity,
    h.last_cost_price,
    cast(h.quantity_on_hand * h.last_cost_price as number(18, 2)) as stock_value,
    h.reorder_level,
    h.target_stock_level,
    h.quantity_on_hand <= h.reorder_level                         as is_below_reorder_level,
    cast(h.last_edited_when as date)                              as snapshot_date
from {{ ref('slv_stock_item_holdings') }} h
