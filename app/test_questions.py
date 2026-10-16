"""
Test de bout en bout du text-to-SQL sur les questions du sujet.

    python app/test_questions.py
"""
import sys
import warnings

warnings.filterwarnings("ignore")
from cortex_analyst import ask_analyst, connect, run_sql  # noqa: E402

QUESTIONS = sys.argv[1:] or [
    "Quels sont les dix meilleurs clients par chiffre d'affaires ?",
    "Quel est le montant total des ventes par mois ?",
    "Quels produits génèrent le plus de bénéfices ?",
    "Quel est le taux de marge par territoire commercial en 2015 ?",
    "Quels produits sont sous le seuil de réapprovisionnement ?",
]

conn = connect()
ok = 0
for q in QUESTIONS:
    print("=" * 80, "\nQ :", q)
    try:
        ans = ask_analyst(conn, [{"role": "user", "content": [{"type": "text", "text": q}]}])
        print("Cortex :", ans.text.strip()[:200])
        if not ans.sql:
            print("Pas de SQL. Suggestions :", ans.suggestions)
            continue
        df = run_sql(conn, ans.sql)
        print(f"{len(df)} ligne(s)\n", df.head(5).to_string(index=False))
        ok += 1
    except Exception as e:  # noqa: BLE001
        print("ERREUR :", e)
print(f"\n{ok}/{len(QUESTIONS)} questions traitées avec succès.")
