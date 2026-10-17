{{ config(
    materialized='incremental',
    unique_key='invoice_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns'
) }}

select
    invoice_id,
    customer_id,
    bill_to_customer_id,
    order_id,
    delivery_method_id,
    contact_person_id,
    salesperson_person_id,
    packed_by_person_id,
    invoice_date,
    coalesce(is_credit_note, false)           as is_credit_note,
    {{ clean_text('credit_note_reason') }}    as credit_note_reason,
    total_dry_items,
    total_chiller_items,
    confirmed_delivery_time,
    cast(confirmed_delivery_time as date)     as confirmed_delivery_date,
    {{ clean_text('confirmed_received_by') }} as confirmed_received_by,
    last_edited_when
from {{ source('bronze', 'sales_invoices') }}
{{ incremental_filter() }}
{{ dedup('invoice_id', 'last_edited_when') }}
