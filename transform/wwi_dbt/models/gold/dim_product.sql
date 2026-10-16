-- Produit = article de stock (StockItem) enrichi
with groups as (
    select
        sisg.stock_item_id,
        listagg(sg.stock_group_name, ', ') within group (order by sg.stock_group_name) as stock_groups,
        min(sg.stock_group_name) as main_stock_group
    from {{ ref('slv_stock_item_stock_groups') }} sisg
    join {{ ref('slv_stock_groups') }} sg on sg.stock_group_id = sisg.stock_group_id
    group by sisg.stock_item_id
)
select
    si.stock_item_id,
    si.stock_item_name                              as product_name,
    coalesce(si.brand, 'Sans marque')               as brand,
    si.size,
    coalesce(col.color_name, 'Non renseignée')      as color,
    up.package_type_name                            as unit_package,
    op.package_type_name                            as outer_package,
    si.quantity_per_outer,
    si.is_chiller_stock,
    si.lead_time_days,
    si.unit_price,
    si.recommended_retail_price,
    si.tax_rate,
    si.typical_weight_per_unit,
    si.country_of_manufacture,
    coalesce(g.main_stock_group, 'Non classé')      as main_stock_group,
    g.stock_groups,
    si.supplier_id,
    s.supplier_name
from {{ ref('slv_stock_items') }} si
left join {{ ref('slv_colors') }} col on col.color_id = si.color_id
left join {{ ref('slv_package_types') }} up on up.package_type_id = si.unit_package_id
left join {{ ref('slv_package_types') }} op on op.package_type_id = si.outer_package_id
left join {{ ref('slv_suppliers') }} s on s.supplier_id = si.supplier_id
left join groups g on g.stock_item_id = si.stock_item_id
