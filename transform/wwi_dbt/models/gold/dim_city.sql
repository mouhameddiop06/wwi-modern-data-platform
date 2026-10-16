-- Géographie dénormalisée : ville > province/État > pays > continent
select
    c.city_id,
    c.city_name,
    sp.state_province_code,
    sp.state_province_name,
    sp.sales_territory,
    co.country_name,
    co.iso_alpha3_code     as country_code,
    co.continent,
    co.region,
    co.subregion,
    c.latest_recorded_population as city_population
from {{ ref('slv_cities') }} c
left join {{ ref('slv_state_provinces') }} sp on sp.state_province_id = c.state_province_id
left join {{ ref('slv_countries') }} co on co.country_id = sp.country_id
