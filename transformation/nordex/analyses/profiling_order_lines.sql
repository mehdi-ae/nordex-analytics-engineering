select *
 from {{source('raw', 'order_lines')}} 
-- where sku = 'SKU-01022' ;

select 
    count(*) as total, 
    count(distinct order_id) as unique_orders,
    min(cast (quantity_ordered as numeric)) as min_qty,
    min(cast (unit_price_eur as numeric)) as min_price, 
    min(cast(line_total_eur as numeric)) as min_line_total,
    countif(cast(unit_price_eur as numeric) <= 0 ) as non_positive_prices,
    countif(sku is null) as null_skus
from {{source('raw', 'order_lines')}};

select 
    count(distinct concat(order_id, '+', sku)) as key_test_count, 
    count(*)
from {{source('raw', 'order_lines')}};

select 
    distinct concat(order_id, '+', sku) as unique_key,
    count(concat(order_id, '+', sku)) as count_unique
from {{source('raw', 'order_lines')}}
group by 1
having count_unique > 1; 

select 
*
from {{source('raw', 'order_lines')}}
where order_id = 'ORD-018121' ; 

select order_id, sku, line_no, count(*)
from {{ source('raw', 'order_lines') }}
group by order_id, sku, line_no
having count(*) > 1;