-- Dimension client historisée (SCD type 2) : une ligne par version du client
-- (évolution du plafond de crédit, de la catégorie, de la remise...)
select
    h.customer_version_id,
    h.customer_id,
    h.customer_name,
    coalesce(cc.customer_category_name, 'Non renseigné')      as customer_category,
    coalesce(bg.buying_group_name, 'Aucun')                   as buying_group,
    h.credit_limit,
    h.standard_discount_percentage,
    h.is_on_credit_hold,
    h.payment_days,
    h.valid_from,
    case when h.valid_to >= '9999-01-01' then null else h.valid_to end as valid_to,
    h.valid_to >= '9999-01-01'                                as is_current,
    row_number() over (partition by h.customer_id order by h.valid_from) as version_number
from {{ ref('slv_customers_history') }} h
left join {{ ref('slv_customer_categories') }} cc on cc.customer_category_id = h.customer_category_id
left join {{ ref('slv_buying_groups') }} bg on bg.buying_group_id = h.buying_group_id
