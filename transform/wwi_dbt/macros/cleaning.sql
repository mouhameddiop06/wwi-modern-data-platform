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

{# Clé de substitution : hash MD5 des colonnes données #}
{% macro surrogate_key(cols) -%}
    md5({% for c in cols %}coalesce(cast({{ c }} as varchar), '_null_'){% if not loop.last %} || '|' || {% endif %}{% endfor %})
{%- endmacro %}

{#
  Filtre incrémental : lors d'une exécution incrémentale, ne traite que les lignes
  modifiées depuis le dernier chargement (colonne de suivi last_edited_when).
#}
{% macro incremental_filter(col='last_edited_when', target_col='last_edited_when') -%}
    {% if is_incremental() -%}
    where {{ col }} > (select coalesce(max({{ target_col }}), '1900-01-01'::timestamp_ntz) from {{ this }})
    {%- endif %}
{%- endmacro %}
