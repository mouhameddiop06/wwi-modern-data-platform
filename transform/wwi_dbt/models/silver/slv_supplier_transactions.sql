select
    supplier_transaction_id,
    supplier_id,
    transaction_type_id,
    purchase_order_id,
    payment_method_id,
    {{ clean_text('supplier_invoice_number') }} as supplier_invoice_number,
    transaction_date,
    {{ to_amount('amount_excluding_tax') }}     as amount_excluding_tax,
    {{ to_amount('tax_amount') }}               as tax_amount,
    {{ to_amount('transaction_amount') }}       as transaction_amount,
    {{ to_amount('outstanding_balance') }}      as outstanding_balance,
    finalization_date,
    coalesce(is_finalized, false)               as is_finalized,
    last_edited_when
from {{ source('bronze', 'purchasing_supplier_transactions') }}
{{ dedup('supplier_transaction_id', 'last_edited_when') }}
