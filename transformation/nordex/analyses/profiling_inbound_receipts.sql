select  * FROM {{source('raw', 'inbound_receipts')}};


select 
    count(receipt_id) as receipt_count, 
    count(distinct receipt_id) as unique_receipts,
    count(*) as row_count, 
    countif(sku is null) as null_skus, 
    count(distinct site_id) as distinct_sites, 
    min(cast(quantity_received as numeric)) as min_qty,
    countif(quantity_received is null) as null_qty,
    countif(receipt_date is NULL) as null_dates, 
FROM {{source('raw', 'inbound_receipts')}};    


select 
    countif(cast(receipt_date as date) is null) as non_iso_dates
FROM {{source('raw', 'inbound_receipts')}};
