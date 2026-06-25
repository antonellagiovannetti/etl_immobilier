import streamlit as st
import time

# Configuration de la page
st.set_page_config(page_title="Demo Pipeline ETL", layout="wide")

# ==========================================
# DESIGN STYLE : ADAPTATIVE GLASS NÉON (CSS)
# ==========================================
st.markdown("""
    <style>
        /* Boîte translucide adaptative utilisant les variables globales Streamlit */
        .neon-box {
            background-color: rgba(128, 128, 128, 0.08);
            border: 1px solid rgba(128, 128, 128, 0.15);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            min-height: 180px; /* Augmenté pour accueillir confortablement les logs internes */
            transition: all 0.5s ease;
            display: flex;
            flex-direction: column;
            justify-content:开;
        }
        
        /* Halos lumineux subtils et adaptatifs (ajustés selon l'intensité) */
        .neon-extract {
            box-shadow: 0 0 25px rgba(128, 128, 128, 0.15);
        }
        .neon-transform {
            box-shadow: 0 0 30px rgba(10, 132, 255, 0.25);
        }
        .neon-kpi {
            box-shadow: 0 0 30px rgba(255, 159, 10, 0.25);
        }
        .neon-load {
            box-shadow: 0 0 30px rgba(48, 209, 88, 0.25);
        }
        
        /* Typographies synchronisées avec les couleurs de police du thème actif */
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
            margin-top: 45px;
            font-weight: 300;
            color: var(--text-color);
            opacity: 0.3;
        }
        .status-text {
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: auto; /* Aligne le statut vers le bas de la boîte */
            padding-top: 8px;
            border-top: 1px solid rgba(128, 128, 128, 0.1);
        }
        .log-text {
            font-size: 0.78rem;
            font-family: 'SF Mono', Monaco, Consolas, monospace;
            margin-top: 4px;
            color: var(--text-color);
            opacity: 0.7;
            line-height: 1.2;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Pipeline ETL - Execution en temps reel")
st.markdown("Lancez l'execution complete du pipeline pour observer le traitement des donnees.")

# ==========================================
# INITIALISATION DES ÉTATS (Session State)
# ==========================================
if "status_extract" not in st.session_state:
    st.session_state.status_extract = "⚪ En attente"
if "status_transform" not in st.session_state:
    st.session_state.status_transform = "⚪ En attente"
if "status_kpi" not in st.session_state:
    st.session_state.status_kpi = "⚪ En attente"
if "status_load" not in st.session_state:
    st.session_state.status_load = "⚪ En attente"

if "log_extract" not in st.session_state:
    st.session_state.log_extract = "..."
if "log_transform" not in st.session_state:
    st.session_state.log_transform = "..."
if "log_kpi" not in st.session_state:
    st.session_state.log_kpi = "..."
if "log_load" not in st.session_state:
    st.session_state.log_load = "..."

# ==========================================
# INTERFACE GRAPHIQUE : BLOCS INTERACTIFS
# ==========================================

c1, arrow1, c2, arrow2, c3, arrow3, c4 = st.columns([3, 0.4, 3, 0.4, 3, 0.4, 3])

with c1:
    st.markdown(f"""
        <div class='neon-box neon-extract'>
            <strong>1. EXTRACT</strong>
            <small>Fichiers sources (CSV, NPZ)</small>
            <div class='log-text'>{st.session_state.log_extract}</div>
            <div class='status-text'>Statut : {st.session_state.status_extract}</div>
        </div>
    """, unsafe_allow_html=True)

with arrow1:
    st.markdown("<h3 class='neon-arrow'>→</h3>", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class='neon-box neon-transform'>
            <strong>2. TRANSFORM</strong>
            <small>Nettoyage & Harmonisation</small>
            <div class='log-text'>{st.session_state.log_transform}</div>
            <div class='status-text'>Statut : {st.session_state.status_transform}</div>
        </div>
    """, unsafe_allow_html=True)

with arrow2:
    st.markdown("<h3 class='neon-arrow'>→</h3>", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class='neon-box neon-kpi'>
            <strong>3. CALCUL KPI</strong>
            <small>Normalisation & Scores</small>
            <div class='log-text'>{st.session_state.log_kpi}</div>
            <div class='status-text'>Statut : {st.session_state.status_kpi}</div>
        </div>
    """, unsafe_allow_html=True)

with arrow3:
    st.markdown("<h3 class='neon-arrow'>→</h3>", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
        <div class='neon-box neon-load'>
            <strong>4. LOAD</strong>
            <small>PostgreSQL (Docker)</small>
            <div class='log-text'>{st.session_state.log_load}</div>
            <div class='status-text'>Statut : {st.session_state.status_load}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# GESTION DES BOUTONS ET DU PIPELINE SÉQUENTIEL
# ==========================================

if st.button("Lancer le pipeline complet", type="primary"):
    
    # ---- 1. EXTRACT ----
    st.session_state.status_extract = "🔵 En cours..."
    st.session_state.log_extract = "Lecture de transactions.npz (9,1M lignes)..."
    st.rerun() if time.sleep(0.8) else None
    
    st.session_state.log_extract = "Extraction de loyers.csv et foyers_fiscaux.csv..."
    st.rerun() if time.sleep(0.8) else None
    
    st.session_state.status_extract = "🟢 Termine"
    st.session_state.log_extract = "8 fichiers extraits vers /raw"
    
    # ---- 2. TRANSFORM ----
    st.session_state.status_transform = "🔵 En cours..."
    st.session_state.log_transform = "Filtre qualite (communes >= 5 transactions)..."
    st.rerun() if time.sleep(1.0) else None
    
    st.session_state.log_transform = "Nettoyage des prix aberrants..."
    st.rerun() if time.sleep(0.8) else None
    
    st.session_state.status_transform = "🟢 Termine"
    st.session_state.log_transform = "Donnees nettes et coherentes"
    
    # ---- 3. CALCUL KPI ----
    st.session_state.status_kpi = "🔵 En cours..."
    st.session_state.log_kpi = "Calcul des 4 KPI bruts métier..."
    st.rerun() if time.sleep(1.0) else None
    
    st.session_state.log_kpi = "Normalisation nationale via normalize_kpi()..."
    st.rerun() if time.sleep(0.8) else None
    
    st.session_state.status_kpi = "🟢 Termine"
    st.session_state.log_kpi = "Table score_attractivite generee"
    
    # ---- 4. LOAD ----
    st.session_state.status_load = "🔵 En cours..."
    st.session_state.log_load = "Connexion PostgreSQL (Port 5432)..."
    st.rerun() if time.sleep(0.8) else None
    
    st.session_state.log_load = "Insertion en mode Batch (7 tables)..."
    st.rerun() if time.sleep(1.0) else None
    
    st.session_state.status_load = "🟢 Termine"
    st.session_state.log_load = "Base de donnees synchronisee"
    st.rerun()
    
    # ---- FIN DE TRAITEMENT & AUTO-RESET (5 SECONDES) ----
    time.sleep(5.0)
    
    st.session_state.status_extract = "⚪ En attente"
    st.session_state.status_transform = "⚪ En attente"
    st.session_state.status_kpi = "⚪ En attente"
    st.session_state.status_load = "⚪ En attente"
    st.session_state.log_extract = "..."
    st.session_state.log_transform = "..."
    st.session_state.log_kpi = "..."
    st.session_state.log_load = "..."
    st.rerun()