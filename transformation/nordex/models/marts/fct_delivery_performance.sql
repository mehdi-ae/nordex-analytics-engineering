with source as (
    select *
    from {{ ref('int_shipments_delivery_status') }}
), 
fct_delivery_performance as (
    select 
        shipment_id, 
        order_id, 
        carrier_name, 
        origin_site, 
        dest_region, 
        ship_date, 
        date_trunc(ship_date, week) as ship_week,
        date_trunc(ship_date, month) as ship_month,
        delivery_status,
        case when delivery_status = 'on_time' then 1 else 0 end as is_on_time,
        case when delivery_status = 'late' then 1 else 0 end as is_late,
        case when delivery_status in ('on_time', 'late') then 1 else 0 end as is_measurable_delivery,
        case when delivery_status = 'in_transit' then 1 else 0 end as is_in_transit,
        case when delivery_status = 'to_investigate' then 1 else 0 end as is_to_investigate,
        promised_delivery_date, 
        actual_delivery_date, 
        weight_grams, 
        freight_cost_eur
    from source
)

select *
from fct_delivery_performance