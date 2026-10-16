# Modern Data Platform WWI — Architecture Médaillon & Text-to-SQL avec Cortex AI

Projet M2 BI — FST / Département Maths-Info, Université Cheikh Anta Diop (encadrant : Dr Jean Gane SARR).

Plateforme de données moderne construite sur la base **Wide World Importers** (Microsoft) :
les données transactionnelles de SQL Server sont ingérées dans **Snowflake** avec **DLT**,
organisées en couches **Bronze / Silver / Gold** avec **dbt**, orchestrées par **Dagster**,
puis interrogées en **langage naturel** depuis une application **Streamlit** grâce à
**Snowflake Cortex Analyst**.

> « Quels sont les dix meilleurs clients par chiffre d'affaires ? » → SQL généré → tableau + graphique, sans écrire une ligne de SQL.

---

## Sommaire

1. [Architecture](#1-architecture)
2. [Structure du dépôt](#2-structure-du-dépôt)
3. [Prérequis](#3-prérequis)
4. [Installation pas à pas](#4-installation-pas-à-pas)
5. [Commandes du quotidien](#5-commandes-du-quotidien)
6. [Détail des couches](#6-détail-des-couches)
7. [Qualité des données](#7-qualité-des-données)
8. [Application Text-to-SQL](#8-application-text-to-sql)
9. [Sécurité](#9-sécurité)
10. [Limites et pistes d'amélioration](#10-limites-et-pistes-damélioration)
11. [Dépannage](#11-dépannage)

---

## 1. Architecture

```mermaid
flowchart LR
    subgraph SRC["Système source"]
        SQL[("SQL Server 2025<br/>WideWorldImporters<br/>(OLTP)")]
    end

    subgraph ORCH["Orchestration — Dagster"]
        direction LR
        DLT["DLT<br/>ingestion incrémentale"]
        DBT["dbt<br/>transformations + tests"]
    end

    subgraph SF["Snowflake — WWI_DB"]
        direction LR
        B[("BRONZE<br/>28 tables brutes")]
        S[("SILVER<br/>27 tables nettoyées")]
        G[("GOLD<br/>schéma en étoile<br/>6 dimensions · 6 faits")]
        CA{{"Cortex Analyst<br/>+ modèle sémantique"}}
    end

    subgraph APP["Restitution"]
        ST["Application Streamlit<br/>questions en français"]
        U(("Décideur"))
    end

    SQL -->|extraction| DLT -->|chargement| B
    B --> DBT --> S --> G
    U -->|question| ST -->|question + historique| CA
    CA -->|SQL généré| ST
    ST -->|exécution lecture seule<br/>rôle WWI_ANALYST| G
    G -->|résultats| ST -->|tableau + graphique| U
```

| Étape | Outil | Rôle |
|---|---|---|
| Source | SQL Server 2025 Developer | Base OLTP `WideWorldImporters` (ventes, achats, stocks, clients, fournisseurs, paiements) |
| Ingestion | DLT 1.31 | Extraction SQL Server → Snowflake `BRONZE`, chargement incrémental + merge |
| Stockage | Snowflake | Base `WWI_DB`, schémas `BRONZE`, `SILVER`, `GOLD`, entrepôt `WWI_WH` |
| Transformation | dbt-core 1.12 | Modèles SQL versionnés, documentés et testés (Silver puis Gold) |
| Orchestration | Dagster 1.13 | Lignage DLT → dbt, job quotidien, reprise sur erreur, contrôles qualité |
| IA | Snowflake Cortex Analyst | Traduction question en langage naturel → SQL sur la couche Gold |
| Interface | Streamlit | Conversation, SQL généré, graphiques automatiques, export CSV |

### Flux d'exécution quotidien (Dagster)

```mermaid
flowchart LR
    T(["Planning<br/>06:00 Africa/Dakar"]) --> J["wwi_daily_job"]
    J --> A1["Étape wwi_bronze<br/>28 assets DLT"]
    A1 --> A2["Étape dbt build<br/>27 Silver + 12 Gold"]
    A2 --> C["129 contrôles qualité<br/>(tests dbt)"]
    A1 -. échec .-> R["RetryPolicy<br/>2 tentatives / 60 s"]
    A2 -. échec .-> R
```

---

## 2. Structure du dépôt

```
projet_pratique_bi/
├── .env.example              # Modèle des paramètres de connexion (copier en .env)
├── requirements.txt          # Dépendances Python
├── dbt.ps1                   # Lance dbt avec les variables du .env
├── dagster.ps1               # Lance l'interface Dagster + le planificateur
├── streamlit.ps1             # Lance l'application Text-to-SQL
│
├── snowflake/
│   └── 00_setup.sql          # Entrepôt, base, schémas, rôles, utilisateur technique
│
├── ingestion/                # Couche BRONZE (DLT)
│   ├── wwi_pipeline.py       # Pipeline SQL Server -> Snowflake
│   └── check_bronze.py       # Réconciliation des volumes source / Bronze
│
├── transform/wwi_dbt/        # Couches SILVER et GOLD (dbt)
│   ├── dbt_project.yml
│   ├── profiles.yml          # Connexion Snowflake via variables d'environnement
│   ├── macros/               # clean_text, to_amount, dedup, generate_schema_name
│   ├── models/silver/        # 27 modèles slv_* + sources + tests
│   ├── models/gold/          # 6 dim_* + 6 fact_* + documentation + tests
│   └── tests/                # Tests métier (réconciliation, cohérence HT/TVA/TTC...)
│
├── orchestration/
│   └── definitions.py        # Assets DLT + dbt, job, planning, reprise sur erreur
│
└── app/                      # Application Text-to-SQL
    ├── streamlit_app.py      # Interface utilisateur
    ├── cortex_analyst.py     # Appel Cortex Analyst + exécution SQL sécurisée
    ├── semantic_model.yaml   # Modèle sémantique de la couche GOLD
    └── test_questions.py     # Test de bout en bout des questions de référence
```

---

## 3. Prérequis

| Composant | Version testée | Remarque |
|---|---|---|
| Windows | 11 | Scripts `.ps1` fournis ; adaptables sous Linux/macOS |
| Python | 3.13 | |
| SQL Server | 2025 Developer (2016 SP1 minimum) | Authentification Windows |
| Pilote ODBC | ODBC Driver 18 for SQL Server | |
| Snowflake | Compte d'essai Enterprise, AWS US West (Oregon) | Cortex Analyst disponible |
| Disque / RAM | 10 Go libres, 1,5 Go RAM pour SQL Server | |

---

## 4. Installation pas à pas

### 4.1 Restaurer la base WideWorldImporters

1. Télécharger **`WideWorldImporters-Full.bak`** (version OLTP) depuis la
   [page des versions Microsoft](https://github.com/Microsoft/sql-server-samples/releases/tag/wide-world-importers-v1.0).
   Ne pas prendre la version `DW` : l'entrepôt est reconstruit par ce projet.
2. Copier le fichier dans un dossier lisible par le service SQL Server
   (le dossier *Téléchargements* ne l'est pas), par exemple `C:\Users\Public\SQLBackups\`.
3. Restaurer :

```bash
sqlcmd -S localhost -E -C -Q "RESTORE DATABASE WideWorldImporters FROM DISK = N'C:\Users\Public\SQLBackups\WideWorldImporters-Full.bak' WITH MOVE 'WWI_Primary' TO N'C:\Program Files\Microsoft SQL Server\MSSQL17.MSSQLSERVER\MSSQL\DATA\WideWorldImporters.mdf', MOVE 'WWI_UserData' TO N'C:\Program Files\Microsoft SQL Server\MSSQL17.MSSQLSERVER\MSSQL\DATA\WideWorldImporters_UserData.ndf', MOVE 'WWI_Log' TO N'C:\Program Files\Microsoft SQL Server\MSSQL17.MSSQLSERVER\MSSQL\DATA\WideWorldImporters.ldf', MOVE 'WWI_InMemory_Data_1' TO N'C:\Program Files\Microsoft SQL Server\MSSQL17.MSSQLSERVER\MSSQL\DATA\WideWorldImporters_InMemory_Data_1', STATS = 10"
```

> Adapter `MSSQL17.MSSQLSERVER` au dossier de votre instance. L'option `-C` fait confiance
> au certificat local (nécessaire avec le pilote ODBC 18).

### 4.2 Préparer Snowflake

1. Créer un compte d'essai sur <https://signup.snowflake.com> (édition **Enterprise**, AWS, région US West ou US East).
2. Dans une feuille SQL Snowflake, ouvrir [`snowflake/00_setup.sql`](snowflake/00_setup.sql),
   **remplacer le mot de passe** de `WWI_PIPELINE_USER`, puis tout exécuter (*Run All*).

Le script crée :

| Objet | Nom |
|---|---|
| Entrepôt (XS, suspension auto 60 s) | `WWI_WH` |
| Base et schémas | `WWI_DB.BRONZE`, `WWI_DB.SILVER`, `WWI_DB.GOLD` |
| Rôle pipelines (lecture-écriture) | `WWI_ENGINEER` |
| Rôle application (lecture GOLD + Cortex) | `WWI_ANALYST` |
| Utilisateur technique | `WWI_PIPELINE_USER` |

### 4.3 Configurer le projet

```bash
copy .env.example .env
```

Renseigner dans `.env` l'identifiant du compte (`SNOWFLAKE_ACCOUNT`, format `ORGNAME-ACCOUNTNAME`)
et le mot de passe choisi (`SNOWFLAKE_PASSWORD`). Ce fichier est exclu de Git.

### 4.4 Installer l'environnement Python

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4.5 Premier chargement complet

```bash
.venv\Scripts\python.exe ingestion\wwi_pipeline.py
```

```bash
.\dbt.ps1 build
```

Ou, en une seule fois via Dagster :

```bash
.\dagster.ps1
```

puis, dans l'interface (<http://localhost:3000>) : **Jobs → wwi_daily_job → Materialize all**.

---

## 5. Commandes du quotidien

| Objectif | Commande |
|---|---|
| Ingestion incrémentale Bronze | `.venv\Scripts\python.exe ingestion\wwi_pipeline.py` |
| Ingestion de quelques tables | `.venv\Scripts\python.exe ingestion\wwi_pipeline.py --tables Sales.Orders Sales.Customers` |
| Rechargement complet Bronze | `.venv\Scripts\python.exe ingestion\wwi_pipeline.py --full-refresh` |
| Réconciliation SQL Server / Bronze | `.venv\Scripts\python.exe ingestion\check_bronze.py` |
| Construire et tester Silver + Gold | `.\dbt.ps1 build` |
| Seulement la couche Gold | `.\dbt.ps1 build --select gold` |
| Documentation et lignage dbt | `.\dbt.ps1 docs generate` puis `.\dbt.ps1 docs serve` |
| Interface Dagster + planning | `.\dagster.ps1` → <http://localhost:3000> |
| Exécuter le job sans interface | `$env:DAGSTER_HOME="$PWD\.dagster_home"; .venv\Scripts\dagster.exe job execute -m orchestration.definitions -d . -j wwi_daily_job` |
| Application Text-to-SQL | `.\streamlit.ps1` → <http://localhost:8501> |
| Tester les questions de référence | `cd app; ..\.venv\Scripts\python.exe test_questions.py` |

> Le planning quotidien ne se déclenche que lorsque `dagster.ps1` est lancé (il démarre le démon Dagster).

---

## 6. Détail des couches

### 6.1 Bronze — données brutes (DLT)

Fichier : [`ingestion/wwi_pipeline.py`](ingestion/wwi_pipeline.py)

- **28 tables** des schémas `Application`, `Purchasing`, `Sales`, `Warehouse`, nommées
  `<schéma>_<table>` en minuscules (ex. `sales_invoice_lines`).
- **Chargement incrémental** : les tables possédant `LastEditedWhen` ou `ValidFrom` (tables temporelles)
  ne rechargent que les lignes nouvelles ou modifiées, fusionnées (*merge*) sur la clé primaire.
  Les autres tables sont remplacées intégralement.
- **Colonnes exclues** : types spatiaux (`geography`) et binaires (photos, mots de passe hachés).
- Lecture via SQLAlchemy + pyarrow ; état incrémental conservé par DLT (`~/.dlt/pipelines`).

### 6.2 Silver — données nettoyées (dbt)

Dossier : [`transform/wwi_dbt/models/silver`](transform/wwi_dbt/models/silver) — **27 tables `slv_*`**.

| Règle | Mise en œuvre |
|---|---|
| Texte normalisé | `trim`, chaînes vides → `NULL` (macro `clean_text`) |
| Montants | `NUMBER(18,2)` (macro `to_amount`) |
| Booléens et quantités | valeurs manquantes → `false` / `0` |
| Dédoublonnage | version la plus récente par clé (macro `dedup`) |
| Règles métier | montant HT = quantité × prix unitaire ; TTC = `extended_price` |
| JSON | pays de fabrication extrait de `custom_fields` |
| Minimisation | coordonnées bancaires et identifiants de connexion exclus |

### 6.3 Gold — schéma en étoile (dbt)

Dossier : [`transform/wwi_dbt/models/gold`](transform/wwi_dbt/models/gold)

```mermaid
erDiagram
    FACT_SALES }o--|| DIM_CUSTOMER : customer_id
    FACT_SALES }o--|| DIM_PRODUCT : stock_item_id
    FACT_SALES }o--|| DIM_EMPLOYEE : salesperson_id
    FACT_SALES }o--|| DIM_CITY : delivery_city_id
    FACT_SALES }o--|| DIM_DATE : invoice_date
    FACT_ORDERS }o--|| DIM_CUSTOMER : customer_id
    FACT_ORDERS }o--|| DIM_PRODUCT : stock_item_id
    FACT_ORDERS }o--|| DIM_DATE : order_date
    FACT_PURCHASES }o--|| DIM_SUPPLIER : supplier_id
    FACT_PURCHASES }o--|| DIM_PRODUCT : stock_item_id
    FACT_CUSTOMER_TRANSACTIONS }o--|| DIM_CUSTOMER : customer_id
    FACT_STOCK_MOVEMENTS }o--|| DIM_PRODUCT : stock_item_id
    FACT_STOCK_HOLDINGS ||--|| DIM_PRODUCT : stock_item_id
    DIM_PRODUCT }o--|| DIM_SUPPLIER : supplier_id
    DIM_CUSTOMER }o--|| DIM_CITY : delivery_city_id
```

| Table | Grain | Lignes | Contenu |
|---|---|---|---|
| `fact_sales` | ligne de facture | 228 265 | CA HT, TVA, TTC, bénéfice, quantité |
| `fact_orders` | ligne de commande | 231 412 | quantités commandées / préparées, reliquats |
| `fact_purchases` | ligne de bon de commande fournisseur | 8 367 | quantités et montants d'achat |
| `fact_customer_transactions` | transaction client | 97 147 | factures, paiements, solde restant dû |
| `fact_stock_movements` | mouvement de stock | 236 667 | entrées / sorties |
| `fact_stock_holdings` | produit (photo actuelle) | 227 | stock, valeur, alerte de réapprovisionnement |
| `dim_date` | jour | 1 461 | année, trimestre, mois et jours en français |
| `dim_customer` | client | 663 | catégorie, groupement d'achat, territoire, pays |
| `dim_product` | produit | 227 | marque, couleur, groupe, fournisseur |
| `dim_supplier` | fournisseur | 13 | catégorie, pays, délai de paiement |
| `dim_employee` | employé | 19 | dont commerciaux |
| `dim_city` | ville | 37 940 | État, territoire commercial, pays, continent |

Les clés sont les identifiants naturels de la source (`customer_id`, `stock_item_id`…), ce qui
simplifie les jointures générées par l'IA.

---

## 7. Qualité des données

`.\dbt.ps1 build` exécute **170 nœuds** (39 modèles + tests) ; dans Dagster, les tests
apparaissent comme **129 contrôles qualité** rattachés aux tables.

| Type | Exemples |
|---|---|
| Unicité / non-nullité | clé de chaque table Silver et Gold |
| Intégrité référentielle | chaque fait pointe vers une dimension existante |
| Valeurs autorisées | `direction` ∈ {Entrée, Sortie} |
| Règles métier | HT + TVA = TTC ; quantités vendues > 0 ; dates couvertes par `dim_date` |
| Réconciliation | CA TTC Gold = CA TTC Bronze ; volumes SQL Server = Bronze (`check_bronze.py`) |

---

## 8. Application Text-to-SQL

```mermaid
sequenceDiagram
    actor U as Décideur
    participant ST as Streamlit
    participant CA as Cortex Analyst
    participant G as Snowflake GOLD
    U->>ST: « Quels produits génèrent le plus de bénéfices ? »
    ST->>CA: question + historique + modèle sémantique
    CA-->>ST: interprétation + SQL
    ST->>ST: contrôle lecture seule
    ST->>G: exécution (rôle WWI_ANALYST)
    G-->>ST: résultats
    ST-->>U: interprétation, SQL, graphique, tableau, CSV
```

- **Modèle sémantique** ([`app/semantic_model.yaml`](app/semantic_model.yaml)) : décrit les
  10 tables Gold, leurs relations, des synonymes français (« CA », « marge », « commercial »…),
  les indicateurs (`total_revenue`, `total_profit`, `margin_rate`…) et trois **requêtes vérifiées**
  correspondant aux questions du sujet.
- **Conversation** : les questions de suivi tiennent compte du contexte
  (« Et seulement pour les supermarchés, par mois en 2015 ? »).
- **Graphique automatique** : courbe pour une dimension temporelle, barres triées pour une
  catégorie, indicateur pour une valeur unique.

Exemples de questions :

- Quels sont les dix meilleurs clients par chiffre d'affaires ?
- Quel est le montant total des ventes par mois ?
- Quels produits génèrent le plus de bénéfices ?
- Quel est le taux de marge par territoire commercial en 2015 ?
- Quels commerciaux ont réalisé le plus de ventes en 2016 ?
- Quels produits sont sous le seuil de réapprovisionnement ?

> **Pourquoi Cortex Analyst plutôt que `CORTEX.COMPLETE` ?** Sur un compte d'essai Snowflake,
> les fonctions LLM génériques (`COMPLETE`, `AI_COMPLETE`, `AI_CLASSIFY`…) sont désactivées.
> Cortex Analyst, le service Snowflake dédié au text-to-SQL, reste disponible et produit un SQL
> plus fiable car guidé par le modèle sémantique.

---

## 9. Sécurité

- **Secrets** : uniquement dans `.env` (exclu de Git) ; jamais dans le code.
- **Moindre privilège** : l'application utilise le rôle `WWI_ANALYST`, limité à la **lecture du schéma GOLD**
  et à Cortex ; les pipelines utilisent `WWI_ENGINEER`.
- **SQL contrôlé** : avant exécution, l'application refuse tout ce qui n'est pas une instruction
  unique `SELECT` / `WITH` et tout mot-clé d'écriture (`INSERT`, `DROP`, `GRANT`…). Résultats limités à 10 000 lignes.
- **Données personnelles minimisées** dès la couche Silver (coordonnées bancaires, identifiants de connexion, photos exclus).

---

## 10. Limites et pistes d'amélioration

- Le compte d'essai expire après 30 jours / 400 $ de crédits.
- La couche Bronze conserve la dernière version des lignes ; l'historisation (SCD type 2) pourrait
  être ajoutée avec les *snapshots* dbt ou les tables d'archive temporelles de SQL Server.
- `dbt build` reconstruit toutes les tables ; des modèles `incremental` réduiraient le coût à grande échelle.
- Pistes : déploiement de l'application dans *Streamlit in Snowflake*, modèle sémantique publié
  comme *semantic view*, alertes Dagster (e-mail / Slack) en cas d'échec, CI GitHub Actions lançant `dbt build`.

---

## 11. Dépannage

| Symptôme | Cause / solution |
|---|---|
| `sqlcmd` : *certificate chain was issued by an authority that is not trusted* | Ajouter `-C` (ODBC 18 chiffre par défaut) |
| `RESTORE` : *Operating system error 5 (Accès refusé)* | Copier le `.bak` dans un dossier lisible par le service SQL (`C:\Users\Public\SQLBackups`) |
| DLT : *QueuePool limit of size 5 overflow 10 reached* | Déjà corrigé : le moteur utilise `NullPool` (une connexion par table extraite en parallèle) |
| Cortex : *AI function … is not available for trial accounts* | Normal sur un compte d'essai pour `COMPLETE` ; l'application utilise Cortex Analyst |
| Cortex Analyst : *Invalid semantic model yaml* | Une expression contenant une virgule doit être entre guillemets dans le YAML |
| Dagster : `manifest.json` introuvable | Lancer `.\dbt.ps1 parse` (ou passer par `.\dagster.ps1`, qui le régénère) |
| Les scripts `.ps1` sont bloqués | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
