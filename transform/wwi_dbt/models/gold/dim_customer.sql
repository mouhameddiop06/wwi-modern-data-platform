select
    c.customer_id,
    c.customer_name,
    c.bill_to_customer_id,
    bill.customer_name                          as bill_to_customer_name,
    coalesce(cc.customer_category_name, 'Non renseigné') as customer_category,
    coalesce(bg.buying_group_name, 'Aucun')     as buying_group,
    p.full_name                                 as primary_contact,
    dm.delivery_method_name                     as delivery_method,
    c.delivery_city_id,
    city.city_name                              as city,
    city.state_province_name                    as state_province,
    city.sales_territory,
    city.country_name                           as country,
    c.credit_limit,
    c.standard_discount_percentage,
    c.payment_days,
    c.is_on_credit_hold,
    c.account_opened_date
from {{ ref('slv_customers') }} c
left join {{ ref('slv_customers') }} bill on bill.customer_id = c.bill_to_customer_id
left join {{ ref('slv_customer_categories') }} cc on cc.customer_category_id = c.customer_category_id
left join {{ ref('slv_buying_groups') }} bg on bg.buying_group_id = c.buying_group_id
left join {{ ref('slv_people') }} p on p.person_id = c.primary_contact_person_id
left join {{ ref('slv_delivery_methods') }} dm on dm.delivery_method_id = c.delivery_method_id
left join {{ ref('dim_city') }} city on city.city_id = c.delivery_city_id
