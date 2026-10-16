-- Données personnelles minimisées : identifiants de connexion et préférences exclus
select
    person_id,
    {{ clean_text('full_name') }}            as full_name,
    {{ clean_text('preferred_name') }}       as preferred_name,
    coalesce(is_employee, false)             as is_employee,
    coalesce(is_salesperson, false)          as is_salesperson,
    lower({{ clean_text('email_address') }}) as email_address,
    {{ clean_text('phone_number') }}         as phone_number
from {{ source('bronze', 'application_people') }}
{{ dedup('person_id', 'valid_from') }}
