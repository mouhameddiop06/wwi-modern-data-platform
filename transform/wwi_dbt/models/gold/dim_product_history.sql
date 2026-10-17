-- Dimension produit historisée (SCD type 2) : une ligne par version du produit.
-- Permet d'analyser l'évolution des prix dans le temps.
select
    h.stock_item_version_id,
    h.stock_item_id,
    h.stock_item_name                                         as product_name,
    coalesce(h.brand, 'Sans marque')                          as brand,
    coalesce(c.color_name, 'Non renseignée')                  as color,
    s.supplier_name,
    h.unit_price,
    h.recommended_retail_price,
    h.tax_rate,
    h.valid_from,
    case when h.valid_to >= '9999-01-01' then null else h.valid_to end as valid_to,
    h.valid_to >= '9999-01-01'                                as is_current,
    row_number() over (partition by h.stock_item_id order by h.valid_from) as version_number
from {{ ref('slv_stock_items_history') }} h
left join {{ ref('slv_colors') }} c on c.color_id = h.color_id
left join {{ ref('slv_suppliers') }} s on s.supplier_id = h.supplier_id
