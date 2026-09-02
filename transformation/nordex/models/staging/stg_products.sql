WITH source AS (
    SELECT * FROM {{ source('raw', 'products') }}
), 

formatted AS (
    SELECT 
        TRIM(sku) AS sku, 
        TRIM(product_name) AS product_name, 
        TRIM(category) AS category,
        SAFE_CAST(weight_grams AS NUMERIC) AS weight_grams,
        SAFE_CAST(unit_cost_eur AS NUMERIC) AS unit_cost_eur,
        SAFE_CAST(list_price_eur AS NUMERIC) AS list_price_eur
    FROM source
), 
contract_flags AS (
    SELECT 
        sku, 
        product_name,
        category, 
        weight_grams, 
        unit_cost_eur,
        list_price_eur, 
        CASE WHEN weight_grams < 20 OR weight_grams > 20000 THEN TRUE ELSE FALSE END AS is_weight_out_of_bounds, 
        CASE WHEN list_price_eur < unit_cost_eur THEN TRUE ELSE FALSE END AS is_price_below_cost,
        CASE WHEN weight_grams <= 0 OR unit_cost_eur <= 0 OR list_price_eur <= 0 THEN TRUE ELSE FALSE END AS has_non_positive_value, 
        CASE WHEN weight_grams IS NULL THEN TRUE ELSE FALSE END AS is_weight_uncastable
    FROM formatted
), 
final AS (
    SELECT *
    FROM contract_flags
)

SELECT *
FROM final


