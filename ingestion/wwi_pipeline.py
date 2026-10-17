"""
Pipeline DLT : SQL Server (WideWorldImporters) -> Snowflake (WWI_DB.BRONZE)

Stratégie de chargement par table :
  - colonne LastEditedWhen  -> incrémental + merge sur la clé primaire
  - table temporelle (ValidFrom) -> incrémental + merge sur la clé primaire
  - sinon (dont tables *_Archive sans clé) -> remplacement complet (replace)

Colonnes exclues : types spatiaux (geography) et binaires (photos, mots de passe hachés),
inutiles pour l'analyse et non supportés tels quels par Snowflake.

Utilisation :
    python ingestion/wwi_pipeline.py                      # toutes les tables, incrémental
    python ingestion/wwi_pipeline.py --tables Sales.Orders Sales.Customers
    python ingestion/wwi_pipeline.py --full-refresh       # recharge tout depuis zéro
"""
from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path
from urllib.parse import quote_plus

import dlt
import sqlalchemy as sa
from dlt.sources.sql_database import sql_table
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Types geography non reconnus par SQLAlchemy : colonnes exclues de toute façon
warnings.filterwarnings("ignore", message="Did not recognize type")

PIPELINE_NAME = "wwi_sqlserver_to_snowflake"
DATASET_NAME = "bronze"  # -> schéma WWI_DB.BRONZE

# Tables sources (schéma.table) - hors tables d'archive des tables temporelles
TABLES: list[str] = [
    # Application (référentiels)
    "Application.Cities",
    "Application.Countries",
    "Application.DeliveryMethods",
    "Application.PaymentMethods",
    "Application.People",
    "Application.StateProvinces",
    "Application.TransactionTypes",
    # Purchasing (achats)
    "Purchasing.PurchaseOrderLines",
    "Purchasing.PurchaseOrders",
    "Purchasing.SupplierCategories",
    "Purchasing.Suppliers",
    "Purchasing.SupplierTransactions",
    # Sales (ventes)
    "Sales.BuyingGroups",
    "Sales.CustomerCategories",
    "Sales.Customers",
    "Sales.CustomerTransactions",
    "Sales.InvoiceLines",
    "Sales.Invoices",
    "Sales.OrderLines",
    "Sales.Orders",
    "Sales.SpecialDeals",
    # Warehouse (stocks)
    "Warehouse.Colors",
    "Warehouse.PackageTypes",
    "Warehouse.StockGroups",
    "Warehouse.StockItemHoldings",
    "Warehouse.StockItems",
    "Warehouse.StockItemStockGroups",
    "Warehouse.StockItemTransactions",
    # Historique des tables temporelles (versions passées) -> dimensions SCD2
    "Sales.Customers_Archive",
    "Warehouse.StockItems_Archive",
]

EXCLUDED_TYPES = ("GEOGRAPHY", "GEOMETRY", "VARBINARY", "IMAGE", "BINARY")
CURSOR_COLUMNS = ("LastEditedWhen", "ValidFrom")


def mssql_engine() -> sa.Engine:
    driver = quote_plus(os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server"))
    host = os.getenv("MSSQL_HOST", "localhost")
    database = os.getenv("MSSQL_DATABASE", "WideWorldImporters")
    user = os.getenv("MSSQL_USER")
    password = os.getenv("MSSQL_PASSWORD")
    auth = f"{quote_plus(user)}:{quote_plus(password)}@" if user else ""
    trusted = "" if user else "&trusted_connection=yes"
    url = (
        f"mssql+pyodbc://{auth}{host}/{database}"
        f"?driver={driver}&TrustServerCertificate=yes{trusted}"
    )
    # NullPool : DLT ouvre une connexion par table extraite en parallèle
    return sa.create_engine(url, poolclass=sa.pool.NullPool)


def snowflake_destination():
    return dlt.destinations.snowflake(
        credentials={
            "host": os.environ["SNOWFLAKE_ACCOUNT"],
            "username": os.environ["SNOWFLAKE_USER"],
            "password": os.environ["SNOWFLAKE_PASSWORD"],
            "database": os.environ["SNOWFLAKE_DATABASE"],
            "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
            "role": os.environ["SNOWFLAKE_ROLE"],
        }
    )


def drop_unsupported_columns(table: sa.Table) -> None:
    """Retire les colonnes spatiales / binaires avant l'extraction."""
    for col in list(table.columns):
        if str(col.type).upper().startswith(EXCLUDED_TYPES) or isinstance(col.type, sa.types.NullType):
            table._columns.remove(col)


def build_resources(engine: sa.Engine, tables: list[str]):
    inspector = sa.inspect(engine)
    for full_name in tables:
        schema, name = full_name.split(".")
        columns = {c["name"] for c in inspector.get_columns(name, schema=schema)}
        pk = inspector.get_pk_constraint(name, schema=schema)["constrained_columns"]
        # Incrémental uniquement avec une clé de fusion : sans clé, un "replace"
        # incrémental écraserait la table avec les seules nouvelles lignes
        cursor = next((c for c in CURSOR_COLUMNS if c in columns), None) if pk else None

        resource = sql_table(
            credentials=engine,
            table=name,
            schema=schema,
            backend="pyarrow",
            reflection_level="full",
            table_adapter_callback=drop_unsupported_columns,
            incremental=dlt.sources.incremental(cursor) if cursor else None,
        )
        # Nom cible : sales_invoice_lines, warehouse_stock_items, ...
        resource = resource.with_name(f"{schema}_{name}")
        if cursor:
            resource.apply_hints(write_disposition="merge", primary_key=pk)
        else:
            resource.apply_hints(write_disposition="replace")
        yield resource


@dlt.source(name="wwi_sqlserver")
def wwi_source(tables: list[str] | None = None):
    """Source DLT regroupant toutes les tables WWI (utilisée aussi par Dagster)."""
    yield from build_resources(mssql_engine(), tables or TABLES)


def make_pipeline(progress: str | None = "log") -> dlt.Pipeline:
    return dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination=snowflake_destination(),
        dataset_name=DATASET_NAME,
        progress=progress,
    )


def run(tables: list[str] | None = None, full_refresh: bool = False):
    pipeline = make_pipeline()
    # drop_resources : supprime les tables ciblées et réinitialise leur état incrémental
    info = pipeline.run(
        wwi_source(tables),
        refresh="drop_resources" if full_refresh else None,
    )
    print(info)
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tables", nargs="*", help="Sous-ensemble de tables (ex. Sales.Orders)")
    parser.add_argument("--full-refresh", action="store_true", help="Recharge complète")
    args = parser.parse_args()
    run(args.tables, args.full_refresh)
