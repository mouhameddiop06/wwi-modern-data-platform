{{ config(
    materialized='incremental',
    unique_key='customer_transaction_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns'
) }}

select
    customer_transaction_id,
    customer_id,
    transaction_type_id,
    invoice_id,
    payment_method_id,
    transaction_date,
    {{ to_amount('amount_excluding_tax') }} as amount_excluding_tax,
    {{ to_amount('tax_amount') }}           as tax_amount,
    {{ to_amount('transaction_amount') }}   as transaction_amount,
    {{ to_amount('outstanding_balance') }}  as outstanding_balance,
    finalization_date,
    coalesce(is_finalized, false)           as is_finalized,
    last_edited_when
from {{ source('bronze', 'sales_customer_transactions') }}
{{ incremental_filter() }}
{{ dedup('customer_transaction_id', 'last_edited_when') }}
