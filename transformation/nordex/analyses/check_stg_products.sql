select
    countif(is_weight_out_of_bounds) as nb_weight_out,
    countif(is_price_below_cost)     as nb_price_below,
    countif(has_non_positive_value)  as nb_non_positive,
    countif(is_weight_uncastable)    as nb_uncastable,
    count(*)                         as total
from {{ ref('stg_products') }}