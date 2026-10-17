-- =====================================================================
-- Projet MDP AI - Améliorations (à exécuter une fois en ACCOUNTADMIN)
--   1. Alerte budgétaire : moniteur de crédits sur l'entrepôt WWI_WH
--   2. Intégration continue : droit de cloner la base (environnement de test)
--   3. Streamlit in Snowflake : schéma APP pour héberger l'application
-- =====================================================================
USE ROLE ACCOUNTADMIN;

-- ---------------------------------------------------------------------
-- 1. Moniteur de ressources : alerte e-mail à 75 % et 90 % du quota mensuel,
--    suspension de l'entrepôt à 100 % (protège les crédits de l'essai).
--    Les e-mails partent vers les administrateurs ayant activé les
--    notifications (Profil > Notifications dans Snowsight).
-- ---------------------------------------------------------------------
CREATE OR REPLACE RESOURCE MONITOR WWI_CREDIT_MONITOR
  WITH CREDIT_QUOTA = 50
       FREQUENCY = MONTHLY
       START_TIMESTAMP = IMMEDIATELY
  TRIGGERS
    ON 75 PERCENT DO NOTIFY
    ON 90 PERCENT DO NOTIFY
    ON 100 PERCENT DO SUSPEND
    ON 110 PERCENT DO SUSPEND_IMMEDIATE;

ALTER WAREHOUSE WWI_WH SET RESOURCE_MONITOR = WWI_CREDIT_MONITOR;

-- ---------------------------------------------------------------------
-- 2. Intégration continue : la CI clone WWI_DB (clone « zéro copie »,
--    instantané et sans coût de stockage initial) dans WWI_DB_CI, y exécute
--    dbt build, puis supprime le clone.
-- ---------------------------------------------------------------------
GRANT CREATE DATABASE ON ACCOUNT TO ROLE WWI_ENGINEER;

-- ---------------------------------------------------------------------
-- 3. Streamlit in Snowflake : schéma dédié à l'application
-- ---------------------------------------------------------------------
USE ROLE WWI_ENGINEER;
CREATE SCHEMA IF NOT EXISTS WWI_DB.APP;
GRANT USAGE ON SCHEMA WWI_DB.APP TO ROLE WWI_ANALYST;
