select 
    count(*) as nb_lignes,
    count(distinct sku) as unique_skus, 
    countif(product_name is null),
    countif(category is null), 
    countif(weight_grams is null), 
    countif(unit_cost_eur is null), 
    countif(list_price_eur is null),
    min(weight_grams), 
    max(weight_grams), 
    min(unit_cost_eur), 
    min(list_price_eur)
from {{ source('raw', 'products') }}; 


select sku, product_name, weight_grams
from {{source('raw', 'products')}}
where cast(weight_grams as numeric) < 50
order by weight_grams desc;

select 
    sku, 
    cast(list_price_eur as numeric), 
    cast(unit_cost_eur as numeric),
from {{source('raw', 'products')}}
where  cast(list_price_eur as numeric) < cast(unit_cost_eur as numeric)
;
