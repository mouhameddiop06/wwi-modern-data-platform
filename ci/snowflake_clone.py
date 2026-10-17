"""
Gestion de la base de test de l'intégration continue (clone « zéro copie » de WWI_DB).

    python ci/snowflake_clone.py create WWI_DB_CI_123
    python ci/snowflake_clone.py drop   WWI_DB_CI_123
"""
import os
import re
import sys

import snowflake.connector

action, name = sys.argv[1], sys.argv[2].upper()
if not re.fullmatch(r"WWI_DB_CI_[A-Z0-9_]+", name):
    sys.exit("Nom de clone invalide : il doit commencer par WWI_DB_CI_")

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    password=os.environ["SNOWFLAKE_PASSWORD"],
    role=os.environ.get("SNOWFLAKE_ROLE", "WWI_ENGINEER"),
    warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "WWI_WH"),
)
with conn.cursor() as cur:
    if action == "create":
        cur.execute(f"CREATE OR REPLACE DATABASE {name} CLONE WWI_DB")
        print(f"Clone {name} créé à partir de WWI_DB")
    elif action == "drop":
        cur.execute(f"DROP DATABASE IF EXISTS {name}")
        print(f"Clone {name} supprimé")
    else:
        sys.exit("Action attendue : create ou drop")
conn.close()
