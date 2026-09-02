WITH source AS (
    SELECT *
    FROM {{source('raw', 'carriers')}}
), 
final AS (
    SELECT
        TRIM(carrier_id) AS carrier_id,
        TRIM(carrier_name) AS carrier_name, 
        TRIM(service_level) AS service_level
    FROM source
)

SELECT *
FROM final