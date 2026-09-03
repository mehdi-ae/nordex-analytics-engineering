WITH source AS (
    SELECT *
    FROM {{source('raw', 'inbound_receipts')}}
), 
formatted AS (
    SELECT 
        TRIM(receipt_id) AS receipt_id, 
        TRIM(sku) AS sku, 
        TRIM(site_id) AS site_id, 
        SAFE_CAST(quantity_received AS NUMERIC) AS quantity_received, 
        SAFE_CAST(receipt_date AS DATE) AS receipt_date
    FROM source
)
SELECT *
FROM formatted