-- Coordonnées bancaires exclues (données sensibles, inutiles à l'analyse)
select
    supplier_id,
    {{ clean_text('supplier_name') }}        as supplier_name,
    supplier_category_id,
    primary_contact_person_id,
    delivery_method_id,
    delivery_city_id,
    {{ clean_text('supplier_reference') }}   as supplier_reference,
    payment_days,
    {{ clean_text('phone_number') }}         as phone_number,
    lower({{ clean_text('website_url') }})   as website_url,
    {{ clean_text('delivery_postal_code') }} as delivery_postal_code
from {{ source('bronze', 'purchasing_suppliers') }}
{{ dedup('supplier_id', 'valid_from') }}
