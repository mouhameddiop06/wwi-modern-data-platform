select
    customer_id,
    {{ clean_text('customer_name') }}                  as customer_name,
    bill_to_customer_id,
    customer_category_id,
    buying_group_id,
    primary_contact_person_id,
    delivery_method_id,
    delivery_city_id,
    {{ to_amount('credit_limit') }}                    as credit_limit,
    account_opened_date,
    cast(standard_discount_percentage as number(5, 2)) as standard_discount_percentage,
    coalesce(is_on_credit_hold, false)                 as is_on_credit_hold,
    payment_days,
    {{ clean_text('phone_number') }}                   as phone_number,
    lower({{ clean_text('website_url') }})             as website_url,
    {{ clean_text('delivery_postal_code') }}           as delivery_postal_code
from {{ source('bronze', 'sales_customers') }}
{{ dedup('customer_id', 'valid_from') }}
