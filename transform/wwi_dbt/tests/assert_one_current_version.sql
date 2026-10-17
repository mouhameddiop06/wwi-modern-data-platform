-- SCD2 : chaque produit et chaque client a exactement une version courante
select 'produit' as entite, stock_item_id as id, count_if(is_current) as nb_courantes
from {{ ref('dim_product_history') }}
group by stock_item_id
having count_if(is_current) <> 1
union all
select 'client', customer_id, count_if(is_current)
from {{ ref('dim_customer_history') }}
group by customer_id
having count_if(is_current) <> 1
