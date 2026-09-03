select *
from {{source('raw', 'orders')}}
limit 20;

select 
    count(distinct order_id) as unique_orders, 
    count(*) as total_rows, 
    count(cast(order_ts AS TIMESTAMP)) as iso_1, 
    count(cast(order_date as date)) as iso_2, 
    countif(status is null) as null_status,
    count(distinct status) as unique_status
from {{source('raw', 'orders')}};


select *
from {{source('raw', 'orders')}}
where order_id in 
(select order_id
from {{source('raw', 'orders')}}
group by  order_id
having count(order_id) > 1 );


select 
    distinct ship_to_region 
from {{source('raw', 'orders')}};

select 
    countif(ship_to_region is null) as null_regions 
from {{source('raw', 'orders')}}
;