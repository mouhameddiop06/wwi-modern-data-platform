{{ config(
    materialized='incremental',
    unique_key='invoice_line_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns'
) }}

-- Grain : une ligne de facture
select
    il.invoice_line_id,
    il.invoice_id,
    i.order_id,
    i.invoice_date,
    i.customer_id,
    i.bill_to_customer_id,
    il.stock_item_id,
    i.salesperson_person_id             as salesperson_id,
    c.delivery_city_id,
    dm.delivery_method_name             as delivery_method,
    pt.package_type_name                as package_type,
    i.is_credit_note,
    il.quantity,
    il.unit_price,
    il.tax_rate,
    il.amount_excluding_tax,
    il.tax_amount,
    il.amount_including_tax,
    il.line_profit                      as profit,
    i.confirmed_delivery_date,
    greatest(il.last_edited_when, i.last_edited_when) as last_edited_when
from {{ ref('slv_invoice_lines') }} il
join {{ ref('slv_invoices') }} i on i.invoice_id = il.invoice_id
left join {{ ref('slv_customers') }} c on c.customer_id = i.customer_id
left join {{ ref('slv_delivery_methods') }} dm on dm.delivery_method_id = i.delivery_method_id
left join {{ ref('slv_package_types') }} pt on pt.package_type_id = il.package_type_id
{% if is_incremental() %}
where greatest(il.last_edited_when, i.last_edited_when) >
      (select coalesce(max(last_edited_when), '1900-01-01'::timestamp_ntz) from {{ this }})
{% endif %}
