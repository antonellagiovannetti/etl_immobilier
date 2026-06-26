# Projet ETL Immobilier

## Présentation du projet

Ce projet est un projet d'école d'ETL appliqué à des données immobilières.

L'objectif est de récupérer des données immobilières depuis une ou plusieurs sources, puis de les nettoyer, les transformer et les charger dans un format exploitable.

Pour que tous les membres du groupe travaillent dans les mêmes conditions, il est obligatoire de créer un environnement Python dédié au projet.

---

## 1. Création de l'environnement

Chaque utilisateur doit créer un environnement nommé `immobilier`.

```bash
conda create -n immobilier python=3.11
```

## 2. Activation de l'environnement

Avant de travailler sur le projet, il faut toujours activer l'environnement :

```bash
conda activate immobilier
```

## 3. Installation des dépendances

Le fichier requirements.txt est déjà fourni dans le projet.

Une fois l'environnement activé, il suffit d'installer les dépendances avec la commande suivante :

```bash
pip install -r requirements.txt
```

## 4. Structure recommandée du projet

```
Projet_ETL_Immobilier/
│
├── data/
│   ├── raw/          # Données brutes
│   ├── cleaned/      # Données nettoyées
│   └── final/        # Données finales exploitables
│
├── notebooks/        # Notebooks d'exploration
│
├── src/
│   ├── API.py        # Enrichissement communes via geo.api.gouv.fr
│   ├── extract.py    # Extraction des données
│   ├── transform.py  # Transformation et nettoyage
│   ├── kpi.py        # KPIs
│   └── load.py       # Chargement des données
│
├── requirements.txt
└── README.md
```

---

## 5. Base de données PostgreSQL (Docker)

La base de données tourne dans un conteneur Docker. Chaque membre du groupe doit avoir **Docker Desktop** installé et lancé avant de démarrer.

### 5.1 Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et **démarré** (icône active dans la barre des tâches)

### 5.2 Fichier `.env`

Créer un fichier `.env` à la racine du projet (il n'est pas versionné sur Git) :

```env
POSTGRES_DB=etl_immobilier
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
GEO_API_COMMUNES_URL=https://geo.api.gouv.fr/communes
```

Un fichier `.env.example` est fourni dans le repo comme modèle.

### 5.3 Démarrer la base de données

```bash
docker compose up -d
```

Le schéma de la base est appliqué automatiquement au premier démarrage depuis `db/schema.sql`.

### 5.4 Vérifier que la base est opérationnelle

```bash
docker exec -it etl_immobilier_db psql -U admin -d etl_immobilier
```

Si la commande s'ouvre sur un prompt `etl_immobilier=#`, la base est prête.

> **Erreur fréquente** : `failed to connect to the docker API` → Docker Desktop n'est pas lancé. L'ouvrir et attendre que l'icône soit verte, puis relancer la commande.

### 5.5 Arrêter la base de données

```bash
docker compose down
```

Les données sont persistées dans un volume Docker et ne sont pas perdues à l'arrêt.

### 5.6 Connexion depuis Python

```python
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
```

---

## 6. Bloc API communes

Le fichier `src/API.py` contient un bloc de recuperation API. Il ne lit pas les fichiers du projet
et n'ecrit pas de fichier de sortie : une autre etape du pipeline lui fournit une liste de villes,
puis exploite le resultat retourne.

L'URL de l'API doit rester dans l'environnement :

```env
GEO_API_COMMUNES_URL=https://geo.api.gouv.fr/communes
```

### 6.1 Fonction disponible

```python
from src.API import recuperer_infos_communes

resultat = recuperer_infos_communes(["Lyon", "Paris"])
```

La fonction retourne un dictionnaire :

- `data` : communes trouvees avec les champs utiles.
- `errors` : villes non trouvees ou erreurs d'appel API.

### 6.2 Champs recuperes

- `latitude` : `centre.coordinates[1]`
- `longitude` : `centre.coordinates[0]`
- `code_insee` : `code`
- `code_region` : `codeRegion`
- `nom_region` : `region.nom`
- `population` : `population`
- `superficie_m2` : `surface * 10000`

La densite n'est pas recuperee depuis l'API. Elle sera calculee ensuite dans la partie KPI.
