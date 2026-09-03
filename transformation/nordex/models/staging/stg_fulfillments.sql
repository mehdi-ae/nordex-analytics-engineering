WITH source AS (
    SELECT *
    FROM {{source('raw', 'fulfillments')}}
), 
formatted AS (
    SELECT 
        TRIM(fulfillment_id) AS fulfillment_id, 
        TRIM(order_id) AS order_id, 
        TRIM(sku) AS sku, 
        TRIM(site_id) AS site_id, 
        SAFE_CAST(quantity_fulfilled AS NUMERIC) AS quantity_fulfilled, 
        SAFE_CAST(fulfillment_ts AS TIMESTAMP) AS fulfillment_ts, 
        SAFE_CAST(fulfillment_date AS DATE) AS fulfillment_date
    FROM source
)

SELECT *
FROM formatted