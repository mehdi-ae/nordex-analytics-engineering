with shipments as (
    select *
    from {{ ref('stg_shipments') }}
),
orders as (
    select *
    from {{ ref('stg_orders') }}
),
shipments_enriched as (
    select 
        s.* except(dest_region), 
        coalesce(s.dest_region, o.ship_to_region) as dest_region,
        case when s.dest_region is not null then 'shipment'
             when o.ship_to_region is not null then 'order'
             else 'unknown' end as dest_region_source, 
        case when s.dest_region is null and o.ship_to_region is null then True 
             else False end as is_dest_region_still_missing
        
    from 
        shipments s
        left join orders o on s.order_id = o.order_id
)

select *
from shipments_enriched
