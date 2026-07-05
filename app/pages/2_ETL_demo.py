import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import API
import extract
import load as load_module
import transform

# Verrou Postgres (session-level) empechant deux executions concurrentes du
# pipeline : si l'onglet est ferme/rafraichi en plein chargement puis relance,
# ou si quelqu'un clique deux fois, le deuxieme essai est bloque au lieu de
# lancer un insert en double par-dessus le premier. Le verrou est
# automatiquement libere par Postgres si la connexion qui le detient meurt
# (crash, tab fermee), donc pas de risque de blocage permanent.
PIPELINE_LOCK_KEY = 918273

# Configuration de la page
st.set_page_config(page_title="Demo Pipeline ETL", layout="wide")

# ==========================================
# DESIGN STYLE : ADAPTATIVE GLASS NÉON (CSS)
# ==========================================
st.markdown("""
    <style>
        .neon-box {
            background-color: rgba(128, 128, 128, 0.08);
            border: 1px solid rgba(128, 128, 128, 0.15);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            min-height: 220px;
            transition: all 0.5s ease;
            display: flex;
            flex-direction: column;
        }
        .neon-extract { box-shadow: 0 0 25px rgba(128, 128, 128, 0.15); }
        .neon-transform { box-shadow: 0 0 30px rgba(10, 132, 255, 0.25); }
        .neon-kpi { box-shadow: 0 0 30px rgba(255, 159, 10, 0.25); }
        .neon-load { box-shadow: 0 0 30px rgba(48, 209, 88, 0.25); }
        .neon-box strong {
            color: var(--text-color);
            font-size: 1.1rem;
            letter-spacing: 0.5px;
            display: block;
            margin-bottom: 2px;
        }
        .neon-box small {
            color: var(--text-color);
            opacity: 0.6;
            font-size: 0.8rem;
            display: block;
            margin-bottom: 12px;
        }
        .neon-arrow {
            text-align: center;
            margin-top: 90px;
            font-weight: 300;
            color: var(--text-color);
            opacity: 0.3;
        }
        .status-text {
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: auto;
            padding-top: 8px;
            border-top: 1px solid rgba(128, 128, 128, 0.1);
        }
        .log-text {
            font-size: 0.76rem;
            font-family: 'SF Mono', Monaco, Consolas, monospace;
            margin-top: 4px;
            color: var(--text-color);
            opacity: 0.75;
            line-height: 1.35;
            white-space: pre-line;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Pipeline ETL - Execution en temps reel")
st.markdown(
    "Lance le vrai pipeline (extraction des 8 sources, transformation, calcul des KPI, "
    "chargement en base) et observe chaque etape s'executer reellement."
)

# ==========================================
# CADRE D'AFFICHAGE DES 4 ETAPES
# ==========================================
columns = st.columns([3, 0.4, 3, 0.4, 3, 0.4, 3])
placeholders = {}
labels = [
    ("extract", "1. EXTRACT", "8 sources brutes", "neon-extract"),
    ("transform", "2. TRANSFORM", "Nettoyage & harmonisation", "neon-transform"),
    ("kpi", "3. CALCUL KPI", "Normalisation & score", "neon-kpi"),
    ("load", "4. LOAD", "PostgreSQL (Docker)", "neon-load"),
]


def render_box(key: str, title: str, subtitle: str, css_class: str, status: str, log: str) -> str:
    return f"""
        <div class='neon-box {css_class}'>
            <strong>{title}</strong>
            <small>{subtitle}</small>
            <div class='log-text'>{log}</div>
            <div class='status-text'>Statut : {status}</div>
        </div>
    """


col_index = 0
for key, title, subtitle, css_class in labels:
    with columns[col_index]:
        placeholders[key] = st.empty()
        placeholders[key].markdown(
            render_box(key, title, subtitle, css_class, "⚪ En attente", "..."), unsafe_allow_html=True
        )
    col_index += 1
    if col_index < len(columns):
        with columns[col_index]:
            st.markdown("<h3 class='neon-arrow'>→</h3>", unsafe_allow_html=True)
        col_index += 1


def update(key: str, title: str, subtitle: str, css_class: str, status: str, log: str) -> None:
    placeholders[key].markdown(render_box(key, title, subtitle, css_class, status, log), unsafe_allow_html=True)


st.markdown("---")

# ==========================================
# EXECUTION REELLE DU PIPELINE
# ==========================================

def run_pipeline() -> None:
    # ---- 1. EXTRACT ----
    update("extract", "1. EXTRACT", "8 sources brutes", "neon-extract", "🔵 En cours...", "Lecture de transactions.npz...")
    df_transactions_raw = extract.extract_transactions_npz()
    log_extract = f"transactions.npz : {len(df_transactions_raw):,} lignes brutes\n"
    update("extract", "1. EXTRACT", "8 sources brutes", "neon-extract", "🔵 En cours...", log_extract + "Telechargement DVF (geo-dvf, 2025)...")

    df_dvf_2025 = extract.extract_dvf(2025)
    log_extract += f"DVF 2025 (data.gouv.fr) : {len(df_dvf_2025):,} lignes\n"
    update("extract", "1. EXTRACT", "8 sources brutes", "neon-extract", "🔵 En cours...", log_extract + "Carte des loyers 2024/2025...")

    loyers_2024 = extract.extract_loyers_complement(2024)
    loyers_2025 = extract.extract_loyers_complement(2025)
    log_extract += f"Carte des loyers : {len(loyers_2024) + len(loyers_2025):,} lignes (2024+2025)\n"
    update("extract", "1. EXTRACT", "8 sources brutes", "neon-extract", "🔵 En cours...", log_extract + "IRCOM (revenus des menages, DGFiP)...")

    ircom_df = extract.extract_ircom()
    log_extract += f"IRCOM : {len(ircom_df):,} lignes\n"
    update("extract", "1. EXTRACT", "8 sources brutes", "neon-extract", "🔵 En cours...", log_extract + "LOVAC (logements vacants, Cerema)...")

    lovac_df = extract.extract_lovac()
    log_extract += f"LOVAC : {len(lovac_df):,} communes\n"
    update("extract", "1. EXTRACT", "8 sources brutes", "neon-extract", "🔵 En cours...", log_extract + "Referentiel communes (geo.api.gouv.fr)...")

    communes_api = API.recuperer_toutes_communes()
    log_extract += f"Communes (API) : {len(communes_api):,} communes\n"
    update("extract", "1. EXTRACT", "8 sources brutes", "neon-extract", "🔵 En cours...", log_extract + "IRL (API SDMX INSEE)...")

    irl_df = API.recuperer_irl()

    ti_df = extract.extract_webstat_series(PROJECT_ROOT / "data/raw/additional_data/new_housing_loans_interest_rate.csv")
    flux_df = extract.extract_webstat_series(PROJECT_ROOT / "data/raw/additional_data/new_housing_loans_flow.csv")
    debt_df = extract.extract_webstat_series(PROJECT_ROOT / "data/raw/additional_data/household_debt_ratio.csv")
    log_extract += f"IRL + 3 series Banque de France : {len(irl_df)} trimestres, {len(ti_df) + len(flux_df) + len(debt_df)} observations"

    update("extract", "1. EXTRACT", "8 sources brutes", "neon-extract", "🟢 Termine", log_extract)

    # ---- 2. TRANSFORM ----
    update("transform", "2. TRANSFORM", "Nettoyage & harmonisation", "neon-transform", "🔵 En cours...", "Filtre qualite transactions (>= 5 sur 2022-2024)...")
    transactions = transform.transform_transactions(df_transactions_raw)
    log_transform = f"transactions : {len(transactions):,} lignes retenues\n"

    update("transform", "2. TRANSFORM", "Nettoyage & harmonisation", "neon-transform", "🔵 En cours...", log_transform + "Harmonisation loyers/foyers/parc...")
    loyers = transform.transform_loyers(pd.read_csv(PROJECT_ROOT / "data/raw/loyers.csv"), [loyers_2024, loyers_2025])
    foyers = transform.transform_foyers_fiscaux(pd.read_csv(PROJECT_ROOT / "data/raw/foyers_fiscaux.csv"), ircom_df)
    parc = transform.transform_parc_immobilier(pd.read_csv(PROJECT_ROOT / "data/raw/parc_immobilier.csv"), lovac_df)
    log_transform += f"loyers : {len(loyers):,} | foyers_fiscaux : {len(foyers):,} | parc_immobilier : {len(parc):,}\n"

    update("transform", "2. TRANSFORM", "Nettoyage & harmonisation", "neon-transform", "🔵 En cours...", log_transform + "Consolidation indicateurs macro + referentiel communes...")
    macro = transform.transform_indicateurs_macro(ti_df, flux_df, debt_df, irl_df)
    communes = transform.build_communes(communes_api)
    demographics = transform.build_demographics(communes_api)
    log_transform += f"indicateurs_macro : {len(macro):,} mois | communes : {len(communes):,}"

    update("transform", "2. TRANSFORM", "Nettoyage & harmonisation", "neon-transform", "🟢 Termine", log_transform)

    # ---- 3. CALCUL KPI ----
    update("kpi", "3. CALCUL KPI", "Normalisation & score", "neon-kpi", "🔵 En cours...", "Calcul rendement brut, taux de vacance, effort fiscal, prix m2 median...")
    score = transform.compute_kpi(transactions, loyers, foyers, parc)
    top = score.dropna(subset=["score_attractivite"]).sort_values("score_attractivite", ascending=False).iloc[0]
    log_kpi = (
        f"score_attractivite : {len(score):,} communes evaluees\n"
        f"annee de reference : {score['annee_ref'].iloc[0]}\n"
        f"meilleur score : id_ville {int(top['id_ville'])} ({top['score_attractivite']:.1f}/100)"
    )
    update("kpi", "3. CALCUL KPI", "Normalisation & score", "neon-kpi", "🟢 Termine", log_kpi)

    # ---- 4. LOAD ----
    update("load", "4. LOAD", "PostgreSQL (Docker)", "neon-load", "🔵 En cours...", "Ecriture des CSV dans data/final/...")
    valid_ids = set(communes["id_ville"])
    outputs = {
        "communes": communes,
        "demographics": demographics,
        "transactions": transactions[transactions["id_ville"].isin(valid_ids)],
        "loyers": loyers[loyers["id_ville"].isin(valid_ids)],
        "foyers_fiscaux": foyers[foyers["id_ville"].isin(valid_ids)],
        "parc_immobilier": parc[parc["id_ville"].isin(valid_ids)],
        "indicateurs_macro": macro,
        "score_attractivite": score[score["id_ville"].isin(valid_ids)],
    }
    load_module.DATA_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, df in outputs.items():
        df.to_csv(load_module.DATA_DIR / f"{table_name}.csv", index=False)

    log_load = "Connexion PostgreSQL...\n"
    update("load", "4. LOAD", "PostgreSQL (Docker)", "neon-load", "🔵 En cours...", log_load)

    with load_module.engine.begin() as conn:
        for table_name in load_module.TABLES:
            conn.execute(load_module.text(f"TRUNCATE operationnel.{table_name} CASCADE"))

    for table_name in load_module.TABLES:
        load_module.load_table(table_name)
        log_load += f"{table_name} : {len(outputs[table_name]):,} lignes inserees\n"
        update("load", "4. LOAD", "PostgreSQL (Docker)", "neon-load", "🔵 En cours...", log_load)

    update("load", "4. LOAD", "PostgreSQL (Docker)", "neon-load", "🟢 Termine", log_load + "Base synchronisee.")


if st.button("Lancer le pipeline complet", type="primary"):
    lock_conn = load_module.engine.connect()
    acquired = lock_conn.execute(
        load_module.text("SELECT pg_try_advisory_lock(:key)"), {"key": PIPELINE_LOCK_KEY}
    ).scalar()

    if not acquired:
        st.error(
            "Un chargement est deja en cours (verrou actif en base) - "
            "attends qu'il se termine avant d'en relancer un, sinon les donnees "
            "seraient inserees en double."
        )
        lock_conn.close()
    else:
        try:
            run_pipeline()
            st.success("Pipeline complet execute avec succes.")
        finally:
            lock_conn.execute(load_module.text("SELECT pg_advisory_unlock(:key)"), {"key": PIPELINE_LOCK_KEY})
            lock_conn.close()
