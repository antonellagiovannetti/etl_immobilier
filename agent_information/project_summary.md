# Résumé global du projet — ETL Immobilier

## Objectif
Projet d'école (Master Data & IA M1 — Ynov 2025-2026) répondant à la question métier :
« Dans quelle ville française acheter pour investir en 2026 ? »

Le pipeline ETL agrège des données immobilières et socio-économiques françaises
(transactions DVF, loyers, foyers fiscaux, parc immobilier, indicateurs macro,
démographie via l'API geo.api.gouv.fr) pour calculer un score d'attractivité par
commune, exposé ensuite dans une application Streamlit.

## Structure du dépôt
```
etl_immobilier/
├── app/                     # Application Streamlit
│   ├── app.py                # Page d'accueil
│   └── pages/
│       ├── 1_Dashboard.py    # Top 10 communes, carte, KPIs
│       └── 2_ETL_demo.py     # Démo du pipeline ETL
├── data/
│   ├── raw/                  # Données brutes (CSV + transactions.npz)
│   └── final/                # Données transformées prêtes à charger
├── db/
│   └── schema.sql            # Schéma PostgreSQL (schéma `operationnel`)
├── src/
│   ├── API.py                # Enrichissement communes via geo.api.gouv.fr
│   ├── extract.py             # Extraction des transactions (NPZ -> DataFrame)
│   ├── transform.py           # Nettoyage/transformation des transactions
│   ├── load.py                # Chargement des CSV finaux vers PostgreSQL
│   ├── kpi.py                  # Calculs des KPI et du score d'attractivité
│   └── Analyse_exploratoire/  # Notebooks d'exploration (Ala Eddine, Damien)
├── docker-compose.yml         # Conteneur PostgreSQL 15
├── requirements.txt
├── README.md                  # Setup env conda + Docker + guide d'utilisation
└── EXPLICATION_UTILISATION.md # Détail extraction/transformation des transactions
```

## Environnement technique
- Python 3.11 (environnement conda nommé `immobilier`)
- Dépendances clés : pandas, numpy, sqlalchemy, psycopg2-binary, streamlit,
  python-dotenv, jupyter, matplotlib/seaborn, openpyxl
- Base de données : PostgreSQL 15 via Docker Compose (`etl_immobilier_db`),
  schéma `operationnel`, initialisé automatiquement depuis `db/schema.sql`
- Configuration via fichier `.env` (non versionné), modèle dans `.env.example` :
  `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`,
  `POSTGRES_PORT`, `GEO_API_COMMUNES_URL`

## Modèle de données (schéma `operationnel`)
- `communes` — référentiel géographique (id_ville, département, ville, lat/long, code INSEE, code région)
- `demographics` — population, superficie, densité (source API geo.api.gouv.fr)
- `transactions` — transactions DVF (prix, prix_m2, surface, type de bâtiment, VEFA…)
- `loyers` — loyers médians par commune/année (appartement, maison, moyen)
- `foyers_fiscaux` — revenu fiscal moyen, impôt moyen par commune/année
- `parc_immobilier` — nombre de logements, logements vacants, taux de vacance
- `indicateurs_macro` — taux d'intérêt, flux d'emprunts, taux d'endettement, IRL (national, mensuel)
- `score_attractivite` — table finale : score d'attractivité par commune et année de référence

## Pipeline ETL
1. **Extract** (`src/extract.py`) : lit `data/raw/transactions.npz`, décode les
   colonnes texte stockées en `uint8` (séparateur `\x00`), renvoie un DataFrame pandas.
2. **Transform** (`src/transform.py`) : calcule `annee` et `prix_m2`, filtre les
   `prix_m2` hors de la plage [500, 30000], supprime les doublons, ne garde que
   les communes ayant ≥ 5 transactions entre 2022 et 2024, écrit
   `data/final/transactions.npz`.
3. **API communes** (`src/API.py`) : `recuperer_infos_communes(villes)` interroge
   geo.api.gouv.fr pour récupérer latitude/longitude, code INSEE, code région,
   population, superficie. Ne lit/n'écrit aucun fichier — reçoit une liste de
   villes et retourne un dict `{data, errors}`.
4. **KPI** (`src/kpi.py`) : calcule le rendement brut, le taux de vacance, le
   ratio d'effort fiscal, normalise ces indicateurs (0-100) puis calcule le
   score d'attractivité final pondéré : 35% rendement + 25% effort fiscal
   (inversé) + 20% richesse + 20% vacance (inversée).
5. **Load** (`src/load.py`) : charge les CSV finaux (`data/final/*.csv`) dans
   les tables PostgreSQL du schéma `operationnel` via SQLAlchemy (`to_sql`,
   append, chunksize 5000), puis vérifie le nombre de lignes insérées par table.
6. **App Streamlit** (`app/`) : page d'accueil + Dashboard (Top 10 communes,
   carte interactive, KPIs) + page ETL demo (en cours de développement).

Un futur module `pipeline.py` doit orchestrer extract → transform → load
pour l'ensemble des sources (actuellement seul le flux transactions est
branché de bout en bout).

## Historique de développement (commits notables)
- Initialisation, notebooks d'exploration, Docker Postgres, schema.sql
- Ajout table démographics + intégration API géo
- Ajout des utilitaires de calcul KPI (`src/kpi.py`)
- Ajout `load.py` pour charger les CSV nettoyés vers PostgreSQL
- Ajout de l'app Streamlit (accueil, dashboard, démo ETL)
- Chargement Postgres depuis `.env` + amélioration UI ETL
- Ajout du client API communes + documentation
- Ajout des modules extract/transform pour les transactions (dernier commit)

## Travail de groupe
Projet collaboratif (plusieurs contributeurs : Damien, Antonella, Ala Eddine…),
avec des branches par fonctionnalité et des pull requests fusionnées sur `main`.
La branche courante de travail est `Damien`.
