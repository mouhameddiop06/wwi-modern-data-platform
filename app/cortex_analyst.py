"""
Moteur text-to-SQL : question en langage naturel -> Cortex Analyst -> SQL -> résultats.

- Cortex Analyst (API REST Snowflake) génère le SQL à partir du modèle sémantique
  `semantic_model.yaml` décrivant la couche GOLD.
- Le SQL est contrôlé (lecture seule) puis exécuté avec le rôle WWI_ANALYST,
  qui ne peut lire que le schéma GOLD.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests
import snowflake.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SEMANTIC_MODEL = (Path(__file__).parent / "semantic_model.yaml").read_text(encoding="utf-8")
ANALYST_ENDPOINT = "/api/v2/cortex/analyst/message"
MAX_ROWS = 10_000

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|create|alter|truncate|grant|revoke|call|copy|put|remove|use|execute)\b",
    re.IGNORECASE,
)


def connect() -> snowflake.connector.SnowflakeConnection:
    """Connexion Snowflake avec le rôle analyste (lecture seule sur GOLD)."""
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.getenv("SNOWFLAKE_APP_USER", os.environ["SNOWFLAKE_USER"]),
        password=os.getenv("SNOWFLAKE_APP_PASSWORD", os.environ["SNOWFLAKE_PASSWORD"]),
        role=os.getenv("SNOWFLAKE_APP_ROLE", "WWI_ANALYST"),
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ.get("SNOWFLAKE_DATABASE", "WWI_DB"),
        schema="GOLD",
        client_session_keep_alive=True,
    )


@dataclass
class AnalystAnswer:
    text: str = ""
    sql: str | None = None
    suggestions: list[str] = field(default_factory=list)
    request_id: str | None = None
    raw_content: list[dict] = field(default_factory=list)  # pour l'historique multi-tours


def ask_analyst(conn, messages: list[dict]) -> AnalystAnswer:
    """Envoie la conversation à Cortex Analyst et renvoie texte + SQL proposé."""
    host = conn.host or f"{os.environ['SNOWFLAKE_ACCOUNT']}.snowflakecomputing.com"
    resp = requests.post(
        f"https://{host}{ANALYST_ENDPOINT}",
        headers={
            "Authorization": f'Snowflake Token="{conn.rest.token}"',
            "Content-Type": "application/json",
        },
        json={"messages": messages, "semantic_model": SEMANTIC_MODEL},
        timeout=120,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Cortex Analyst a répondu {resp.status_code} : {resp.text[:500]}")

    body = resp.json()
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


def run_sql(conn, sql: str) -> pd.DataFrame:
    check_read_only(sql)
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchmany(MAX_ROWS)
        cols = [c[0] for c in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    # Les NUMBER Snowflake arrivent en Decimal : conversion pour les graphiques
    for col in df.columns:
        if df[col].dtype == object and len(df) and type(df[col].dropna().iloc[0]).__name__ == "Decimal":
            df[col] = df[col].astype(float)
    return df
