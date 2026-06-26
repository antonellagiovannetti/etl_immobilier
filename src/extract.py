from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.modules.setdefault("numexpr", None)
sys.modules.setdefault("bottleneck", None)

import pandas as pd


RAW_TRANSACTIONS_PATH = Path("data/raw/transactions.npz")
TRANSACTIONS_COLUMNS = [
    "id_transaction",
    "id_ville",
    "date_transaction",
    "prix",
    "type_batiment",
    "surface_habitable",
    "n_pieces",
    "vefa",
]


def decode_uint8_text_column(values: np.ndarray, expected_rows: int) -> np.ndarray:
    """
    Decode a text column stored in the raw NPZ as concatenated UTF-8 bytes
    separated by null bytes.
    """
    if values.dtype != np.uint8:
        return values.astype(str)

    decoded = values.tobytes().decode("utf-8").split("\x00")
    if len(decoded) != expected_rows:
        raise ValueError(
            f"Colonne texte invalide: {len(decoded)} valeurs decodees pour "
            f"{expected_rows} lignes attendues."
        )
    return np.asarray(decoded, dtype=str)


def extract_transactions_npz(
    input_path: str | Path = RAW_TRANSACTIONS_PATH,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Load raw real-estate transactions from a NPZ file and decode byte-packed
    text columns into UTF-8 strings.
    """
    selected_columns = columns or TRANSACTIONS_COLUMNS
    input_path = Path(input_path)

    with np.load(input_path, allow_pickle=False) as data:
        missing_columns = sorted(set(selected_columns) - set(data.files))
        if missing_columns:
            raise KeyError(f"Colonnes absentes du fichier source: {missing_columns}")

        n_rows = len(data["id_transaction"])
        extracted = {}
        for column in selected_columns:
            values = data[column]
            if values.dtype == np.uint8:
                values = decode_uint8_text_column(values, n_rows)
            extracted[column] = values

    return pd.DataFrame(extracted)
