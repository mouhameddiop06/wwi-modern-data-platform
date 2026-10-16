-- Calendrier généré (une ligne par jour), libellés en français
with days as (
    select dateadd(day, seq4(), '{{ var("date_start") }}'::date) as date_day
    from table(generator(rowcount => 3000))
)
select
    date_day,
    year(date_day)                                   as year,
    quarter(date_day)                                as quarter,
    'T' || quarter(date_day)                         as quarter_label,
    month(date_day)                                  as month,
    decode(month(date_day),
        1, 'Janvier', 2, 'Février', 3, 'Mars', 4, 'Avril', 5, 'Mai', 6, 'Juin',
        7, 'Juillet', 8, 'Août', 9, 'Septembre', 10, 'Octobre', 11, 'Novembre', 12, 'Décembre')
                                                     as month_name,
    to_char(date_day, 'YYYY-MM')                     as year_month,
    weekofyear(date_day)                             as week_of_year,
    dayofmonth(date_day)                             as day_of_month,
    dayofweekiso(date_day)                           as day_of_week,
    decode(dayofweekiso(date_day),
        1, 'Lundi', 2, 'Mardi', 3, 'Mercredi', 4, 'Jeudi', 5, 'Vendredi', 6, 'Samedi', 7, 'Dimanche')
                                                     as day_name,
    dayofweekiso(date_day) in (6, 7)                 as is_weekend
from days
where date_day <= '{{ var("date_end") }}'::date
