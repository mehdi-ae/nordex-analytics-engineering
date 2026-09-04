WITH source AS (
    SELECT *
    FROM {{source('raw', 'finance_ledger')}}
), 
formatted AS (
    SELECT 
        TRIM(order_ref) AS order_ref,
        SAFE.PARSE_DATE('%d/%m/%Y', revenue_date) AS revenue_date,
        SAFE_CAST(recognized_revenue_eur AS NUMERIC) AS recognized_revenue_eur, 
        SAFE_CAST(cogs_eur AS NUMERIC) AS cogs_eur, 
        SAFE_CAST(freight_cost_eur AS NUMERIC) AS freight_cost_eur
    FROM source
),
contract_flags AS (
    SELECT 
        order_ref, 
        revenue_date, 
        recognized_revenue_eur,
        cogs_eur, 
        freight_cost_eur, 
        CASE WHEN recognized_revenue_eur <= 0 THEN TRUE ELSE FALSE END AS is_revenue_non_positive,
        CASE WHEN cogs_eur <= 0 THEN TRUE ELSE FALSE END AS is_cogs_non_positive, 
        CASE WHEN freight_cost_eur IS NULL THEN TRUE ELSE FALSE END AS is_freight_missing
    FROM formatted
), 
final AS (
    SELECT *
    FROM contract_flags
)

SELECT *
FROM final