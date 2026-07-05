# Log erreurs — Projet ETL Immobilier

Ce fichier recense les erreurs connues et documentées du projet (issues du code et de la
documentation), pas un historique d'incidents en production. Il n'existe pas de logging
centralisé dans le projet à ce jour — seuls des `print()` et des exceptions ponctuelles sont
utilisés.

## Docker / PostgreSQL

**`failed to connect to the docker API`**
- Cause : Docker Desktop n'est pas lancé.
- Solution documentée (README.md, section 6.4) : ouvrir Docker Desktop, attendre que
  l'icône soit verte/active, puis relancer `docker compose up -d`.

## `src/extract.py`

**`ValueError` dans `decode_uint8_text_column`**
- Message : `Colonne texte invalide: {n} valeurs decodees pour {expected_rows} lignes attendues.`
- Cause : le nombre de valeurs obtenues après avoir découpé le tableau `uint8` sur le
  séparateur `\x00` ne correspond pas au nombre de lignes attendu (fichier `.npz` source
  corrompu ou mal formé).

**`KeyError` dans `extract_transactions_npz`**
- Message : `Colonnes absentes du fichier source: {missing_columns}`
- Cause : une ou plusieurs colonnes attendues (`id_transaction`, `id_ville`,
  `date_transaction`, `prix`, `type_batiment`, `surface_habitable`, `n_pieces`, `vefa`)
  sont absentes du fichier `data/raw/transactions.npz`.

## `src/API.py`

**`RuntimeError` — URL API manquante**
- Message : `GEO_API_COMMUNES_URL est manquant dans l'environnement...`
- Cause : la variable d'environnement `GEO_API_COMMUNES_URL` n'est définie ni dans
  l'environnement, ni dans `.env`.

**`RuntimeError` — échec d'appel API après retries**
- Message : `Erreur API apres {retries} tentative(s): {last_error}`
- Cause : l'appel à `geo.api.gouv.fr` a échoué après le nombre de tentatives configuré
  (3 par défaut), avec un backoff progressif entre chaque tentative.
- Comportement : l'erreur est capturée par ville et ajoutée à la liste `errors` du résultat
  retourné par `recuperer_infos_communes` ; le traitement des autres villes continue
  (pas d'arrêt global du batch).

**Ville non trouvée**
- Cas géré explicitement : si l'API ne retourne aucune commune pour un nom donné, une
  entrée est ajoutée à `errors` (`"Aucune commune retournee par l'API"`) plutôt que de
  lever une exception.

## `src/transform.py`

- Aucune levée d'exception spécifique documentée ; les transactions hors de la plage
  `prix_m2 ∈ [500, 30000]` sont silencieusement filtrées (pas une erreur, mais une règle de
  nettoyage à garder en tête si le nombre de lignes finales semble anormalement bas).

## Constat général

Aucun fichier de log applicatif ni module `logging` n'est en place dans le projet. Toute
mise en place future d'un logging centralisé (fichier de log, niveaux, rotation) serait à
ajouter — ce fichier devra être complété au fur et à mesure que de nouvelles erreurs
réelles sont rencontrées et corrigées par l'équipe.
