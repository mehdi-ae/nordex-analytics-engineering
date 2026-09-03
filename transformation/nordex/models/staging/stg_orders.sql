WITH source AS (
    SELECT *
    FROM {{source('raw', 'orders')}}
), 
formatted AS (
    SELECT 
        TRIM(order_id) AS order_id,
        TRIM(customer_id) AS customer_id,
        SAFE_CAST(order_ts AS TIMESTAMP) AS order_ts, 
        SAFE_CAST(order_date AS DATE) AS order_date, 
        TRIM(ship_to_region) AS ship_to_region, 
        TRIM(status) AS status
    FROM source
), 
deduplication AS (
    SELECT 
        order_id, 
        customer_id, 
        order_ts, 
        order_date,
        ship_to_region, 
        status,
        CASE WHEN ship_to_region IS NULL THEN TRUE ELSE FALSE END AS is_region_missing
    FROM formatted
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY order_id, customer_id, order_ts, order_date, ship_to_region, status 
        ORDER BY order_date) = 1 
), 
final AS (
    SELECT * 
    FROM deduplication
)

SELECT *
FROM final