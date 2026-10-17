-- Historique des niveaux de stock issu du snapshot dbt (une ligne par version)
select
    dbt_scd_id                                               as stock_version_id,
    stock_item_id,
    quantity_on_hand,
    last_cost_price,
    cast(quantity_on_hand * last_cost_price as number(18, 2)) as stock_value,
    reorder_level,
    target_stock_level,
    dbt_valid_from                                           as valid_from,
    dbt_valid_to                                             as valid_to,
    dbt_valid_to is null                                     as is_current
from {{ ref('snp_stock_item_holdings') }}
