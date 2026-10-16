-- Grain : une transaction client (facture, paiement, avoir...)
select
    ct.customer_transaction_id,
    ct.transaction_date,
    ct.customer_id,
    ct.invoice_id,
    tt.transaction_type_name   as transaction_type,
    pm.payment_method_name     as payment_method,
    ct.amount_excluding_tax,
    ct.tax_amount,
    ct.transaction_amount,
    ct.outstanding_balance,
    ct.is_finalized,
    ct.finalization_date
from {{ ref('slv_customer_transactions') }} ct
left join {{ ref('slv_transaction_types') }} tt on tt.transaction_type_id = ct.transaction_type_id
left join {{ ref('slv_payment_methods') }} pm on pm.payment_method_id = ct.payment_method_id
