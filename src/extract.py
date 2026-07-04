from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

sys.modules.setdefault("numexpr", None)
sys.modules.setdefault("bottleneck", None)

import pandas as pd


def _get_env_var(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return None


def _require_env_var(name: str) -> str:
    value = _get_env_var(name)
    if not value:
        raise RuntimeError(
            f"{name} est manquant dans l'environnement. Ajoute-le dans .env ou .env.example."
        )
    return value.rstrip("/")


CARTE_LOYERS_DATASET_IDS = {
    2024: "6751be987c09f4be821c6934",
    2025: "693aa2feed1bf4da603faa49",
}
IRCOM_DATASET_ID = "536998cba3a729239d20505e"
LOVAC_DATASET_ID = "61816c6e23197bb34835228e"

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


def _download_bytes(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _data_gouv_resources(dataset_id: str) -> list[dict]:
    api_url = _require_env_var("DATA_GOUV_API_URL")
    payload = json.loads(_download_bytes(f"{api_url}/{dataset_id}/"))
    return payload["resources"]


def extract_dvf(year: int) -> pd.DataFrame:
    """
    Telecharge les transactions DVF geolocalisees (Etalab/geo-dvf) pour une
    annee donnee. Retourne un DataFrame brut, une ligne par mutation.
    """
    url = f"{_require_env_var('GEO_DVF_BASE_URL')}/{year}/full.csv.gz"
    raw_bytes = _download_bytes(url, timeout=180)
    return pd.read_csv(
        io.BytesIO(raw_bytes),
        compression="gzip",
        dtype={"code_commune": str, "code_departement": str, "code_postal": str},
        low_memory=False,
    )


def extract_loyers_complement(year: int) -> pd.DataFrame:
    """
    Telecharge la "Carte des loyers" (data.gouv.fr) pour une annee donnee et
    fusionne les indicateurs appartement / maison sur le code INSEE commune.
    """
    dataset_id = CARTE_LOYERS_DATASET_IDS[year]
    resources = _data_gouv_resources(dataset_id)

    appartement_url = next(
        r["url"] for r in resources if r["title"] == "Indicateurs de loyer appartement"
    )
    maison_url = next(
        r["url"] for r in resources if r["title"] == "Indicateurs de loyer maison"
    )

    def _read(url: str, value_col: str) -> pd.DataFrame:
        df = pd.read_csv(
            io.BytesIO(_download_bytes(url, timeout=120)),
            sep=";",
            encoding="latin-1",
            dtype={"INSEE_C": str},
            decimal=",",
        )
        return df[["INSEE_C", "LIBGEO", "loypredm2"]].rename(
            columns={"loypredm2": value_col}
        )

    appartements = _read(appartement_url, "loyer_m2_appartement")
    maisons = _read(maison_url, "loyer_m2_maison")

    merged = appartements.merge(maisons, on=["INSEE_C", "LIBGEO"], how="outer")
    merged["annee"] = year
    return merged


def extract_ircom() -> pd.DataFrame:
    """
    Telecharge le millesime IRCOM (revenus des menages par commune, DGFiP) le
    plus recent disponible sur data.gouv.fr et retourne la feuille communes.
    """
    resources = _data_gouv_resources(IRCOM_DATASET_ID)
    zip_resources = [r for r in resources if r["format"] == "zip"]
    latest = max(zip_resources, key=lambda r: r["last_modified"])

    zip_bytes = _download_bytes(latest["url"], timeout=180)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        xlsx_name = next(
            name for name in archive.namelist()
            if name.endswith("_complet_revenus.xlsx") or "communes_complet" in name
        )
        with archive.open(xlsx_name) as xlsx_file:
            df = pd.read_excel(
                io.BytesIO(xlsx_file.read()),
                sheet_name="ListeCommune",
                skiprows=7,
                header=None,
                names=[
                    "col_a", "departement", "id_ville", "ville", "tranche_rfr",
                    "n_foyers_fiscaux", "revenu_fiscal_reference", "impot_net",
                    "n_foyers_imposes", "revenu_fiscal_reference_imposes",
                    "n_foyers_salaires", "montant_salaires",
                    "n_foyers_retraites", "montant_retraites",
                ],
            )
    df = df.drop(columns=["col_a"])
    df["id_ville"] = df["id_ville"].astype(str).str.zfill(3)
    return df


def extract_lovac() -> pd.DataFrame:
    """
    Telecharge le jeu LOVAC (logements vacants du parc prive par commune,
    2020-2026, Cerema/DHUP) depuis data.gouv.fr.
    """
    resources = _data_gouv_resources(LOVAC_DATASET_ID)
    communes_resource = next(r for r in resources if "Communes" in r["title"])

    return pd.read_csv(
        io.BytesIO(_download_bytes(communes_resource["url"], timeout=120)),
        sep=";",
        encoding="latin-1",
        dtype={"CODGEO_26": str},
        na_values=["s"],
        low_memory=False,
    )


def extract_webstat_series(path: str | Path) -> pd.DataFrame:
    """
    Parse un export CSV Webstat (Banque de France) telecharge manuellement :
    6 lignes d'entete (titre, code serie, unite, magnitude, methode, source)
    puis des lignes date;valeur. Retourne un DataFrame [date, valeur] avec la
    valeur ramenee a l'unite de base (application du facteur de magnitude).
    """
    path = Path(path)
    lines = path.read_text(encoding="utf-8-sig").splitlines()

    header = dict(line.split(";", 1) for line in lines[:6] if ";" in line)
    magnitude_match = re.search(r"\((-?\d+)\)", header.get("Magnitude :", "(0)"))
    exponent = int(magnitude_match.group(1)) if magnitude_match else 0
    scale = 10 ** exponent

    records = []
    for line in lines[6:]:
        if ";" not in line:
            continue
        date_str, value_str = line.split(";", 1)
        value_str = value_str.strip()
        value = None if value_str in ("-", "") else float(value_str.replace(",", ".")) * scale
        records.append({"date": date_str, "valeur": value})

    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    df.attrs["titre"] = header.get("Titre :", "").strip()
    df.attrs["code_serie"] = header.get("Code série :", "").strip()
    df.attrs["unite"] = header.get("Unité :", "").strip()
    return df
