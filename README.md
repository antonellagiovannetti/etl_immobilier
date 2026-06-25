# Projet ETL Immobilier

## Présentation du projet

Ce projet est un projet scolaire d’ETL appliqué à des données immobilières.

L’objectif est de récupérer des données immobilières depuis une ou plusieurs sources, puis de les nettoyer, les transformer et les charger dans un format exploitable.

Pour que tous les membres du groupe travaillent dans les mêmes conditions, il est obligatoire de créer un environnement Python dédié au projet.

---

## 1. Création de l’environnement

Chaque utilisateur doit créer un environnement nommé `immobilier`.

```bash
conda create -n immobilier python=3.11
```
## 2. Activation de l’environnement

Avant de travailler sur le projet, il faut toujours activer l’environnement :

```bash
conda activate immobilier
```

## 3. Installation des dépendances

Le fichier requirements.txt est déjà fourni dans le projet.

Une fois l’environnement activé, il suffit d’installer les dépendances avec la commande suivante :

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
├── notebooks/        # Notebooks d’exploration
│
├── src/
│   ├── extract.py    # Extraction des données
│   ├── transform.py  # Transformation et nettoyage
│   ├── kpi.py        # KPIs
│   └── load.py       # Chargement des données
│
├── requirements.txt
└── README.md
```