with source as (

    select *
    from {{ ref('int_shipments_delivery_status') }}

),

final as (

    select
        s.shipment_id,
        s.order_id,
        c.carrier_id,
        s.origin_site as origin_site_id,
        s.dest_region,
        s.ship_date,
        s.delivery_status,
        s.promised_delivery_date,
        s.actual_delivery_date,
        date_diff(s.actual_delivery_date, s.promised_delivery_date, day) as delivery_delay_days,
        s.weight_grams,
        s.freight_cost_eur
    from source s
    left join {{ ref('dim_carrier') }} c on s.carrier_name = c.carrier_name

)

select *
from final