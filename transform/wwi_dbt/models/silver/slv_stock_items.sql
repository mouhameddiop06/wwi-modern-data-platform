-- custom_fields (JSON) : extraction du pays de fabrication
select
    stock_item_id,
    {{ clean_text('stock_item_name') }}                        as stock_item_name,
    supplier_id,
    color_id,
    unit_package_id,
    outer_package_id,
    {{ clean_text('brand') }}                                  as brand,
    {{ clean_text('size') }}                                   as size,
    lead_time_days,
    quantity_per_outer,
    coalesce(is_chiller_stock, false)                          as is_chiller_stock,
    {{ clean_text('barcode') }}                                as barcode,
    cast(tax_rate as number(5, 3))                             as tax_rate,
    {{ to_amount('unit_price') }}                              as unit_price,
    {{ to_amount('recommended_retail_price') }}                as recommended_retail_price,
    cast(typical_weight_per_unit as number(10, 3))             as typical_weight_per_unit,
    try_parse_json(custom_fields):CountryOfManufacture::string as country_of_manufacture
from {{ source('bronze', 'warehouse_stock_items') }}
{{ dedup('stock_item_id', 'valid_from') }}
