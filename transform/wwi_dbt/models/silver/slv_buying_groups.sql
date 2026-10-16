select
    buying_group_id,
    {{ clean_text('buying_group_name') }} as buying_group_name
from {{ source('bronze', 'sales_buying_groups') }}
{{ dedup('buying_group_id', 'valid_from') }}
