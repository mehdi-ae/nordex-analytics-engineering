WITH source AS (
    SELECT *
    FROM {{source('raw', 'sites')}}
), 
formatted AS (
    SELECT 
        TRIM(site_id) AS site_id,
        TRIM(city) AS city, 
        TRIM(region) AS region, 
        SAFE_CAST(storage_capacity_units AS NUMERIC) AS storage_capacity_units
    FROM source  
), 
final AS (
    SELECT 
        site_id, 
        city, 
        region, 
        storage_capacity_units
    FROM formatted
)
SELECT *
FROM final