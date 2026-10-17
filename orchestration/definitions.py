"""
Orchestration Dagster de la Modern Data Platform WWI.

    Bronze (assets DLT)  ->  Silver (modèles dbt)  ->  Gold (modèles dbt)

- Les tables Bronze ont pour clé ["bronze", <table>] : la même clé que les
  sources dbt, ce qui relie automatiquement DLT et dbt dans le lignage.
- Les tests dbt apparaissent comme des contrôles qualité (asset checks).
- Un job quotidien rejoue toute la chaîne, avec reprise automatique sur erreur.

Lancement : .\\dagster.ps1   (interface sur http://localhost:3000)
"""
import os
import re
import sys
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetSelection,
    AssetSpec,
    DefaultScheduleStatus,
    Definitions,
    RetryPolicy,
    ScheduleDefinition,
    define_asset_job,
)
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets
from dagster_dlt import DagsterDltResource, DagsterDltTranslator, dlt_assets
from dagster_dlt.translator import DltResourceTranslatorData
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")  # identifiants Snowflake pour DLT et dbt

# `dbt` doit être trouvable même si l'environnement virtuel n'est pas activé
# (utilisé par prepare_if_dev pour régénérer le manifest)
VENV_BIN = Path(sys.executable).parent
if str(VENV_BIN) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{VENV_BIN}{os.pathsep}{os.environ.get('PATH', '')}"

from ingestion.wwi_pipeline import make_pipeline, wwi_source  # noqa: E402
from orchestration.alerts import (  # noqa: E402
    gold_freshness_checks,
    gold_freshness_sensor,
    wwi_run_failure_alert,
)

# =====================================================================
# BRONZE : ingestion DLT SQL Server -> Snowflake
# =====================================================================


def snake(name: str) -> str:
    """Sales_InvoiceLines -> sales_invoice_lines (convention de nommage DLT)."""
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


class BronzeTranslator(DagsterDltTranslator):
    def get_asset_spec(self, data: DltResourceTranslatorData) -> AssetSpec:
        spec = super().get_asset_spec(data)
        return spec.replace_attributes(
            key=AssetKey(["bronze", snake(data.resource.name)]),
            deps=[],
            group_name="bronze",
            kinds={"dlt", "sqlserver", "snowflake"},
        )


@dlt_assets(
    dlt_source=wwi_source(),
    dlt_pipeline=make_pipeline(progress=None),
    name="wwi_bronze",
    dagster_dlt_translator=BronzeTranslator(),
)
def bronze_assets(context: AssetExecutionContext, dlt: DagsterDltResource):
    yield from dlt.run(context=context)


# =====================================================================
# SILVER / GOLD : transformations dbt
# =====================================================================

DBT_DIR = ROOT / "transform" / "wwi_dbt"
dbt_project = DbtProject(project_dir=DBT_DIR, profiles_dir=DBT_DIR)
dbt_project.prepare_if_dev()  # régénère le manifest en mode `dagster dev`


class MedallionDbtTranslator(DagsterDbtTranslator):
    """Clés ["silver", modèle] / ["gold", modèle] et groupes par couche."""

    def get_asset_spec(self, manifest, unique_id, project):
        spec = super().get_asset_spec(manifest, unique_id, project)
        node = manifest["nodes"].get(unique_id)
        if node and node["resource_type"] in ("model", "snapshot"):
            # dossier du modèle (silver / gold) ; les snapshots d'historisation vont en silver
            layer = node["fqn"][1] if node["resource_type"] == "model" else "silver"
            spec = spec.replace_attributes(
                key=AssetKey([layer, node["name"]]),
                group_name=layer,
            )
        return spec


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    dagster_dbt_translator=MedallionDbtTranslator(),
)
def dbt_medallion_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    # `build` = modèles + tests, dans l'ordre des dépendances
    yield from dbt.cli(["build"], context=context).stream()


# =====================================================================
# JOB + PLANIFICATION
# =====================================================================

wwi_daily_job = define_asset_job(
    name="wwi_daily_job",
    description="Chaîne complète : ingestion Bronze (DLT) puis Silver et Gold (dbt).",
    selection=AssetSelection.all(),
    op_retry_policy=RetryPolicy(max_retries=2, delay=60),  # reprise sur erreur
)

wwi_daily_schedule = ScheduleDefinition(
    name="wwi_daily_schedule",
    job=wwi_daily_job,
    cron_schedule="0 6 * * *",  # tous les jours à 06:00
    execution_timezone="Africa/Dakar",
    default_status=DefaultScheduleStatus.RUNNING,
)

defs = Definitions(
    assets=[bronze_assets, dbt_medallion_assets],
    asset_checks=gold_freshness_checks,
    jobs=[wwi_daily_job],
    schedules=[wwi_daily_schedule],
    sensors=[wwi_run_failure_alert, gold_freshness_sensor],
    resources={
        "dlt": DagsterDltResource(),
        "dbt": DbtCliResource(
            project_dir=dbt_project,
            profiles_dir=DBT_DIR,
            dbt_executable=str(VENV_BIN / ("dbt.exe" if os.name == "nt" else "dbt")),
        ),
    },
)
