select *
from {{ ref('fct_delivery_performance') }}
where (is_measurable_delivery = 1 and (is_on_time = 0 and is_late = 0))
    or (is_measurable_delivery = 0 and (is_on_time = 1 or is_late = 1))