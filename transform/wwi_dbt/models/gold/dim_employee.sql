-- Employés (dont commerciaux) issus de la table People
select
    person_id      as employee_id,
    full_name      as employee_name,
    preferred_name,
    is_salesperson,
    email_address
from {{ ref('slv_people') }}
where is_employee
