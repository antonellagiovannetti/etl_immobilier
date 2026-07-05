# Sources utilisées — Projet ETL Immobilier

## Fichiers de données brutes (`data/raw/`)

| Fichier | Colonnes principales | Granularité |
|---|---|---|
| `transactions.npz` / `transactions_sample.csv` | id_transaction, date_transaction, prix, departement, id_ville, ville, code_postal, adresse, type_batiment, vefa, n_pieces, surface_habitable, id_parcelle_cadastre, latitude, longitude, surfaces annexes (dépendances, locaux industriels, terrains agricoles/sols, nature) | par transaction |
| `loyers.csv` | departement, id_ville, ville, date, loyer_m2_appartement, loyer_m2_maison | par commune / année |
| `foyers_fiscaux.csv` | date, departement, id_ville, ville, n_foyers_fiscaux, revenu_fiscal_moyen, montant_impot_moyen, répartition par tranches de revenu (0-10k … 100k+) | par commune / année |
| `parc_immobilier.csv` | date, departement, id_ville, ville, n_logements, n_logements_vacants | par commune / année |
| `indice_reference_loyers.csv` | quarter, IRL | national / trimestre |
| `taux_interet.csv` | date, taux | national / mois |
| `taux_endettement.csv` | date, taux_endettement | national / année |
| `flux_nouveaux_emprunts.csv` | date, emprunts_M€ | national / mois |

Ces fichiers correspondent, d'après leur structure et leur nommage (colonnes en français,
granularité commune/INSEE, indicateurs macro nationaux), aux types de sources publiques
françaises habituellement utilisées pour ce genre d'analyse immobilière :
- Transactions immobilières : données de type DVF (Demandes de Valeurs Foncières).
- Foyers fiscaux / revenus : données de type INSEE (revenus fiscaux localisés).
- Parc immobilier / logements vacants : données de type INSEE (logements).
- Loyers : données de type observatoires des loyers.
- Taux d'intérêt, taux d'endettement, flux d'emprunts, IRL : données de type Banque de
  France / INSEE (indicateurs macroéconomiques nationaux).

Aucun fichier du dépôt ne cite explicitement l'origine exacte (URL, organisme, date
d'extraction) de ces CSV — cette section reste donc au niveau du constat observable dans
les fichiers, pas d'une source certifiée.

## API externe

**`geo.api.gouv.fr/communes`** (API Découpage administratif du gouvernement français)
- Utilisée dans `src/API.py` via `recuperer_infos_communes(villes)`.
- URL configurée par la variable d'environnement `GEO_API_COMMUNES_URL` (dans `.env`,
  modèle dans `.env.example`).
- Champs demandés à l'API : `nom, code, codeRegion, region, population, surface, centre`.
- Champs conservés après traitement (`_format_commune`) :
  - `latitude` / `longitude` (depuis `centre.coordinates`)
  - `code_insee` (`code`)
  - `code_region` (`codeRegion`)
  - `nom_region` (`region.nom`)
  - `population`
  - `superficie_m2` (`surface` en hectares × 10 000)
- La densité (habitants/km²) n'est pas fournie par l'API : elle est calculée ensuite dans
  `src/kpi.py` / la table `demographics`.

## Base de données

- PostgreSQL 15 (image Docker officielle `postgres:15`), schéma `operationnel` défini dans
  `db/schema.sql`, alimenté depuis les CSV finaux (`data/final/*.csv`) par `src/load.py`.

---

## Extension des données jusqu'en 2026 — Vérification des sources proposées (04/07/2026)

Contexte : les données actuelles s'arrêtent en 2024. Un agent de recherche a proposé une liste
de sources pour compléter chaque CSV jusqu'en 2026. Chaque source a été testée manuellement
(requêtes réelles, téléchargement d'un échantillon, inspection des colonnes) avant toute
intégration au pipeline. Statut détaillé ci-dessous — ✅ vérifié et exploitable, ⚠️ vérifié
mais accès restreint/limité, ❌ source cassée telle que fournie par l'agent de recherche.

### ✅ Transactions immobilières — remplace/complète `transactions.npz`

- **Source réelle testée** : Etalab / DVF géolocalisées — `https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/full.csv.gz`
  (et non les fichiers `valeursfoncieres-2024.txt` cités par l'agent, qui sont le format brut
  DGFiP non enrichi ; la version géolocalisée `geo-dvf` est plus directement exploitable).
- **Test effectué** : téléchargement de `2025/full.csv.gz` (~98 Mo compressés, 3 714 830 lignes),
  colonnes confirmées : `id_mutation, date_mutation, nature_mutation, valeur_fonciere,
  code_commune, nom_commune, type_local, surface_reelle_bati, nombre_pieces_principales,
  longitude, latitude…` — compatible avec le schéma `transactions` existant (mapping direct :
  `valeur_fonciere → prix`, `date_mutation → date_transaction`, `code_commune → id_ville`,
  `surface_reelle_bati → surface_habitable`, `nombre_pieces_principales → n_pieces`).
- **Couverture 2026** : confirmée absente (dossier `2026/` existe mais vide — `full.csv.gz`
  renvoie 404). Confirme la remarque de l'agent : décalage de publication d'environ 6 mois.
  → il faudra extrapoler/propager la tendance de fin 2025 pour le début 2026.
- **Verdict : source à intégrer.**

### ✅ Loyers — remplace/complète `loyers.csv`

- **Source réelle testée** : jeu de données data.gouv.fr *"Carte des loyers" - Indicateurs de
  loyers d'annonce par commune en 2025* (`id` data.gouv : `693aa2feed1bf4da603faa49`), mis à
  jour le 2025-12-11.
- **Test effectué** : téléchargement du CSV `pred-app-mef-dhup.csv` (indicateur loyer
  appartement), colonnes confirmées : `id_zone, INSEE_C, LIBGEO, EPCI, DEP, REG, loypredm2,
  lwr.IPm2, upr.IPm2, TYPPRED, nbobs_com, nbobs_mail, R2_adj`.
- **Points d'attention** : fichier en `;` (point-virgule) et encodage Latin-1/CP1252 (les
  accents apparaissent mal si lu en UTF-8 — à gérer explicitement dans `extract.py`, ex.
  `encoding="latin-1"`). Il existe 4 fichiers distincts par type de bien (appartement,
  appartement 1-2 pièces, appartement 3+ pièces, maison) — à agréger pour obtenir l'équivalent
  de `loyer_m2_appartement` / `loyer_m2_maison` / `loyer_m2_moyen`.
- **Verdict : source à intégrer.**

### ✅ Foyers fiscaux — remplace/complète `foyers_fiscaux.csv`

- **Source réelle testée** : jeu de données data.gouv.fr *"L'impôt sur le revenu par
  collectivité territoriale (IRCOM)"* (`id` data.gouv : `536998cba3a729239d20505e`), millésime
  **IRCOM 2025 (revenus 2024)** ajouté le 2026-05-26.
- **Test effectué** : téléchargement et décompression du zip
  `ircom-2025-revenus-2024.zip` ; le fichier `ircom_communes_complet_revenus_2024.xlsx`
  (feuille `ListeCommune`, ~85 600 lignes) contient les données par commune, avec colonnes :
  `Dép., Commune, Libellé de la commune, tranche de RFR, Nombre de foyers fiscaux, RFR des
  foyers fiscaux, Impôt net (total), Nombre de foyers fiscaux imposés, RFR des foyers imposés,
  Traitements et salaires (nb + montant), Retraites et pensions (nb + montant)`.
  Format `.xlsx` (nécessite `openpyxl`), pas de `.csv` direct.
- **Confirmation du décalage annoncé** : la DGFiP publie bien avec ~2 ans de retard — en 2026,
  seul le millésime "revenus 2024" est disponible ; 2025 et 2026 devront être extrapolés.
- **Verdict : source à intégrer** (nécessite un mapping des tranches de RFR vers les colonnes
  `n_foyers_0k_10k … n_foyers_100k_plus` actuelles, les libellés de tranches diffèrent).

### ✅ Parc immobilier / logements vacants — remplace/complète `parc_immobilier.csv`

- **Source réelle testée** : jeu de données data.gouv.fr *"Logements vacants du parc privé par
  commune, département, région, France, de 2020 à 2026"* (LOVAC — Cerema/DHUP), `id` data.gouv :
  `61816c6e23197bb34835228e`, mis à jour le 2026-06-25.
- **Test effectué** : téléchargement de `Lovac_opendata_Communes.csv`, colonnes confirmées :
  `CODGEO_26, LIBGEO_26, pp_vacant_26, pp_vacant_plus_2ans_26, ff_pp_total_25, pp_vacant_25, …`
  (une paire de colonnes par année de 2020 à 2026 : logements vacants et parc total).
- **Points d'attention** : fichier en `;` et encodage Latin-1 (mêmes précautions que pour les
  loyers) ; certaines valeurs sont masquées par le secret statistique et remplacées par la
  lettre `"s"` (communes à faible nombre de logements) — à traiter comme valeur manquante
  (`NaN`), pas comme `0`.
- **Verdict : source à intégrer** — meilleure que la source proposée par l'agent (pas de lien
  direct LOVAC fonctionnel fourni par l'agent ; celui-ci a été retrouvé indépendamment sur
  data.gouv.fr et correspond exactement au besoin, avec des données déjà disponibles jusqu'en
  2026).

### ✅ Indice de référence des loyers (IRL) — remplace/complète `indice_reference_loyers.csv`

- **Source réelle testée** : INSEE, série BDM identifiant **`001515333`** ("Indice de référence
  des loyers (IRL)"), via l'API SDMX publique et sans clé :
  `https://www.bdm.insee.fr/series/sdmx/data/SERIES_BDM/001515333`
- **Test effectué** : appel réel de l'URL, réponse XML SDMX valide, dernière observation
  `2026-Q1 = 146.6`, confirmant la disponibilité du T1 2026 annoncée par l'agent. Historique
  remonte à 2003 (largement suffisant).
- **Verdict : source à intégrer.** L'agent n'avait pas donné d'URL technique exploitable
  ("Série de l'IRL sur le site de l'INSEE" est vague) — l'identifiant de série et l'endpoint
  SDMX ont été retrouvés et testés indépendamment.

### ⚠️ Taux d'intérêt, taux d'endettement, flux de nouveaux emprunts (Banque de France Webstat)

Concerne les trois fichiers `taux_interet.csv`, `taux_endettement.csv`,
`flux_nouveaux_emprunts.csv`.

- **L'URL fournie par l'agent de recherche est cassée et ne fonctionne pas** :
  `.../catalog/datasets/observations/exports/json/...` renvoie une erreur 404
  `"The requested dataset observations does not exist."` — le dataset générique
  `observations` interrogeable par `series_key` n'existe plus sur l'API publique actuelle.
- **Vérification approfondie** : la clé de série `MIR1.M.FR.B.A22HR.A.R.A.2254U6.EUR.N` citée
  par l'agent est correcte et correspond bien à la bonne série ("Taux des crédits nouveaux à
  l'habitat (hors négociations) aux particuliers"), et les métadonnées confirment que la donnée
  existe réellement et va jusqu'à avril 2026 (dernière valeur : 3,22 %). Le problème n'est donc
  pas la série visée, mais l'accès à ses observations via l'API.
- **Constat** : sur le catalogue public actuel (`webstat.banque-france.fr/api/explore/v2.1/…`),
  les ~37 000 séries n'exposent que leurs métadonnées ; aucune ne retourne d'observations
  directement interrogeables sans authentification (`has_records: true` ne concerne qu'un seul
  jeu de données non pertinent). Le site indique explicitement que l'automatisation via API
  nécessite de se connecter à un "developer portail" (compte développeur, gratuit sur
  inscription mais non anonyme).
- **Aucune source alternative libre équivalente trouvée** : ni data.gouv.fr, ni Eurostat
  (table `irt_st_m` testée : pas de détail par type de crédit/pays au niveau requis) ne
  proposent de mirroir public de ces séries Banque de France.
- **Recommandation** :
  1. Créer un compte gratuit sur le portail développeur Webstat pour obtenir une clé API, puis
     utiliser l'API authentifiée (le format d'URL restera proche de celui fourni par l'agent,
     mais avec le bon nom de dataset et un header d'authentification).
  2. En alternative sans compte : export manuel ponctuel (CSV/XLSX) depuis les pages séries du
     portail Webstat (ex. page `https://webstat.banque-france.fr/fr/catalogue/MIR1/MIR1.M.FR.B.A22HR.A.R.A.2254U6.EUR.N`
     pour le taux d'intérêt), à répéter à chaque mise à jour des données du projet.
  3. Le "Taux d'endettement des ménages" (HCSF) et la "Production de crédits nouveaux à
     l'habitat" suivent la même contrainte d'accès — leurs identifiants de série exacts restent
     à confirmer une fois l'accès à l'API obtenu (recherche plein texte indisponible sur le
     catalogue public actuel, qui ignore le paramètre `q`).
- **Verdict : sources non intégrables en l'état sans démarche supplémentaire** (création de
  compte développeur ou récupération manuelle). Ne pas brancher d'appel automatisé sur l'URL
  fournie par l'agent : elle échouerait systématiquement (404).
