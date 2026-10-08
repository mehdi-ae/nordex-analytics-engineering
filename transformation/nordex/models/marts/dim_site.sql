with sites as (
    select *
    from {{ ref('stg_sites') }}
)
select * 
from sites