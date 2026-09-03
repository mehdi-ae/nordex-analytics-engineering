select * 
from {{source('raw', 'finance_ledger')}};


select 
    count(*), 
    count(distinct order_ref),
    countif(revenue_date is null) as null_dates,
    countif(recognized_revenue_eur is null) as null_rev,
    countif(cogs_eur is null) as null_cogs,
    countif(freight_cost_eur is null) as null_cost_eur, 
    min(cast(recognized_revenue_eur as numeric)) as min_rev, 
    min(cast(cogs_eur as numeric)) as min_cogs, 
    min(cast(freight_cost_eur as numeric)) as min_freight_cost
from {{source('raw', 'finance_ledger')}};

select * 
from {{source('raw', 'finance_ledger')}}
where CAST(cogs_eur AS NUMERIC) <= 0 ;

select countif(revenue_date is not null and safe_cast(revenue_date as date) is null) as non_iso
from {{source('raw', 'finance_ledger')}};
