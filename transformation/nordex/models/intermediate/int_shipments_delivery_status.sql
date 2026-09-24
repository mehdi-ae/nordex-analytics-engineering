with source as (
    select *
    from {{ ref('int_shipments_enriched') }}
), 
delivery_status as (
    select 
        shipment_id, 
        order_id, 
        origin_site, 
        dest_region, 
        carrier_name, 
        ship_date, 
        promised_delivery_date, 
        actual_delivery_date, 
        weight_grams, 
        freight_cost_eur, 
        status,
        case 
            when status = 'DELIVERED' and actual_delivery_date is null then 'to investigate'
            when status = 'DELIVERED' and actual_delivery_date <= promised_delivery_date then 'on_time'
            when status = 'DELIVERED' and actual_delivery_date > promised_delivery_date then 'late'
            when status = 'IN_TRANSIT' then 'in_transit'
            else 'unknown status' 
        end as delivery_status
    from source
)
select *
from delivery_status