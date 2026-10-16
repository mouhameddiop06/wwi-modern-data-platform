{#
  Utilise directement le schéma déclaré (SILVER, GOLD) au lieu du
  comportement par défaut de dbt (<schema_cible>_<schema_custom>).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim | upper }}
    {%- endif -%}
{%- endmacro %}
