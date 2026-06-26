import streamlit as st
import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv
import os
from pathlib import Path

# Configuration de la page
st.set_page_config(page_title="Dashboard Interactif", page_icon="📊", layout="wide")

# ---------------------------------------------------------
# CONNEXION À LA BASE DE DONNÉES POSTGRESQL (Docker)
# ---------------------------------------------------------
@st.cache_resource
def init_connection():
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    required_vars = [
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise RuntimeError(
            "Variables d'environnement manquantes dans .env : "
            + ", ".join(missing_vars)
        )

    database_url = sa.URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=os.getenv("POSTGRES_DB"),
    )
    return sa.create_engine(database_url, pool_pre_ping=True)

try:
    engine = init_connection()
except Exception as e:
    st.error("Impossible de se connecter à la base de données PostgreSQL.")
    st.caption(str(e))
    st.stop()

# ---------------------------------------------------------
# CHARGEMENT DES DONNÉES DEPUIS SCORE_ATTRACTIVITE
# ---------------------------------------------------------
@st.cache_data
def load_dashboard_data():
    query = """
        SELECT c.ville, c.departement, s.prix_m2_median, s.loyer_m2_moyen, 
               s.rendement_brut, s.taux_vacance, s.ratio_effort_fiscal, s.score_attractivite
        FROM score_attractivite s
        JOIN communes c ON s.id_ville = c.id_ville
        ORDER BY s.score_attractivite DESC;
    """
    return pd.read_sql(query, engine)

try:
    df = load_dashboard_data()
except Exception as e:
    st.error("Impossible de charger les données du dashboard depuis PostgreSQL.")
    st.caption(str(e))
    st.stop()

# ---------------------------------------------------------
# AFFICHAGE DU DASHBOARD
# ---------------------------------------------------------
st.title("Tableau de Bord de l'Attractivité Immobilière")
st.markdown("Classement national des communes selon le ratio *rendement / risque / accessibilité*.")

if df.empty:
    st.warning(
        "La connexion PostgreSQL fonctionne, mais la table score_attractivite "
        "ne contient pas encore de données."
    )
    st.stop()

# Filtres dans la barre latérale pour affiner le Top 10
st.sidebar.header("Filtres du Dashboard")
selected_dept = st.sidebar.multiselect(
    "Filtrer par département", 
    options=sorted(df["departement"].unique()),
    default=[]
)

# Application du filtre si sélectionné
df_filtered = df[df["departement"].isin(selected_dept)] if selected_dept else df

# Section 1 : Le Top 10 National / Filtré
st.subheader("🏆 Top 10 des Communes les plus attractives")
top_10 = df_filtered.head(10)

# Affichage d'un tableau propre et dynamique
st.dataframe(
    top_10,
    column_config={
        "ville": "Ville",
        "departement": "Département",
        "prix_m2_median": st.column_config.NumberColumn("Prix médian (€/m²)", format="%d €"),
        "loyer_m2_moyen": st.column_config.NumberColumn("Loyer moyen (€/m²)", format="%.2f €"),
        "rendement_brut": st.column_config.NumberColumn("Rendement Brut", format="%.2f %%"),
        "taux_vacance": st.column_config.NumberColumn("Taux de Vacance", format="%.2f %%"),
        "score_attractivite": st.column_config.ProgressColumn("Score Attractivité", format="%.1f", min_value=0, max_value=100)
    },
    hide_index=True,
    use_container_width=True
)

st.markdown("---")

# Section 2 : Graphiques Métier (Rendement et Vacance)
st.subheader("Analyses des indicateurs clés (Top 10)")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Histogramme du rendement brut (%)**")
    # Utilisation du graphique natif de Streamlit pour la simplicité et la performance
    st.bar_chart(top_10.set_index("ville")["rendement_brut"])

with col2:
    st.markdown("**Comparatif du Taux de Vacance (%)**")
    # Un line_chart ou bar_chart exprime très bien la variance de la vacance entre les villes du Top
    st.line_chart(top_10.set_index("ville")["taux_vacance"])
