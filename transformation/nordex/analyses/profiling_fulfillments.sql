select fulfillment_id
from {{source('raw', 'fulfillments')}}
where date_diff(cast(fulfillment_ts as date), cast(fulfillment_date as date), DAY) != 0  
limit 100; 



select 
    count(distinct fulfillment_id) as fulfillment_count, 
    countif(order_id is null) as null_orders,
    count(*) as total_count, 
    count(distinct order_id) as orders, 
    count(distinct site_id) as sites,
    countif(site_id is null) as null_sites, 
    countif(quantity_fulfilled is null) as null_quantity,
    min(cast(quantity_fulfilled as numeric)) as min_quantity, 
    countif(fulfillment_ts is null) as null_ts, 
    countif(fulfillment_date is null) as null_date
from  {{source('raw', 'fulfillments')}};


select *
from  {{source('raw', 'fulfillments')}}
limit 100;