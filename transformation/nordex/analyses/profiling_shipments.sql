select *
from {{source('raw', 'shipments')}}
limit 10 ;

select 
    count(*) as total_count, 
    count(distinct shipment_id) as key_detection, 
    countif(order_id is null) as null_orders, 
    count(distinct origin_site) as distinct_sites, 
    count(distinct dest_region) as distinct_dest, 
    countif(dest_region is null) as null_destination,
    countif(carrier_name is null) as missing_carrier,
    min(cast(weight_grams as numeric)) as min_weight, 
    min(cast(freight_cost_eur as numeric)) as min_freight_cost
from {{source('raw', 'shipments')}};

select
    countif(cast(promised_delivery_date as date) is null) as non_iso_promise, 
    countif(cast(actual_delivery_date as date) is null) as non_iso_actual
from {{source('raw', 'shipments')}}
where actual_delivery_date is not null ; 

select 
    distinct carrier_name
from {{source('raw', 'shipments')}}; 

select 
    distinct status 
from {{source('raw', 'shipments')}};

select 
    promised_delivery_date, actual_delivery_date, status 
from {{source('raw', 'shipments')}}
where  cast(actual_delivery_date as date) is null
; 

select
    countif(status = 'IN_TRANSIT' and actual_delivery_date is null) as legit_null, 
    countif(status = 'DELIVERED' and actual_delivery_date is null) as bug_null
from {{source('raw', 'shipments')}}; 

select 
    countif(actual_delivery_date is not null and cast(actual_delivery_date as date) < cast(ship_date as date)) as delivery_before_ship
from {{source('raw', 'shipments')}};


---- post dbt run checks ----
select 
    countif(is_delivered_without_date) as delivered_without_date, 
    countif(is_dest_region_missing) as missing_dest, 
    count(*) as total_count
from {{ref('stg_shipments')}} ;

select distinct carrier_name
from {{ref('stg_shipments')}} ;