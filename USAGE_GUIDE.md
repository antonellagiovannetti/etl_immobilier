# Explication d'utilisation

Ce document explique comment utiliser les modules d'extraction et de transformation
des transactions immobilieres.

## Objectif

Le traitement part du fichier brut :

```text
data/raw/transactions.npz
```

Il produit un fichier final nettoye :

```text
data/final/transactions.npz
```

Le code est separe en deux modules pour pouvoir etre reutilise plus tard dans un
fichier `pipeline.py`.

## 1. Module d'extraction

Fichier :

```text
src/extract.py
```

Fonction principale :

```python
from src.extract import extract_transactions_npz

df_raw = extract_transactions_npz("data/raw/transactions.npz")
```

Cette fonction :

- lit le fichier `.npz` brut avec `numpy`;
- verifie que les colonnes demandees existent;
- decode les colonnes texte stockees en `uint8`, separees par le caractere nul `\x00`;
- retourne un `DataFrame pandas`.

Colonnes extraites par defaut :

- `id_transaction`
- `id_ville`
- `date_transaction`
- `prix`
- `type_batiment`
- `surface_habitable`
- `n_pieces`
- `vefa`

## 2. Module de transformation

Fichier :

```text
src/transform.py
```

Fonctions principales :

```python
from src.transform import transform_transactions, save_transactions_npz

df_final = transform_transactions(df_raw)
save_transactions_npz(df_final, "data/final/transactions.npz")
```

La fonction `transform_transactions` applique les regles suivantes :

- creation de la colonne `annee` a partir de `date_transaction`;
- calcul de `prix_m2 = prix / surface_habitable`;
- suppression des transactions dont `prix_m2` est hors de `[500, 30000]`;
- suppression des lignes strictement identiques;
- conservation uniquement des communes avec au moins 5 transactions entre 2022 et 2024;
- conservation des colonnes finales attendues.

Colonnes finales :

- `id_transaction`
- `id_ville`
- `date_transaction`
- `annee`
- `prix`
- `prix_m2`
- `type_batiment`
- `surface_habitable`
- `n_pieces`
- `vefa`

## 3. Exemple pour le futur pipeline

Un futur fichier `pipeline.py` pourra appeler les modules comme ceci :

```python
from src.extract import extract_transactions_npz
from src.transform import transform_transactions, save_transactions_npz


def run_transactions_pipeline():
    df_raw = extract_transactions_npz("data/raw/transactions.npz")
    df_final = transform_transactions(df_raw)
    save_transactions_npz(df_final, "data/final/transactions.npz")
    return df_final


if __name__ == "__main__":
    run_transactions_pipeline()
```

## 4. Execution directe sans pipeline

Pour tester uniquement le traitement des transactions :

```bash
python src/transform.py
```

Par defaut, cette commande lit :

```text
data/raw/transactions.npz
```

et ecrit :

```text
data/final/transactions.npz
```

Il est aussi possible de choisir les chemins :

```bash
python src/transform.py --input data/raw/transactions.npz --output data/final/transactions.npz
```

## 5. Verification rapide du resultat

Le fichier final doit contenir les cles suivantes :

```text
id_transaction, id_ville, date_transaction, annee, prix, prix_m2,
type_batiment, surface_habitable, n_pieces, vefa
```

Exemple de verification :

```python
import numpy as np

with np.load("data/final/transactions.npz", allow_pickle=False) as data:
    print(data.files)
    print(len(data["id_transaction"]))
    print(data["prix_m2"].min(), data["prix_m2"].max())
```
