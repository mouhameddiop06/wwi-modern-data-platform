-- Historique SCD2 des produits : versions archivées + version courante
-- (SQL Server conserve chaque modification dans Warehouse.StockItems_Archive)
with versions as (
    select stock_item_id, stock_item_name, supplier_id, color_id, brand, size,
           unit_price, recommended_retail_price, tax_rate, valid_from, valid_to
    from {{ source('bronze', 'warehouse_stock_items_archive') }}
    union all
    select stock_item_id, stock_item_name, supplier_id, color_id, brand, size,
           unit_price, recommended_retail_price, tax_rate, valid_from, valid_to
    from {{ source('bronze', 'warehouse_stock_items') }}
)
select
    {{ surrogate_key(['stock_item_id', 'valid_from']) }} as stock_item_version_id,
    stock_item_id,
    {{ clean_text('stock_item_name') }}         as stock_item_name,
    supplier_id,
    color_id,
    {{ clean_text('brand') }}                   as brand,
    {{ clean_text('size') }}                    as size,
    {{ to_amount('unit_price') }}               as unit_price,
    {{ to_amount('recommended_retail_price') }} as recommended_retail_price,
    cast(tax_rate as number(5, 3))              as tax_rate,
    valid_from,
    valid_to
from versions
where valid_from < valid_to   -- ignore les versions vides (modifiées dans la même transaction)
{{ dedup('stock_item_id, valid_from', 'valid_to') }}
