WITH source AS (
    SELECT * FROM {{source('raw', 'customers')}}
), 
formatted AS (
    SELECT 
        TRIM(customer_id) AS customer_id, 
        TRIM(region) AS region, 
        SAFE_CAST(signup_date AS DATE) as signup_date
    FROM source
), 
contract_flags AS (
    SELECT 
        customer_id, 
        region, 
        signup_date, 
        CASE WHEN region IS NULL THEN TRUE ELSE FALSE END AS is_region_missing, 
        CASE WHEN signup_date IS NULL THEN TRUE ELSE FALSE END AS is_signup_missing
    FROM formatted
), 
final AS (
    SELECT *
    FROM contract_flags
)

SELECT *
FROM final
