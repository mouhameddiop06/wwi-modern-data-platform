-- =====================================================================
-- Projet MDP AI - Initialisation Snowflake (à exécuter en ACCOUNTADMIN)
-- Crée : entrepôt, base, schémas Médaillon, rôles et utilisateur technique
-- =====================================================================
USE ROLE ACCOUNTADMIN;

-- Cortex : autoriser l'inférence inter-régions (modèles indisponibles localement)
ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';

-- ---------------------------------------------------------------------
-- Entrepôt de calcul (petit, suspension automatique pour économiser les crédits)
-- ---------------------------------------------------------------------
CREATE WAREHOUSE IF NOT EXISTS WWI_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- ---------------------------------------------------------------------
-- Base et schémas Médaillon
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS WWI_DB;
CREATE SCHEMA IF NOT EXISTS WWI_DB.BRONZE;   -- données brutes chargées par DLT
CREATE SCHEMA IF NOT EXISTS WWI_DB.SILVER;   -- données nettoyées (dbt)
CREATE SCHEMA IF NOT EXISTS WWI_DB.GOLD;     -- modèle en étoile (dbt) interrogé par Cortex

-- ---------------------------------------------------------------------
-- Rôles
--   WWI_ENGINEER : pipelines DLT / dbt / Dagster (lecture-écriture)
--   WWI_ANALYST  : application Streamlit (lecture GOLD + Cortex)
-- ---------------------------------------------------------------------
CREATE ROLE IF NOT EXISTS WWI_ENGINEER;
CREATE ROLE IF NOT EXISTS WWI_ANALYST;
GRANT ROLE WWI_ANALYST  TO ROLE WWI_ENGINEER;
GRANT ROLE WWI_ENGINEER TO ROLE SYSADMIN;

GRANT USAGE ON WAREHOUSE WWI_WH TO ROLE WWI_ANALYST;
GRANT USAGE, OPERATE ON WAREHOUSE WWI_WH TO ROLE WWI_ENGINEER;

GRANT OWNERSHIP ON DATABASE WWI_DB TO ROLE WWI_ENGINEER COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA WWI_DB.BRONZE TO ROLE WWI_ENGINEER COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA WWI_DB.SILVER TO ROLE WWI_ENGINEER COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA WWI_DB.GOLD   TO ROLE WWI_ENGINEER COPY CURRENT GRANTS;

GRANT USAGE ON DATABASE WWI_DB TO ROLE WWI_ANALYST;
GRANT USAGE ON SCHEMA WWI_DB.GOLD TO ROLE WWI_ANALYST;
GRANT SELECT ON ALL TABLES    IN SCHEMA WWI_DB.GOLD TO ROLE WWI_ANALYST;
GRANT SELECT ON FUTURE TABLES IN SCHEMA WWI_DB.GOLD TO ROLE WWI_ANALYST;
GRANT SELECT ON ALL VIEWS     IN SCHEMA WWI_DB.GOLD TO ROLE WWI_ANALYST;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA WWI_DB.GOLD TO ROLE WWI_ANALYST;

-- Accès aux fonctions Cortex (LLM + Cortex Analyst)
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE WWI_ANALYST;

-- ---------------------------------------------------------------------
-- Utilisateur technique pour les pipelines
-- >>> Remplace le mot de passe ci-dessous AVANT d'exécuter, puis reporte-le dans ton .env <<<
-- ---------------------------------------------------------------------
CREATE USER IF NOT EXISTS WWI_PIPELINE_USER
  PASSWORD = '<CHOISIS_UN_MOT_DE_PASSE_FORT>'
  DEFAULT_ROLE = WWI_ENGINEER
  DEFAULT_WAREHOUSE = WWI_WH
  DEFAULT_NAMESPACE = WWI_DB.BRONZE
  MUST_CHANGE_PASSWORD = FALSE
  TYPE = LEGACY_SERVICE;
GRANT ROLE WWI_ENGINEER TO USER WWI_PIPELINE_USER;

-- Ton propre utilisateur peut aussi utiliser ces rôles
SET ME = CURRENT_USER();
GRANT ROLE WWI_ENGINEER TO USER IDENTIFIER($ME);
