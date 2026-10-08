with carriers as (
    select *
    from {{ ref('stg_carriers') }}
)
select * 
from carriers