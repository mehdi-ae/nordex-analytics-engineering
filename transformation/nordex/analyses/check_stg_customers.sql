select 
    countif(is_region_missing), 
    countif(is_region_missing), 
    count(*)
from  {{ ref('stg_customers') }}