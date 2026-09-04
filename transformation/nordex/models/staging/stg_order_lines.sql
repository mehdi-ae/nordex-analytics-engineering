WITH source AS (
    SELECT *FROM {{source('raw', 'order_lines')}}
), 
formatted AS (
    SELECT 
        TRIM(order_id) AS order_id, 
        SAFE_CAST(line_no AS INT64) AS line_no, 
        TRIM(sku) AS sku, 
        SAFE_CAST(quantity_ordered AS NUMERIC) AS quantity_ordered, 
        SAFE_CAST(unit_price_eur AS NUMERIC) AS unit_price_eur,
        SAFE_CAST(line_total_eur AS NUMERIC) AS line_total_eur
    FROM source
),
deduplication_and_flags AS (
    SELECT 
        order_id, 
        line_no, 
        sku, 
        quantity_ordered, 
        unit_price_eur, 
        line_total_eur, 
        CASE 
            WHEN unit_price_eur IS NULL THEN NULL 
            WHEN unit_price_eur <= 0 THEN TRUE ELSE FALSE 
        END AS is_price_non_positive, 
        CASE
            WHEN unit_price_eur IS NULL THEN NULL 
            WHEN ROUND(unit_price_eur * quantity_ordered, 2) != ROUND(line_total_eur, 2) THEN TRUE ELSE FALSE 
        END AS is_total_mismatch
    FROM formatted 
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY order_id, line_no, sku, quantity_ordered, unit_price_eur, line_total_eur
        ) = 1 
)
SELECT *
FROM deduplication_and_flags