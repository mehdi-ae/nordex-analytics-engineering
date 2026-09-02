
select 
    count(*)
    , count(distinct customer_id) as distinct_customers
    , countif(customer_id is null) as null_customers
    , count(distinct region) as region_count
    , countif(region is null) as null_regions
    , countif(signup_date is null) as null_signups
from {{ source('raw', 'customers') }} ; 

select distinct region
from {{ source('raw', 'customers') }} ; 

select *
from {{ source('raw', 'customers') }} 
where region is null; 

select *
from {{ source('raw', 'customers') }} 
where signup_date is null; 

select
  countif(region is null and signup_date is null) as les_deux_null,
  countif(region is null and signup_date is not null) as region_seule,
  countif(region is not null and signup_date is null) as signup_seul
from {{ source('raw', 'customers') }};

select
  countif(signup_date is not null and safe_cast(signup_date as date) is null) as non_castable_iso,
  countif(signup_date is not null) as total_non_null
from {{ source('raw', 'customers') }};
