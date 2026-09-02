select *
from {{ source('raw', 'finance_ledger') }}