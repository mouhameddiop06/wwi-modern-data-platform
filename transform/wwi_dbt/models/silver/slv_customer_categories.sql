select
    customer_category_id,
    {{ clean_text('customer_category_name') }} as customer_category_name
from {{ source('bronze', 'sales_customer_categories') }}
{{ dedup('customer_category_id', 'valid_from') }}
