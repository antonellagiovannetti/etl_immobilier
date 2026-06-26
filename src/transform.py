from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.modules.setdefault("numexpr", None)
sys.modules.setdefault("bottleneck", None)

import pandas as pd

try:
    from .extract import RAW_TRANSACTIONS_PATH, extract_transactions_npz
except ImportError:
    from extract import RAW_TRANSACTIONS_PATH, extract_transactions_npz

DEFAULT_OUTPUT_PATH = Path("data/final/transactions.npz")
OUTPUT_COLUMNS = [
    "id_transaction",
    "id_ville",
    "date_transaction",
    "annee",
    "prix",
    "prix_m2",
    "type_batiment",
    "surface_habitable",
    "n_pieces",
    "vefa",
]


def transform_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the business rules for the transactions transform phase.
    """
    df = df.copy()

    df["date_transaction"] = pd.to_datetime(df["date_transaction"], errors="coerce")
    df["annee"] = df["date_transaction"].dt.year.astype("Int64")

    df["prix_m2"] = np.where(
        df["surface_habitable"] > 0,
        df["prix"] / df["surface_habitable"],
        np.nan,
    )

    df = df[df["prix_m2"].between(500, 30_000, inclusive="both")]
    df = df.drop_duplicates()

    transactions_2022_2024 = df[df["annee"].between(2022, 2024, inclusive="both")]
    communes_a_conserver = (
        transactions_2022_2024.groupby("id_ville").size().loc[lambda s: s >= 5].index
    )
    df = df[df["id_ville"].isin(communes_a_conserver)]

    df = df[OUTPUT_COLUMNS].sort_values(["id_ville", "date_transaction", "id_transaction"])
    df["annee"] = df["annee"].astype(np.int32)
    df["date_transaction"] = df["date_transaction"].values.astype("datetime64[D]")

    return df.reset_index(drop=True)


def dataframe_to_npz_arrays(df: pd.DataFrame) -> dict[str, np.ndarray]:
    arrays = {}
    for column in OUTPUT_COLUMNS:
        values = df[column]
        if pd.api.types.is_string_dtype(values) or values.dtype == object:
            arrays[column] = values.astype(str).to_numpy(dtype=np.str_)
        else:
            arrays[column] = values.to_numpy()
    return arrays


def save_transactions_npz(
    df: pd.DataFrame,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> None:
    """
    Save cleaned transactions to a compressed NPZ using one key per final column.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **dataframe_to_npz_arrays(df))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transforme les transactions immobilieres brutes au format NPZ."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=RAW_TRANSACTIONS_PATH,
        help=f"Fichier NPZ source (defaut: {RAW_TRANSACTIONS_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Fichier NPZ cible (defaut: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df_raw = extract_transactions_npz(args.input)
    df_final = transform_transactions(df_raw)
    save_transactions_npz(df_final, args.output)

    print(f"Transactions brutes  : {len(df_raw):,}")
    print(f"Transactions finales : {len(df_final):,}")
    print(f"Fichier ecrit        : {args.output}")


if __name__ == "__main__":
    main()
