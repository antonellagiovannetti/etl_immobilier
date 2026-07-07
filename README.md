# ETL Immobilier — où investir en France en 2026 ?

Projet d'école (Master Data & IA, M1 — Ynov) qui répond à une vraie question d'investisseur :
**dans quelle commune française acheter pour louer, en 2026 ?**

Le pipeline agrège plus de 9 millions de transactions immobilières (DVF) avec les loyers, les
revenus fiscaux, le taux de vacance des logements, la démographie et le contexte du crédit
(taux d'intérêt, endettement) pour calculer un **score d'attractivité par commune**, exposé
dans un dashboard Streamlit interactif (carte, top 10 des communes, KPIs).

---

## Ce que fait le pipeline

1. **Extract** (`src/extract.py`, `src/API.py`) — récupère automatiquement les données depuis
   data.gouv.fr, l'INSEE, la Banque de France et geo.api.gouv.fr (voir [DATA_SOURCES.md](DATA_SOURCES.md)).
2. **Transform** (`src/transform.py`) — nettoie et normalise chaque source (voir [USAGE_GUIDE.md](USAGE_GUIDE.md)
   pour le détail du traitement des transactions).
3. **KPI** (`src/kpi.py`) — calcule rendement locatif, taux de vacance, effort fiscal, et le
   score d'attractivité final par commune.
4. **Load** (`src/load.py`) — charge les tables finales dans PostgreSQL.
5. **App** (`app/`) — dashboard Streamlit pour explorer les résultats.

---

## Démarrer en 5 minutes

### 1. Environnement Python

```bash
conda create -n immobilier python=3.11
conda activate immobilier
pip install -r requirements.txt
```

### 2. Base de données (PostgreSQL via Docker)

Il faut [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré.

Copier le modèle fourni et renseigner un identifiant/mot de passe Postgres (le fichier `.env`
n'est pas versionné) :

```bash
cp .env.example .env
```

Puis démarrer la base (le schéma `db/schema.sql` est appliqué automatiquement) :

```bash
docker compose up -d
```

> **Erreur fréquente** : `failed to connect to the docker API` → Docker Desktop n'est pas lancé.

### 3. Lancer l'application

```bash
streamlit run app/app.py
```

- Page **ETL demo** : lance le pipeline complet (extraction → transformation → KPI → chargement
  en base).
- Page **Dashboard** : top 10 des communes, carte interactive, indicateurs clés.

Pour explorer sans Streamlit, les notebooks `notebooks/etl_pipeline.ipynb` et
`notebooks/dashboard.ipynb` reproduisent le même pipeline en Jupyter.

---

## Structure du projet

```
etl_immobilier/
├── app/               # Application Streamlit (accueil, ETL demo, dashboard)
├── data/
│   ├── raw/           # Données brutes
│   └── final/         # Données transformées, prêtes à charger
├── db/                # Schéma PostgreSQL (schema.sql)
├── notebooks/         # Notebooks d'exploration et pipeline Jupyter
├── src/               # Modules extract / transform / kpi / load / API
├── requirements.txt
├── docker-compose.yml
└── .env.example
```

---

## Pour aller plus loin

- [DATA_SOURCES.md](DATA_SOURCES.md) — d'où vient chaque donnée, et comment elle est récupérée.
- [USAGE_GUIDE.md](USAGE_GUIDE.md) — détail de l'extraction/transformation des transactions.
