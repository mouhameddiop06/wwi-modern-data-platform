{# Texte nettoyé : espaces supprimés, chaînes vides -> NULL #}
{% macro clean_text(col) -%}
    nullif(trim({{ col }}), '')
{%- endmacro %}

{# Montant normalisé en décimal à 2 chiffres #}
{% macro to_amount(col) -%}
    cast({{ col }} as number(18, 2))
{%- endmacro %}

{# Dédoublonnage de sécurité : garde la version la plus récente par clé #}
{% macro dedup(key, order_col) -%}
    qualify row_number() over (partition by {{ key }} order by {{ order_col }} desc) = 1
{%- endmacro %}
