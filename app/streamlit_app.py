"""
WWI Insights — interrogez les données Wide World Importers en langage naturel.

Question (français) -> Snowflake Cortex Analyst -> SQL sur la couche GOLD -> tableau + graphique

    streamlit run app/streamlit_app.py
"""
import re

import altair as alt
import pandas as pd
import streamlit as st

from cortex_analyst import ask_analyst, connect, run_sql

st.set_page_config(page_title="WWI Insights", page_icon="📊", layout="wide")

TIME_RE = re.compile(r"date|mois|month|jour|day|ann[ée]e|year|semaine|week|trimestre|quarter|periode|period", re.I)

EXAMPLES = [
    "Quels sont les dix meilleurs clients par chiffre d'affaires ?",
    "Quel est le montant total des ventes par mois ?",
    "Quels produits génèrent le plus de bénéfices ?",
    "Quel est le taux de marge par territoire commercial en 2015 ?",
    "Quel est le chiffre d'affaires par catégorie de client et par année ?",
    "Quels commerciaux ont réalisé le plus de ventes en 2016 ?",
    "Quels produits sont sous le seuil de réapprovisionnement ?",
    "Quel est le montant total des achats par fournisseur ?",
]


# ------------------------------------------------------------------ connexion
@st.cache_resource(show_spinner="Connexion à Snowflake…")
def get_connection():
    return connect()


def with_reconnect(fn, *args):
    """Rejoue l'appel une fois avec une nouvelle connexion si la session a expiré."""
    try:
        return fn(get_connection(), *args)
    except Exception as exc:  # noqa: BLE001
        if any(s in str(exc) for s in ("390112", "401", "expired", "Authentication token")):
            get_connection.clear()
            return fn(get_connection(), *args)
        raise


# ------------------------------------------------------------------ affichage
def clean_interpretation(text: str) -> str:
    text = text.replace("This is our interpretation of your question:", "").strip()
    return text


def render_chart(df: pd.DataFrame) -> None:
    """Choisit automatiquement un graphique adapté aux résultats."""
    if df.empty:
        return
    # Les colonnes numériques temporelles (année, mois...) ou identifiants sont des axes, pas des mesures
    numeric = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and not TIME_RE.search(c) and not c.upper().endswith("_ID")
    ]
    others = [c for c in df.columns if c not in numeric]

    # Une seule valeur -> indicateur
    if len(df) == 1 and len(numeric) >= 1 and len(df.columns) <= 3:
        cols = st.columns(len(numeric))
        for col, name in zip(cols, numeric):
            col.metric(name.replace("_", " ").capitalize(), f"{df[name].iloc[0]:,.2f}".replace(",", " "))
        return
    if not numeric or not others:
        return

    # Axe X : de préférence une colonne temporelle ; couleur : l'autre dimension éventuelle
    time_cols = [c for c in others if TIME_RE.search(c) or pd.api.types.is_datetime64_any_dtype(df[c])]
    x = time_cols[0] if time_cols else others[0]
    y = numeric[0]
    is_time = bool(time_cols)
    color = next((c for c in others if c != x), None)

    if is_time:
        data = df.copy()
        if not pd.api.types.is_numeric_dtype(data[x]):  # une année (2015) reste un axe ordinal
            try:
                data[x] = pd.to_datetime(data[x])
            except (ValueError, TypeError):
                pass
        chart = alt.Chart(data).mark_line(point=True).encode(
            x=alt.X(f"{x}:T" if pd.api.types.is_datetime64_any_dtype(data[x]) else f"{x}:O", title=x),
            y=alt.Y(f"{y}:Q", title=y),
            color=alt.Color(f"{color}:N") if color else alt.value("#1f77b4"),
            tooltip=list(df.columns),
        )
    else:
        data = df.head(30)
        chart = alt.Chart(data).mark_bar().encode(
            y=alt.Y(f"{x}:N", sort="-x", title=x),
            x=alt.X(f"{y}:Q", title=y),
            color=alt.Color(f"{color}:N") if color else alt.value("#1f77b4"),
            tooltip=list(df.columns),
        )
    st.altair_chart(chart.properties(height=420), use_container_width=True)


def render_answer(msg: dict, key: str) -> None:
    if msg.get("error"):
        st.error(msg["error"])
        return
    if msg.get("text"):
        st.markdown(f"**Interprétation :** {clean_interpretation(msg['text'])}")
    if msg.get("sql"):
        with st.expander("Voir la requête SQL générée"):
            st.code(msg["sql"], language="sql")
    df = msg.get("df")
    if df is not None:
        if df.empty:
            st.info("La requête n'a renvoyé aucun résultat.")
        else:
            tab_chart, tab_table = st.tabs(["📈 Graphique", "📋 Tableau"])
            with tab_chart:
                render_chart(df)
            with tab_table:
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Télécharger en CSV", df.to_csv(index=False).encode("utf-8"),
                    file_name="resultats.csv", mime="text/csv", key=f"dl_{key}",
                )
    for i, sug in enumerate(msg.get("suggestions", [])):
        if st.button(sug, key=f"sug_{key}_{i}"):
            st.session_state.pending = sug
            st.rerun()


# ------------------------------------------------------------------ état
if "history" not in st.session_state:
    st.session_state.history = []      # messages au format Cortex Analyst
    st.session_state.display = []      # messages affichés (avec résultats)
    st.session_state.pending = None


def process(question: str) -> None:
    st.session_state.history.append({"role": "user", "content": [{"type": "text", "text": question}]})
    st.session_state.display.append({"role": "user", "text": question})
    msg = {"role": "assistant"}
    try:
        answer = with_reconnect(ask_analyst, st.session_state.history)
        st.session_state.history.append({"role": "analyst", "content": answer.raw_content})
        msg.update(text=answer.text, sql=answer.sql, suggestions=answer.suggestions)
        if answer.sql:
            msg["df"] = with_reconnect(run_sql, answer.sql)
    except Exception as exc:  # noqa: BLE001
        st.session_state.history.pop()  # garde un historique alterné user/analyst valide
        msg["error"] = f"Impossible de répondre à cette question : {exc}"
    st.session_state.display.append(msg)


# ------------------------------------------------------------------ barre latérale
with st.sidebar:
    st.header("📊 WWI Insights")
    st.caption("Posez vos questions en français : Cortex AI génère le SQL, l'exécute sur la couche **Gold** "
               "de Snowflake et affiche les résultats.")
    st.subheader("Exemples")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex
    st.divider()
    if st.button("🧹 Nouvelle conversation", use_container_width=True):
        st.session_state.history, st.session_state.display = [], []
        st.rerun()
    st.caption("Données : Wide World Importers (2013 – mai 2016), montants en USD.  \n"
               "Accès en lecture seule (rôle WWI_ANALYST).")

# ------------------------------------------------------------------ page principale
st.title("Interrogez vos données en langage naturel")

if not st.session_state.display:
    st.info("Exemple : *« Quel est le chiffre d'affaires par catégorie de client et par année ? »*")

for i, msg in enumerate(st.session_state.display):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["text"])
        else:
            render_answer(msg, key=str(i))

question = st.chat_input("Posez votre question…")
if st.session_state.pending:
    question, st.session_state.pending = st.session_state.pending, None

if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Cortex AI analyse votre question…"):
            process(question)
        render_answer(st.session_state.display[-1], key=str(len(st.session_state.display) - 1))
