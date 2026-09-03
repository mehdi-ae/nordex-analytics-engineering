WITH source AS (
    SELECT * FROM {{source('raw', 'inventory_snapshots')}}
), 
formatted AS (
    SELECT
        SAFE_CAST(snapshot_date AS DATE) AS snapshot_date, 
        TRIM(site_id) AS site_id, 
        TRIM(sku) AS sku, 
        SAFE_CAST(quantity_on_hand AS NUMERIC) AS quantity_on_hand
    FROM source
), 
deduplicated AS (
    SELECT 
        snapshot_date, 
        site_id, 
        sku, 
        quantity_on_hand
    FROM formatted 
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY snapshot_date, site_id, sku
        ORDER BY snapshot_date
    ) = 1 
), 
final AS (
    SELECT 
        snapshot_date, 
        site_id, 
        sku,
        quantity_on_hand
    FROM deduplicated
)

SELECT *
FROM final