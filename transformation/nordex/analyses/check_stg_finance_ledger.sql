select 
    countif(is_revenue_non_positive) as nb_revenue_non_pos,
    countif(is_cogs_non_positive) as nb_cogs_non_pos,
    countif(is_freight_missing) as missing_freight, 
    count(*)
from {{ref('stg_finance_ledger')}};