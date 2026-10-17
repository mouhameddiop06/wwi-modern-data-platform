"""
Moteur text-to-SQL : question en langage naturel -> Cortex Analyst -> SQL -> résultats.

- Cortex Analyst (API REST Snowflake) génère le SQL à partir du modèle sémantique
  `semantic_model.yaml` décrivant la couche GOLD.
- Le SQL est contrôlé (lecture seule) puis exécuté avec le rôle WWI_ANALYST,
  qui ne peut lire que le schéma GOLD.

Le même code fonctionne :
  - en local (connecteur Python + identifiants du fichier .env) ;
  - dans Streamlit in Snowflake (session active + API interne `_snowflake`).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pandas as pd

try:  # module fourni uniquement par Streamlit in Snowflake
    import _snowflake  # type: ignore

    IN_SNOWFLAKE = True
except ImportError:
    IN_SNOWFLAKE = False

APP_DIR = Path(__file__).resolve().parent
SEMANTIC_MODEL = (APP_DIR / "semantic_model.yaml").read_text(encoding="utf-8")
ANALYST_ENDPOINT = "/api/v2/cortex/analyst/message"
MAX_ROWS = 10_000

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|create|alter|truncate|grant|revoke|call|copy|put|remove|use|execute)\b",
    re.IGNORECASE,
)


@dataclass
class AnalystAnswer:
    text: str = ""
    sql: str | None = None
    suggestions: list[str] = field(default_factory=list)
    request_id: str | None = None
    raw_content: list[dict] = field(default_factory=list)  # pour l'historique multi-tours


def parse_answer(body: dict) -> AnalystAnswer:
    content = body["message"]["content"]
    answer = AnalystAnswer(request_id=body.get("request_id"), raw_content=content)
    for item in content:
        if item["type"] == "text":
            answer.text += item["text"]
        elif item["type"] == "sql":
            answer.sql = item["statement"]
        elif item["type"] == "suggestions":
            answer.suggestions = item["suggestions"]
    return answer


def check_read_only(sql: str) -> None:
    """Refuse toute requête qui n'est pas une simple lecture."""
    stripped = re.sub(r"--[^\n]*|/\*.*?\*/", "", sql, flags=re.DOTALL).strip().rstrip(";")
    if ";" in stripped:
        raise ValueError("Une seule instruction SQL est autorisée.")
    if not re.match(r"^(with|select)\b", stripped, re.IGNORECASE):
        raise ValueError("Seules les requêtes SELECT sont autorisées.")
    if FORBIDDEN.search(stripped):
        raise ValueError("La requête contient une instruction non autorisée.")


def to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Les NUMBER Snowflake arrivent en Decimal : conversion pour les graphiques."""
    for col in df.columns:
        if df[col].dtype == object and len(df.dropna(subset=[col])):
            if isinstance(df[col].dropna().iloc[0], Decimal):
                df[col] = df[col].astype(float)
    return df


# ---------------------------------------------------------------- local
class LocalBackend:
    """Exécution sur le poste : connecteur Snowflake + appel REST."""

    name = "local"

    def __init__(self) -> None:
        from dotenv import load_dotenv

        load_dotenv(APP_DIR.parent / ".env")
        self.conn = None
        self.connect()

    def connect(self) -> None:
        import snowflake.connector

        self.conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.getenv("SNOWFLAKE_APP_USER", os.environ["SNOWFLAKE_USER"]),
            password=os.getenv("SNOWFLAKE_APP_PASSWORD", os.environ["SNOWFLAKE_PASSWORD"]),
            role=os.getenv("SNOWFLAKE_APP_ROLE", "WWI_ANALYST"),
            warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
            database=os.environ.get("SNOWFLAKE_DATABASE", "WWI_DB"),
            schema="GOLD",
            client_session_keep_alive=True,
        )

    def _retry_on_expiry(self, fn, *args):
        try:
            return fn(*args)
        except Exception as exc:  # noqa: BLE001
            if any(s in str(exc) for s in ("390112", "401", "expired", "Authentication token")):
                self.connect()
                return fn(*args)
            raise

    def ask(self, messages: list[dict]) -> AnalystAnswer:
        return self._retry_on_expiry(self._ask, messages)

    def _ask(self, messages: list[dict]) -> AnalystAnswer:
        import requests

        host = self.conn.host or f"{os.environ['SNOWFLAKE_ACCOUNT']}.snowflakecomputing.com"
        resp = requests.post(
            f"https://{host}{ANALYST_ENDPOINT}",
            headers={
                "Authorization": f'Snowflake Token="{self.conn.rest.token}"',
                "Content-Type": "application/json",
            },
            json={"messages": messages, "semantic_model": SEMANTIC_MODEL},
            timeout=120,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Cortex Analyst a répondu {resp.status_code} : {resp.text[:500]}")
        return parse_answer(resp.json())

    def run_sql(self, sql: str) -> pd.DataFrame:
        check_read_only(sql)
        return self._retry_on_expiry(self._run_sql, sql)

    def _run_sql(self, sql: str) -> pd.DataFrame:
        with self.conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchmany(MAX_ROWS)
            cols = [c[0] for c in cur.description]
        return to_numeric(pd.DataFrame(rows, columns=cols))


# ---------------------------------------------------------------- Snowflake
class SnowflakeBackend:
    """Exécution dans Streamlit in Snowflake : aucun identifiant à gérer."""

    name = "snowflake"

    def __init__(self) -> None:
        from snowflake.snowpark.context import get_active_session

        self.session = get_active_session()

    def ask(self, messages: list[dict]) -> AnalystAnswer:
        resp = _snowflake.send_snow_api_request(
            "POST", ANALYST_ENDPOINT, {}, {},
            {"messages": messages, "semantic_model": SEMANTIC_MODEL},
            None, 120_000,
        )
        body = json.loads(resp["content"])
        if resp["status"] >= 400:
            raise RuntimeError(f"Cortex Analyst a répondu {resp['status']} : {body.get('message', body)}")
        return parse_answer(body)

    def run_sql(self, sql: str) -> pd.DataFrame:
        check_read_only(sql)
        rows = self.session.sql(sql).limit(MAX_ROWS).collect()
        df = pd.DataFrame([r.as_dict() for r in rows])
        return to_numeric(df)


def get_backend():
    return SnowflakeBackend() if IN_SNOWFLAKE else LocalBackend()
