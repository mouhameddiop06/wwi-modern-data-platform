"""
Déploie l'application dans Streamlit in Snowflake (SiS).

    python deploy/deploy_sis.py

Étapes :
  1. (WWI_ENGINEER) schéma WWI_DB.APP + droits de création accordés à WWI_ANALYST
  2. (WWI_ANALYST)  stage interne, envoi des fichiers de app/, CREATE STREAMLIT
L'application appartient au rôle WWI_ANALYST : elle s'exécute avec ses droits
(lecture seule de GOLD + Cortex), sans aucun mot de passe à stocker.
"""
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
load_dotenv(ROOT / ".env")

DB = os.getenv("SNOWFLAKE_DATABASE", "WWI_DB")
STAGE = f"{DB}.APP.STREAMLIT_STAGE"
APP_NAME = f"{DB}.APP.WWI_INSIGHTS"
STAGE_DIR = "wwi_insights"
FILES = ["streamlit_app.py", "cortex_analyst.py", "semantic_model.yaml", "environment.yml", "LOGO-UCAD.png"]


def main() -> None:
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "WWI_ENGINEER"),
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=DB,
    )
    cur = conn.cursor()

    # 1. Schéma applicatif (propriété de WWI_ENGINEER) et droits pour WWI_ANALYST
    for sql in [
        f"CREATE SCHEMA IF NOT EXISTS {DB}.APP",
        f"GRANT USAGE ON SCHEMA {DB}.APP TO ROLE WWI_ANALYST",
        f"GRANT CREATE STAGE ON SCHEMA {DB}.APP TO ROLE WWI_ANALYST",
        f"GRANT CREATE STREAMLIT ON SCHEMA {DB}.APP TO ROLE WWI_ANALYST",
    ]:
        cur.execute(sql)

    # 2. Stage + fichiers + application, sous le rôle analyste
    cur.execute("USE ROLE WWI_ANALYST")
    cur.execute(f"CREATE STAGE IF NOT EXISTS {STAGE} DIRECTORY = (ENABLE = TRUE)")
    for name in FILES:
        path = (APP_DIR / name).as_posix()
        cur.execute(f"PUT 'file://{path}' @{STAGE}/{STAGE_DIR} AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
        print(f"  envoyé : {name}")

    cur.execute(f"""
        CREATE OR REPLACE STREAMLIT {APP_NAME}
          ROOT_LOCATION = '@{STAGE}/{STAGE_DIR}'
          MAIN_FILE = 'streamlit_app.py'
          QUERY_WAREHOUSE = {os.environ['SNOWFLAKE_WAREHOUSE']}
          TITLE = 'WWI Insights - UCAD'
          COMMENT = 'Text-to-SQL Cortex Analyst sur la couche GOLD'
    """)
    cur.execute(f"SHOW STREAMLITS LIKE 'WWI_INSIGHTS' IN SCHEMA {DB}.APP")
    row = dict(zip([c[0] for c in cur.description], cur.fetchone() or [], strict=False))
    print("\nApplication déployée :", APP_NAME, "| propriétaire :", row.get("owner", "?"))

    org, account = os.environ["SNOWFLAKE_ACCOUNT"].lower().split("-", 1)
    print(f"Ouvrir : https://app.snowflake.com/{org}/{account}/#/streamlit-apps/{APP_NAME}")
    conn.close()


if __name__ == "__main__":
    main()
