# Sources de données du projet

Ce document explique, en langage simple, d'où viennent les données utilisées pour calculer
le score d'attractivité immobilière : quelle donnée, publiée par qui, sur quelle période, et
si elle a été complétée pour aller plus loin dans le temps.

Toutes les sources listées ici sont des **données publiques et gratuites** (open data),
publiées par des organismes officiels français.

## Vue d'ensemble

| Donnée | Utilisée pour | Période initiale | Complétée avec | Période finale |
|---|---|---|---|---|
| Transactions immobilières (DVF) | Prix au m², rendement | 2014 – 2024 | Etalab / DVF géolocalisées (`data.gouv.fr`) | **2014 – 2025** (continu) |
| Loyers par commune | Loyer moyen au m² | 2018, 2022, 2023 | "Carte des loyers" (Ministère du Logement, `data.gouv.fr`) | **2018, 2022 – 2025** *(2019-2021 non publiés par la source)* |
| Revenus des foyers fiscaux | Revenu fiscal moyen | 2014 – 2022 | IRCOM (DGFiP, `data.gouv.fr`) | **2014 – 2022, puis 2024** *(2023 non publié par la source)* |
| Logements vacants / parc immobilier | Taux de vacance | 2019 – 2021 | LOVAC (Cerema/DHUP, `data.gouv.fr`) | **2019 – 2025** (continu) |
| Indice de référence des loyers (IRL) | Révision annuelle des loyers | 2002 – 2024 | INSEE (API officielle) | **2002 – 2026** (continu) |
| Taux d'intérêt des crédits immobiliers | Contexte du marché du crédit | 2014 – 2024 | Banque de France (Webstat) | **2010 – 2026** (continu) |
| Flux de nouveaux crédits à l'habitat | Contexte du marché du crédit | 2010 – 2024 | Banque de France (Webstat) | **2010 – 2026** (continu) |
| Taux d'endettement des ménages | Contexte du marché du crédit | 2012 – 2022 | Banque de France (Webstat) | **1999 – 2025** (continu) |
| Données géographiques et démographiques | Coordonnées, population, densité | — (pas de date fixe) | API officielle du gouvernement (`geo.api.gouv.fr`) | Toujours à jour |

## Détail par source, avec lien vers le jeu de données exact

### 🏠 Transactions immobilières (DVF)
Les prix de vente immobiliers proviennent des **Demandes de Valeurs Foncières (DVF)**, la
base officielle qui enregistre toutes les ventes de biens immobiliers en France.
- Données historiques (2014-2024) : fichier fourni au démarrage du projet, dérivé du jeu
  [Demandes de valeurs foncières géolocalisées](https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees)
  (Etalab, mission gouvernementale pour l'ouverture des données publiques).
- Complément 2025 : même source, millésime 2025, téléchargé directement depuis
  [files.data.gouv.fr/geo-dvf](https://files.data.gouv.fr/geo-dvf/latest/csv/2025/full.csv.gz).
- 2026 n'est pas encore disponible : l'administration publie ces données avec environ
  **6 mois de retard**, ce n'est pas un manque de notre part.

### 🏡 Loyers
Les loyers moyens par commune viennent de la **"Carte des loyers"**, publiée chaque année
par le Ministère chargé du Logement, construite à partir d'annonces immobilières réelles.
Millésimes ajoutés pour compléter les données existantes (2018, 2022, 2023) :
- [Carte des loyers 2024](https://www.data.gouv.fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2024)
- [Carte des loyers 2025](https://www.data.gouv.fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025)

### 💶 Revenus des foyers fiscaux
Les revenus moyens par commune viennent d'**IRCOM** (Impôt sur le Revenu par Collectivité
territoriale), publié par la **DGFiP** (Direction Générale des Finances Publiques) :
[L'impôt sur le revenu par collectivité territoriale (IRCOM)](https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom)
— millésime "revenus 2024" ajouté (le plus récent publié).

**Limite connue** : l'administration fiscale publie toujours ces chiffres avec environ
**2 ans de retard** (les revenus 2025 ne seront connus qu'en 2027). Ce n'est pas un oubli,
c'est structurel — 2024 est donc la donnée la plus récente possible aujourd'hui.

### 🏘️ Logements vacants et parc de logements
Le taux de logements vacants vient de **LOVAC** (dispositif national de lutte contre les
logements vacants), piloté par le **Cerema** pour le compte du Ministère du Logement :
[Logements vacants du parc privé par commune, département, région, France, de 2020 à 2026](https://www.data.gouv.fr/datasets/logements-vacants-du-parc-prive-par-commune-departement-region-france-de-2020-a-2026)
— une des sources les plus à jour du projet, données jusqu'en 2025.

### 📈 Indice de référence des loyers (IRL)
Publié chaque trimestre par l'**INSEE**, cet indice sert de référence légale pour la
révision annuelle des loyers. Récupéré directement via l'API officielle SDMX de l'INSEE
(série n°[001515333](https://www.insee.fr/fr/statistiques/serie/001515333) — "Indice de
référence des loyers (IRL)"), toujours à jour automatiquement.

### 🏦 Taux d'intérêt, flux de crédits et taux d'endettement
Ces trois indicateurs sur le marché du crédit immobilier viennent de la **Banque de
France** (portail [Webstat](https://webstat.banque-france.fr)), récupérés manuellement
(le service d'automatisation de la Banque de France nécessite un compte développeur, ce
qui n'était pas justifié pour ce projet — le téléchargement direct depuis leur site reste
gratuit et ne nécessite aucun compte) :

- [Taux des crédits nouveaux à l'habitat (hors négociations) aux particuliers](https://webstat.banque-france.fr/fr/catalogue/MIR1/MIR1.M.FR.B.A22HR.A.R.A.2254U6.EUR.N)
- [Crédits nouveaux à l'habitat (hors renégociations) aux particuliers résidents, flux, CVS](https://webstat.banque-france.fr/fr/catalogue/MIR1/MIR1.M.FR.B.A22HR.A.5.A.2254U6.EUR.N)
- [Dette des ménages - France, en % du RDB](https://webstat.banque-france.fr/fr/catalogue/CNFSI/CNFSI.Q.S.FR.W0.S1M.S1.N.L.LE.DETT.T._Z.XDC_R_B6G_S1M._T.S.V.N._T)

### 🌍 Données géographiques et démographiques
Les coordonnées, la population et la superficie de chaque commune viennent de l'API
officielle du gouvernement française : [geo.api.gouv.fr](https://geo.api.gouv.fr/communes).
Cette source est interrogée en direct à chaque exécution du pipeline : elle est donc
**toujours à jour automatiquement**, sans mise à jour manuelle nécessaire.

---

*Pour le détail technique (requêtes, formats de fichiers, code utilisé), voir
`agent_information/data_sources.md`.*
