-- Historique SCD2 des clients : versions archivées + version courante
with versions as (
    select customer_id, customer_name, customer_category_id, buying_group_id, delivery_city_id,
           credit_limit, standard_discount_percentage, is_on_credit_hold, payment_days, valid_from, valid_to
    from {{ source('bronze', 'sales_customers_archive') }}
    union all
    select customer_id, customer_name, customer_category_id, buying_group_id, delivery_city_id,
           credit_limit, standard_discount_percentage, is_on_credit_hold, payment_days, valid_from, valid_to
    from {{ source('bronze', 'sales_customers') }}
)
select
    {{ surrogate_key(['customer_id', 'valid_from']) }} as customer_version_id,
    customer_id,
    {{ clean_text('customer_name') }}                  as customer_name,
    customer_category_id,
    buying_group_id,
    delivery_city_id,
    {{ to_amount('credit_limit') }}                    as credit_limit,
    cast(standard_discount_percentage as number(5, 2)) as standard_discount_percentage,
    coalesce(is_on_credit_hold, false)                 as is_on_credit_hold,
    payment_days,
    valid_from,
    valid_to
from versions
where valid_from < valid_to
{{ dedup('customer_id, valid_from', 'valid_to') }}
