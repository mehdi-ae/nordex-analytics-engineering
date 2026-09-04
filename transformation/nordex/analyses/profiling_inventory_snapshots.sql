select * FROM {{source('raw', 'inventory_snapshots')}}
limit 20; 

select 
    count(distinct(concat(snapshot_date, '+', site_id, '+', sku))) as unique_id, 
    count(*) as total_rows, 
    countif(snapshot_date is null) as null_dates,
    countif(site_id is null) as null_sites, 
    countif(sku is null) as null__sku, 
    min(cast(quantity_on_hand as numeric)) as min_quantity
from {{source('raw', 'inventory_snapshots')}}; 

select 
    concat(snapshot_date, '+', site_id, '+', sku) as unique_id,
    count(*) as count_id
from {{source('raw', 'inventory_snapshots')}}
group by 1 
having count_id >1 
order by count_id desc;

select 
    concat(snapshot_date, '+', site_id, '+', sku) as unique_id,
    count(*) as count_id, 
    count(distinct cast(quantity_on_hand as numeric)) as unique_quantities
from {{source('raw', 'inventory_snapshots')}}
group by 1 
having count_id >1 
order by count_id desc;

SELECT 
    COUNTIF(SAFE_CAST(snapshot_date AS date) IS NULL) AS non_iso_dates
FROM 
{{source('raw', 'inventory_snapshots')}};


----- check  post dbt run -----

select count(*) as total 
from {{ref('stg_inventory_snapshots')}};