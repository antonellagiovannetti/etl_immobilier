import streamlit as st
import time

# Configuration de la page
st.set_page_config(page_title="Demo Pipeline ETL", layout="wide")

# ==========================================
# DESIGN STYLE : GLASS NÉON MODE (CSS)
# ==========================================
st.markdown("""
    <style>
        
        
        /* Style de base des cartes translucides (Glassmorphism) */
        .neon-box {
            background-color: rgba(20, 20, 25, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            min-height: 150px;
            transition: all 0.5s ease;
        }
        
        /* Halos Néons spécifiques à chaque étape */
        .neon-extract {
            box-shadow: 0 0 25px rgba(142, 142, 147, 0.15); /* Halo Blanc/Gris discret */
        }
        .neon-transform {
            box-shadow: 0 0 30px rgba(10, 132, 255, 0.25);  /* Halo Bleu néon */
        }
        .neon-kpi {
            box-shadow: 0 0 30px rgba(255, 159, 10, 0.25);   /* Halo Orange néon */
        }
        .neon-load {
            box-shadow: 0 0 30px rgba(48, 209, 88, 0.25);   /* Halo Vert néon */
        }
        
        /* Typographies et détails */
        .neon-box strong {
            color: #FFFFFF;
            font-size: 1.15rem;
            letter-spacing: 0.5px;
            display: block;
            margin-bottom: 4px;
        }
        .neon-box small {
            color: #8E8E93;
            font-size: 0.85rem;
        }
        .neon-arrow {
            text-align: center;
            color: #2C2C2E;
            margin-top: 40px;
            font-weight: 300;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
        }
        .status-text {
            margin-top: 12px;
            font-size: 0.9rem;
            font-weight: 500;
            color: #F2F2F7;
        }
        .log-text {
            color: #AEAEB2;
            font-size: 0.8rem;
            font-family: monospace;
            margin-top: 6px;
            line-height: 1.3;
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
    st.session_state.log_extract = ""
if "log_transform" not in st.session_state:
    st.session_state.log_transform = ""
if "log_kpi" not in st.session_state:
    st.session_state.log_kpi = ""
if "log_load" not in st.session_state:
    st.session_state.log_load = ""

# ==========================================
# INTERFACE GRAPHIQUE : SCHÉMA ET LOGS
# ==========================================

c1, arrow1, c2, arrow2, c3, arrow3, c4 = st.columns([3, 0.4, 3, 0.4, 3, 0.4, 3])

with c1:
    st.markdown("<div class='neon-box neon-extract'><strong>1. EXTRACT</strong><br><small>Fichiers sources (CSV, NPZ)</small></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='status-text'>Statut : {st.session_state.status_extract}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='log-text'>{st.session_state.log_extract}</div>", unsafe_allow_html=True)

with arrow1:
    st.markdown("<h3 class='neon-arrow'>→</h3>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='neon-box neon-transform'><strong>2. TRANSFORM</strong><br><small>Nettoyage & Harmonisation</small></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='status-text'>Statut : {st.session_state.status_transform}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='log-text'>{st.session_state.log_transform}</div>", unsafe_allow_html=True)

with arrow2:
    st.markdown("<h3 class='neon-arrow'>→</h3>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='neon-box neon-kpi'><strong>3. CALCUL KPI</strong><br><small>Normalisation & Scores</small></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='status-text'>Statut : {st.session_state.status_kpi}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='log-text'>{st.session_state.log_kpi}</div>", unsafe_allow_html=True)

with arrow3:
    st.markdown("<h3 class='neon-arrow'>→</h3>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='neon-box neon-load'><strong>4. LOAD</strong><br><small>PostgreSQL (Docker)</small></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='status-text'>Statut : {st.session_state.status_load}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='log-text'>{st.session_state.log_load}</div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# BOUTON UNIQUE ET LOGIQUE D'EXÉCUTION
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
    
    st.session_state.log_transform = "Nettoyage des prix aberrants (500-30k€/m²)..."
    st.rerun() if time.sleep(0.8) else None
    
    st.session_state.status_transform = "🟢 Termine"
    st.session_state.log_transform = "Donnees nettes et coherentes"
    
    # ---- 3. CALCUL KPI ----
    st.session_state.status_kpi = "🔵 En cours..."
    st.session_state.log_kpi = "Calcul rendement brut et ratio effort fiscal..."
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
    st.session_state.log_extract = ""
    st.session_state.log_transform = ""
    st.session_state.log_kpi = ""
    st.session_state.log_load = ""
    st.rerun()