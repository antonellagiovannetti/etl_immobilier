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


def compute_global_id_ville(departement, id_ville) -> int:
    """
    id_ville seul n'est pas unique au niveau national dans les sources
    brutes (juste le numero de commune a l'interieur de son departement,
    ex. "001" existe dans chaque departement). Le schema de la base garde
    id_ville comme cle primaire simple (INTEGER) : on reconstruit donc ici
    une valeur globalement unique a partir de departement + id_ville, sans
    toucher au schema. Corse (2A/2B) et DOM (971-976) sont geres a part
    pour rester dans des plages qui ne se recoupent pas.
    """
    dep = str(departement).strip().upper()
    if dep[:2] == "2A":
        dep_code = 201
    elif dep[:2] == "2B":
        dep_code = 202
    else:
        dep_code = int(dep)
    return dep_code * 1000 + int(id_ville)


def transform_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the business rules for the transactions transform phase.
    """
    df = df.copy()

    df["id_ville"] = [
        compute_global_id_ville(dep, ville)
        for dep, ville in zip(df["departement"], df["id_ville"])
    ]

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


def split_insee_code(code: str) -> tuple[str, int]:
    """
    Decoupe un code INSEE commune (5 caracteres) en (departement, numero de
    commune dans le departement). Gere la Corse (2A/2B, deja sur 2
    caracteres) et les DOM (departement sur 3 caracteres, ex. 971).
    """
    code = str(code).strip().zfill(5)
    if code[:2] in ("97", "98"):
        departement, commune = code[:3], code[3:]
    else:
        departement, commune = code[:2], code[2:]
    return departement, int(commune)


def transform_loyers(
    old_df: pd.DataFrame, complements: list[pd.DataFrame] | None = None
) -> pd.DataFrame:
    """
    Harmonise loyers.csv (2018/2022/2023) avec les millesimes complementaires
    (Carte des loyers 2024/2025, cf. extract_loyers_complement) sur la cle
    id_ville globale.
    """
    old = old_df.rename(columns={"date": "annee"}).copy()
    old["departement"] = old["departement"].astype(str)
    old["id_ville"] = [
        compute_global_id_ville(dep, ville)
        for dep, ville in zip(old["departement"], old["id_ville"])
    ]
    parts = [old[["id_ville", "annee", "loyer_m2_appartement", "loyer_m2_maison"]]]

    for comp in complements or []:
        comp = comp.copy()
        deps_communes = comp["INSEE_C"].map(split_insee_code)
        comp["id_ville"] = [
            compute_global_id_ville(dep, commune) for dep, commune in deps_communes
        ]
        parts.append(comp[["id_ville", "annee", "loyer_m2_appartement", "loyer_m2_maison"]])

    combined = pd.concat(parts, ignore_index=True)
    combined["loyer_m2_moyen"] = combined[["loyer_m2_appartement", "loyer_m2_maison"]].mean(
        axis=1, skipna=True
    )
    return combined.drop_duplicates(subset=["id_ville", "annee"]).reset_index(drop=True)


def transform_foyers_fiscaux(
    old_df: pd.DataFrame, ircom_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """
    Harmonise foyers_fiscaux.csv (2014-2022) avec le millesime IRCOM le plus
    recent (revenus 2024, cf. extract_ircom). Les montants IRCOM sont en
    milliers d'euros et totalises sur la commune : on les ramene a une
    moyenne par foyer pour matcher le format existant.
    """
    old = old_df.rename(columns={"date": "annee"}).copy()
    old["departement"] = old["departement"].astype(str)
    old["id_ville"] = [
        compute_global_id_ville(dep, ville)
        for dep, ville in zip(old["departement"], old["id_ville"])
    ]
    parts = [old[["id_ville", "annee", "revenu_fiscal_moyen", "montant_impot_moyen", "n_foyers_fiscaux"]]]

    if ircom_df is not None:
        totals = ircom_df[ircom_df["tranche_rfr"] == "Total"].copy()
        # Exclut les codes non geographiques (ex. "B3" pour les foyers
        # non-residents) que l'on ne peut pas rattacher a une commune.
        valid_dep = totals["departement"].str.match(r"^(2A|2B|\d{2,3})$")
        totals = totals[valid_dep]
        totals["id_ville"] = [
            compute_global_id_ville(dep, ville)
            for dep, ville in zip(totals["departement"], totals["id_ville"])
        ]
        totals["revenu_fiscal_moyen"] = (
            totals["revenu_fiscal_reference"] * 1000 / totals["n_foyers_fiscaux"]
        )
        totals["montant_impot_moyen"] = totals["impot_net"] * 1000 / totals["n_foyers_fiscaux"]
        totals["annee"] = 2024  # dernier millesime IRCOM disponible (revenus 2024)
        parts.append(
            totals[["id_ville", "annee", "revenu_fiscal_moyen", "montant_impot_moyen", "n_foyers_fiscaux"]]
        )

    combined = pd.concat(parts, ignore_index=True)
    return combined.drop_duplicates(subset=["id_ville", "annee"]).reset_index(drop=True)


def transform_parc_immobilier(
    old_df: pd.DataFrame, lovac_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """
    Harmonise parc_immobilier.csv (2019-2021) avec le jeu LOVAC (2020-2026,
    cf. extract_lovac), qui stocke une paire de colonnes par annee.
    """
    old = old_df.rename(columns={"date": "annee"}).copy()
    old["departement"] = old["departement"].astype(str)
    old["id_ville"] = [
        compute_global_id_ville(dep, ville)
        for dep, ville in zip(old["departement"], old["id_ville"])
    ]
    parts = [old[["id_ville", "annee", "n_logements", "n_logements_vacants"]]]

    if lovac_df is not None:
        year_suffixes = sorted(
            col.rsplit("_", 1)[-1]
            for col in lovac_df.columns
            if col.startswith("pp_vacant_") and col.rsplit("_", 1)[-1].isdigit()
        )
        for suffix in year_suffixes:
            vacants_col = f"pp_vacant_{suffix}"
            total_col = f"ff_pp_total_{suffix}"
            if total_col not in lovac_df.columns:
                continue

            subset = lovac_df[["CODGEO_26", vacants_col, total_col]].copy()
            deps_communes = subset["CODGEO_26"].map(split_insee_code)
            subset["id_ville"] = [
                compute_global_id_ville(dep, commune) for dep, commune in deps_communes
            ]
            subset["annee"] = 2000 + int(suffix)
            subset = subset.rename(
                columns={vacants_col: "n_logements_vacants", total_col: "n_logements"}
            )
            parts.append(subset[["id_ville", "annee", "n_logements", "n_logements_vacants"]])

    combined = pd.concat(parts, ignore_index=True)
    combined["taux_vacance"] = 100 * combined["n_logements_vacants"] / combined["n_logements"]
    return combined.drop_duplicates(subset=["id_ville", "annee"]).reset_index(drop=True)


def transform_indicateurs_macro(
    taux_interet_df: pd.DataFrame,
    flux_emprunts_df: pd.DataFrame,
    taux_endettement_df: pd.DataFrame,
    irl_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construit la table indicateurs_macro (nationale, mensuelle) a partir des
    trois exports Webstat (cf. extract_webstat_series) et de l'IRL
    (cf. API.recuperer_irl). Taux d'endettement et IRL sont trimestriels :
    on les rattache au mois de fin de trimestre, le reste des mois de la
    table reste NULL pour ces deux colonnes.
    """

    def _monthly(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
        out = df.dropna(subset=["valeur"]).copy()
        out["date"] = pd.to_datetime(out["date"])
        out["annee"] = out["date"].dt.year
        out["mois"] = out["date"].dt.month
        return out.rename(columns={"valeur": value_col})[["annee", "mois", value_col]]

    taux_interet = _monthly(taux_interet_df, "taux_interet")

    flux_emprunts = _monthly(flux_emprunts_df, "flux_emprunts_me")
    flux_emprunts["flux_emprunts_me"] = flux_emprunts["flux_emprunts_me"] / 1_000_000

    taux_endettement = _monthly(taux_endettement_df, "taux_endettement")

    irl = irl_df.copy()
    irl[["annee", "trimestre_num"]] = irl["trimestre"].str.split("-Q", expand=True)
    irl["annee"] = irl["annee"].astype(int)
    irl["mois"] = irl["trimestre_num"].astype(int) * 3
    irl = irl[["annee", "mois", "irl"]]

    merged = (
        taux_interet.merge(flux_emprunts, on=["annee", "mois"], how="outer")
        .merge(taux_endettement, on=["annee", "mois"], how="outer")
        .merge(irl, on=["annee", "mois"], how="outer")
    )
    return merged.sort_values(["annee", "mois"]).reset_index(drop=True)


def compute_kpi(
    transactions_df: pd.DataFrame,
    loyers_df: pd.DataFrame,
    foyers_df: pd.DataFrame,
    parc_df: pd.DataFrame,
    annee_ref: int | None = None,
) -> pd.DataFrame:
    """
    Calcule les 4 KPI (rendement brut, taux de vacance, ratio d'effort
    fiscal, prix m2 median) et le score d'attractivite (0-100) par commune,
    conformement au mapping du cahier des charges (section 3 et 8).
    Filtre qualite : communes avec >= 5 transactions sur 2022-2024.
    """
    window = transactions_df[transactions_df["annee"].between(2022, 2024, inclusive="both")]
    agg = (
        window.groupby("id_ville")
        .agg(prix_m2_median=("prix_m2", "median"), n_transactions=("id_transaction", "count"))
        .reset_index()
    )
    agg = agg[agg["n_transactions"] >= 5]

    if annee_ref is None:
        annee_ref = int(min(loyers_df["annee"].max(), foyers_df["annee"].max(), parc_df["annee"].max()))

    def _latest_up_to(df: pd.DataFrame, year: int, value_cols: list[str]) -> pd.DataFrame:
        subset = df[df["annee"] <= year].sort_values("annee")
        subset = subset.groupby("id_ville", as_index=False).tail(1)
        return subset[["id_ville", *value_cols]]

    loyers_ref = _latest_up_to(loyers_df, annee_ref, ["loyer_m2_moyen"])
    foyers_ref = _latest_up_to(foyers_df, annee_ref, ["revenu_fiscal_moyen"])
    parc_ref = _latest_up_to(parc_df, annee_ref, ["taux_vacance"])

    score = (
        agg.merge(loyers_ref, on="id_ville", how="inner")
        .merge(foyers_ref, on="id_ville", how="inner")
        .merge(parc_ref, on="id_ville", how="inner")
    )

    score["rendement_brut"] = (score["loyer_m2_moyen"] * 12) / score["prix_m2_median"] * 100
    score["ratio_effort_fiscal"] = (score["loyer_m2_moyen"] * 12 * 50) / score["revenu_fiscal_moyen"]

    def _min_max(series: pd.Series) -> pd.Series:
        low, high = series.min(), series.max()
        if high == low:
            return series * 0
        return (series - low) / (high - low) * 100

    score["score_rendement"] = _min_max(score["rendement_brut"])
    score["score_effort"] = 100 - _min_max(score["ratio_effort_fiscal"])
    score["score_richesse"] = _min_max(score["revenu_fiscal_moyen"])
    score["score_vacance"] = 100 - _min_max(score["taux_vacance"])

    score["score_attractivite"] = (
        0.35 * score["score_rendement"]
        + 0.25 * score["score_effort"]
        + 0.20 * score["score_richesse"]
        + 0.20 * score["score_vacance"]
    )
    score["annee_ref"] = annee_ref

    return score[
        [
            "id_ville", "annee_ref", "prix_m2_median", "loyer_m2_moyen", "revenu_fiscal_moyen",
            "rendement_brut", "taux_vacance", "ratio_effort_fiscal",
            "score_rendement", "score_effort", "score_richesse", "score_vacance",
            "score_attractivite", "n_transactions",
        ]
    ].sort_values("score_attractivite", ascending=False).reset_index(drop=True)


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
