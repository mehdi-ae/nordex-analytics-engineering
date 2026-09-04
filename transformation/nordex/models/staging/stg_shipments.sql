WITH source AS (
    SELECT *
    FROM {{source('raw', 'shipments')}}
), 
formatted AS (
    SELECT 
        TRIM(shipment_id) AS shipment_id, 
        TRIM(order_id) AS order_id, 
        TRIM(origin_site) AS origin_site, 
        TRIM(dest_region) AS dest_region, 
        UPPER(TRIM(carrier_name)) AS carrier_name, 
        SAFE_CAST(ship_date AS DATE) AS ship_date, 
        SAFE_CAST(promised_delivery_date AS DATE) AS promised_delivery_date, 
        SAFE_CAST(actual_delivery_date AS DATE) AS actual_delivery_date,
        SAFE_CAST(weight_grams AS NUMERIC) AS weight_grams, 
        SAFE_CAST(freight_cost_eur AS NUMERIC) AS freight_cost_eur, 
        TRIM(status) AS status
    FROM source
), 
contract_flags AS (
    SELECT 
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
        CASE WHEN dest_region IS NULL THEN TRUE ELSE FALSE END AS is_dest_region_missing, 
        CASE WHEN status = 'DELIVERED' AND actual_delivery_date IS NULL THEN TRUE ELSE FALSE END AS is_delivered_without_date 
    FROM formatted
)
SELECT *
FROM contract_flags