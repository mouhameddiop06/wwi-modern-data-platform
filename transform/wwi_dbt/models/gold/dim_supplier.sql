select
    s.supplier_id,
    s.supplier_name,
    sc.supplier_category_name    as supplier_category,
    p.full_name                  as primary_contact,
    dm.delivery_method_name      as delivery_method,
    s.delivery_city_id,
    city.city_name               as city,
    city.state_province_name     as state_province,
    city.country_name            as country,
    s.payment_days,
    s.website_url
from {{ ref('slv_suppliers') }} s
left join {{ ref('slv_supplier_categories') }} sc on sc.supplier_category_id = s.supplier_category_id
left join {{ ref('slv_people') }} p on p.person_id = s.primary_contact_person_id
left join {{ ref('slv_delivery_methods') }} dm on dm.delivery_method_id = s.delivery_method_id
left join {{ ref('dim_city') }} city on city.city_id = s.delivery_city_id
