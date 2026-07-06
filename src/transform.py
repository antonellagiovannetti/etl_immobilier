from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.modules.setdefault("numexpr", None)
sys.modules.setdefault("bottleneck", None)

import pandas as pd

try:
    from .extract import (
        RAW_TRANSACTIONS_PATH,
        TRANSACTIONS_COLUMNS,
        extract_dvf,
        extract_ircom,
        extract_loyers_complement,
        extract_lovac,
        extract_transactions_npz,
        extract_webstat_series,
    )
    from .API import recuperer_irl, recuperer_toutes_communes
except ImportError:
    from extract import (
        RAW_TRANSACTIONS_PATH,
        TRANSACTIONS_COLUMNS,
        extract_dvf,
        extract_ircom,
        extract_loyers_complement,
        extract_lovac,
        extract_transactions_npz,
        extract_webstat_series,
    )
    from API import recuperer_irl, recuperer_toutes_communes

DEFAULT_OUTPUT_PATH = Path("data/final/transactions.npz")
DEFAULT_FINAL_DIR = Path("data/final")
RAW_DIR = Path("data/raw")
ADDITIONAL_DATA_DIR = RAW_DIR / "additional_data"
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

    Paris/Lyon/Marseille : les sources DVF/fiscales decoupent parfois ces
    3 villes par arrondissement (75101-75120, 69381-69389, 13201-13216)
    comme s'il s'agissait de communes distinctes, alors que le referentiel
    officiel des communes (geo.api.gouv.fr) ne connait que la ville entiere
    (75056, 69123, 13055). Sans ce regroupement, ces arrondissements ne
    trouvent aucune correspondance dans communes.csv et sont silencieusement
    perdus au chargement - ce qui ferait disparaitre Paris de l'analyse.
    """
    dep = str(departement).strip().upper()
    commune_num = int(id_ville)

    if dep == "75" and 101 <= commune_num <= 120:
        commune_num = 56
    elif dep == "69" and 381 <= commune_num <= 389:
        commune_num = 123
    elif dep == "13" and 201 <= commune_num <= 216:
        commune_num = 55

    if dep[:2] == "2A":
        dep_code = 201
    elif dep[:2] == "2B":
        dep_code = 202
    else:
        dep_code = int(dep)
    return dep_code * 1000 + commune_num


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


def transform_dvf_supplement(dvf_df: pd.DataFrame, id_transaction_offset: int) -> pd.DataFrame:
    """
    Convertit un DataFrame geo-dvf brut (cf. extract_dvf) vers le meme format
    brut que extract_transactions_npz (TRANSACTIONS_COLUMNS), pour pouvoir le
    concatener AVANT transform_transactions et reutiliser telle quelle toute
    sa logique (globalisation id_ville, calcul prix_m2, filtre qualite
    2022-2024, dedoublonnage).

    id_transaction_offset doit depasser le plus grand id_transaction deja
    utilise par les donnees historiques (id_mutation geo-dvf est
    alphanumerique, ex. "2025-1", incompatible avec la colonne INTEGER de
    schema.sql) : on genere ici des identifiants entiers synthetiques.
    """
    df = dvf_df[
        dvf_df["nature_mutation"].isin(["Vente", "Vente en l'état futur d'achèvement"])
        & dvf_df["type_local"].isin(["Maison", "Appartement"])
    ].copy()

    deps_communes = df["code_commune"].map(split_insee_code)
    df["departement"] = [dep for dep, _ in deps_communes]
    df["id_ville"] = [commune for _, commune in deps_communes]

    df["date_transaction"] = df["date_mutation"]
    df["prix"] = df["valeur_fonciere"]
    df["surface_habitable"] = df["surface_reelle_bati"]
    df["type_batiment"] = df["type_local"]
    df["n_pieces"] = df["nombre_pieces_principales"]
    df["vefa"] = df["nature_mutation"] == "Vente en l'état futur d'achèvement"

    df = df.reset_index(drop=True)
    df["id_transaction"] = id_transaction_offset + df.index

    return df[TRANSACTIONS_COLUMNS]


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


def build_communes(communes_api_df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit le referentiel communes.csv a partir du referentiel complet
    des communes francaises (API.recuperer_toutes_communes). Indexe par
    code INSEE, donc sans ambiguite d'homonyme.
    """
    df = communes_api_df.copy()
    deps_communes = df["code_insee"].map(split_insee_code)
    df["departement"] = [dep for dep, _ in deps_communes]
    df["id_ville"] = [
        compute_global_id_ville(dep, commune) for dep, commune in deps_communes
    ]
    df = df.rename(columns={"ville_api": "ville"})
    return df[
        ["id_ville", "departement", "ville", "latitude", "longitude", "code_insee", "code_region"]
    ].drop_duplicates(subset=["id_ville"]).reset_index(drop=True)


def build_demographics(communes_api_df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit demographics.csv (population, superficie, densite) a partir du
    meme referentiel que build_communes.

    Modifications demandees :
    1. Supprimer la colonne vefa si elle existe.
    2. Supprimer les lignes ou population ou densite est vide/NaN ou egal a 0.
    """
    df = communes_api_df.copy()

    # 1 - Supprimer la colonne vefa si elle existe dans la source
    if "vefa" in df.columns:
        df = df.drop(columns=["vefa"])

    deps_communes = df["code_insee"].map(split_insee_code)
    df["id_ville"] = [
        compute_global_id_ville(dep, commune) for dep, commune in deps_communes
    ]

    df["superficie_km2"] = pd.to_numeric(df["superficie_m2"], errors="coerce") / 1_000_000
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df["densite"] = df["population"] / df["superficie_km2"]

    # 2 - Supprimer les lignes ou population ou densite est vide/NaN ou egal a 0
    df = df.dropna(subset=["population", "densite"])
    df = df[(df["population"] != 0) & (df["densite"] != 0)]

    return df[
        ["id_ville", "code_insee", "code_region", "nom_region", "population", "superficie_km2", "densite"]
    ].drop_duplicates(subset=["id_ville"]).reset_index(drop=True)



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




def fill_numeric_medians(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """
    Remplit les valeurs NaN des colonnes numériques par la médiane.
    Si columns est fourni, seules ces colonnes sont traitées.
    """
    df = df.copy()

    if columns is None:
        columns = [
            col for col in df.columns
            if pd.api.types.is_numeric_dtype(df[col]) and col not in ("id_ville", "annee", "mois")
        ]

    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            median_value = df[col].median()
            if pd.notna(median_value):
                df[col] = df[col].fillna(median_value)

    return df


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

    # 7 - Corriger montant_impot_moyen : transformer les valeurs negatives en positives
    if "montant_impot_moyen" in combined.columns:
        combined["montant_impot_moyen"] = pd.to_numeric(
            combined["montant_impot_moyen"], errors="coerce"
        ).abs()

    # 3 - Remplir les valeurs vides/NaN des colonnes numeriques par la mediane
    combined = fill_numeric_medians(
        combined,
        columns=["revenu_fiscal_moyen", "montant_impot_moyen", "n_foyers_fiscaux"]
    )

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
    # 4 - Supprimer les lignes de 1999-01 jusqu'a 2010-11 inclus
    periode_a_supprimer = (
        (merged["annee"] >= 1999)
        & (
            (merged["annee"] < 2010)
            | ((merged["annee"] == 2010) & (merged["mois"] <= 11))
        )
    )
    merged = merged[~periode_a_supprimer].copy()

    # 5 - Remplir les valeurs vides/NaN des indicateurs numeriques par la mediane
    merged = fill_numeric_medians(
        merged,
        columns=["taux_interet", "flux_emprunts_me", "taux_endettement", "irl"]
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

    Le prix m2 median, le nombre de transactions et le filtre qualite
    (>= 5 transactions) portent sur la derniere annee disponible dans
    transactions_df (2025 au moment d'ecrire ce code), pas sur une fenetre
    glissante de plusieurs annees : le score doit refleter le marche actuel,
    pas une moyenne datant potentiellement de 2 ou 3 ans. Une fenetre
    multi-annees couvrirait plus de communes (les petites communes rurales
    n'ont pas toujours 5 transactions/an), mais au prix d'une donnee moins
    a jour - choix valide, mais ce n'est pas celui retenu ici.
    """
    derniere_annee_transactions = int(transactions_df["annee"].max())
    window = transactions_df[transactions_df["annee"] == derniere_annee_transactions]
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


def run_full_pipeline(output_dir: str | Path = DEFAULT_FINAL_DIR) -> dict[str, dict[str, int]]:
    """
    Execute l'extraction + harmonisation des 8 sources et ecrit un CSV par
    table dans output_dir (un fichier par table de db/schema.sql), au
    format attendu par src/load.py (TABLES + DATA_DIR).

    Les lignes dont l'id_ville ne correspond a aucune commune du
    referentiel actuel (fusions de communes depuis 2014, arrondissements
    de Marseille/Paris/Lyon presents dans les sources fiscales mais pas
    dans le referentiel geographique, entrees hors-France) sont retirees
    avant ecriture pour respecter les cles etrangeres de db/schema.sql.
    Le detail (lignes gardees / ecartees) est retourne pour etre reporte.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, dict[str, int]] = {}

    def _write(df: pd.DataFrame, name: str) -> pd.DataFrame:
        df.to_csv(output_dir / f"{name}.csv", index=False)
        stats[name] = {"lignes": len(df), "ecartees": 0}
        return df

    def _write_filtered(df: pd.DataFrame, name: str, valid_ids: set[int]) -> pd.DataFrame:
        before = len(df)
        filtered = df[df["id_ville"].isin(valid_ids)].reset_index(drop=True)
        filtered.to_csv(output_dir / f"{name}.csv", index=False)
        stats[name] = {"lignes": len(filtered), "ecartees": before - len(filtered)}
        return filtered

    communes_api = recuperer_toutes_communes()
    communes = _write(build_communes(communes_api), "communes")
    _write(build_demographics(communes_api), "demographics")
    valid_ids = set(communes["id_ville"])

    raw_transactions = extract_transactions_npz()
    dvf_2025 = extract_dvf(2025)
    dvf_supplement = transform_dvf_supplement(
        dvf_2025, id_transaction_offset=int(raw_transactions["id_transaction"].max()) + 1
    )
    transactions = transform_transactions(
        pd.concat([raw_transactions, dvf_supplement], ignore_index=True)
    )
    transactions = _write_filtered(transactions, "transactions", valid_ids)
    save_transactions_npz(transactions)  # conserve le format .npz historique

    loyers = transform_loyers(
        pd.read_csv(RAW_DIR / "loyers.csv"),
        [extract_loyers_complement(2024), extract_loyers_complement(2025)],
    )
    loyers = _write_filtered(loyers, "loyers", valid_ids)

    foyers = transform_foyers_fiscaux(pd.read_csv(RAW_DIR / "foyers_fiscaux.csv"), extract_ircom())
    foyers = _write_filtered(foyers, "foyers_fiscaux", valid_ids)

    parc = transform_parc_immobilier(pd.read_csv(RAW_DIR / "parc_immobilier.csv"), extract_lovac())
    parc = _write_filtered(parc, "parc_immobilier", valid_ids)

    macro = transform_indicateurs_macro(
        extract_webstat_series(ADDITIONAL_DATA_DIR / "new_housing_loans_interest_rate.csv"),
        extract_webstat_series(ADDITIONAL_DATA_DIR / "new_housing_loans_flow.csv"),
        extract_webstat_series(ADDITIONAL_DATA_DIR / "household_debt_ratio.csv"),
        recuperer_irl(),
    )
    _write(macro, "indicateurs_macro")

    score = compute_kpi(transactions, loyers, foyers, parc)
    _write_filtered(score, "score_attractivite", valid_ids)

    return stats


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
    parser.add_argument(
        "--full",
        action="store_true",
        help="Execute le pipeline complet (8 sources) et ecrit un CSV par table dans data/final/",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.full:
        stats = run_full_pipeline()
        for table, info in stats.items():
            suffix = f" ({info['ecartees']:,} ecartees, id_ville inconnu)" if info["ecartees"] else ""
            print(f"{table:<20} {info['lignes']:,} lignes -> data/final/{table}.csv{suffix}")
        return

    df_raw = extract_transactions_npz(args.input)
    df_final = transform_transactions(df_raw)
    save_transactions_npz(df_final, args.output)

    print(f"Transactions brutes  : {len(df_raw):,}")
    print(f"Transactions finales : {len(df_final):,}")
    print(f"Fichier ecrit        : {args.output}")


if __name__ == "__main__":
    main()
