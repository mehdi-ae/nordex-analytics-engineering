with bounds as (

    select
        min(ship_date) as start_date,
        max(ship_date) as end_date
    from {{ ref('stg_shipments') }}

),

date_spine as (

    select date_day
    from bounds,
    unnest(generate_date_array(bounds.start_date, bounds.end_date, interval 1 day)) as date_day

),

final as (

    select
        date_day,
        extract(year      from date_day) as year,
        extract(quarter   from date_day) as quarter,
        extract(month     from date_day) as month_number,
        extract(day       from date_day) as day_of_month,
        extract(dayofweek from date_day) as day_of_week,
        format_date('%B', date_day)      as month_name,
        format_date('%Y-%m', date_day)   as month_year,
        concat(
            cast(extract(year    from date_day) as string), '-Q',
            cast(extract(quarter from date_day) as string)
        )                                as quarter_year,
        case when extract(dayofweek from date_day) in (1, 7) then true else false end as is_weekend
    from date_spine

)

select * from final