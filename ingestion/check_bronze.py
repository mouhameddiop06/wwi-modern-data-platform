"""
Contrôle de réconciliation : nombre de lignes SQL Server vs Snowflake BRONZE.

    python ingestion/check_bronze.py
"""
import os
import re

import snowflake.connector
import sqlalchemy as sa

from wwi_pipeline import TABLES, mssql_engine


def snake(name: str) -> str:
    """Reproduit la convention de nommage DLT : Sales_InvoiceLines -> sales_invoice_lines."""
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.lower()


def main() -> None:
    sf = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ["SNOWFLAKE_ROLE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema="BRONZE",
    )
    engine = mssql_engine()
    ok = True
    print(f"{'Table':<40}{'SQL Server':>12}{'Snowflake':>12}  Statut")
    with engine.connect() as src, sf.cursor() as cur:
        for full_name in TABLES:
            schema, name = full_name.split(".")
            n_src = src.execute(sa.text(f"SELECT COUNT(*) FROM [{schema}].[{name}]")).scalar()
            target = snake(f"{schema}_{name}")
            n_dst = cur.execute(f"SELECT COUNT(*) FROM {target}").fetchone()[0]
            status = "OK" if n_src == n_dst else "ÉCART"
            ok &= n_src == n_dst
            print(f"{target:<40}{n_src:>12,}{n_dst:>12,}  {status}")
    sf.close()
    print("\nRéconciliation réussie." if ok else "\nDes écarts ont été détectés.")


if __name__ == "__main__":
    main()
