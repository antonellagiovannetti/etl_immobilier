import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
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
    # search_path fixe sur le schema operationnel : toutes les tables du
    # projet y vivent (cf. db/schema.sql), rien dans public.
    return sa.create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": "-csearch_path=operationnel"},
    )

try:
    engine = init_connection()
except Exception as e:
    st.error("Impossible de se connecter à la base de données PostgreSQL.")
    st.caption(str(e))
    st.stop()

# ---------------------------------------------------------
# CHARGEMENT DES DONNÉES DEPUIS SCORE_ATTRACTIVITE
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def load_dashboard_data():
    query = """
        SELECT c.ville, trim(c.departement) AS departement, c.code_insee,
               c.latitude, c.longitude,
               s.prix_m2_median, s.loyer_m2_moyen, s.rendement_brut,
               s.taux_vacance, s.ratio_effort_fiscal, s.score_attractivite,
               s.n_transactions
        FROM operationnel.score_attractivite s
        JOIN operationnel.communes c ON s.id_ville = c.id_ville
        WHERE s.score_attractivite IS NOT NULL
        ORDER BY s.score_attractivite DESC;
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=300)
def load_densite_par_departement():
    query = """
        SELECT trim(c.departement) AS departement, avg(d.densite) AS densite
        FROM operationnel.communes c
        JOIN operationnel.demographics d ON c.id_ville = d.id_ville
        WHERE d.densite IS NOT NULL
        GROUP BY trim(c.departement);
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=300)
def load_annees_disponibles() -> list[int]:
    query = "SELECT DISTINCT annee FROM operationnel.transactions ORDER BY annee DESC;"
    return pd.read_sql(query, engine)["annee"].tolist()

@st.cache_data(ttl=300)
def load_prix_par_departement(annee: int):
    query = """
        SELECT trim(c.departement) AS departement,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY t.prix_m2) AS prix_m2_median
        FROM operationnel.transactions t
        JOIN operationnel.communes c ON t.id_ville = c.id_ville
        WHERE t.annee = %(annee)s
        GROUP BY trim(c.departement);
    """
    return pd.read_sql(query, engine, params={"annee": annee})


try:
    df = load_dashboard_data()
    densite_dept = load_densite_par_departement()
    annees_disponibles = load_annees_disponibles()
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
        "ne contient pas encore de données (relance le pipeline ETL)."
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

# Prix au m2 : toujours la derniere annee reellement disponible dans les
# transactions (pas de prediction sur 2025/2026, la donnee n'existe pas
# encore cote DVF - publiee avec ~6 mois de retard). Affiche clairement
# l'annee utilisee pour eviter toute ambiguite.
derniere_annee_prix = max(annees_disponibles)
prix_dept_derniere_annee = load_prix_par_departement(derniere_annee_prix)

# Fonction reutilisable : carte par commune coloree selon une colonne du KPI
def render_commune_map(data: pd.DataFrame, value_col: str, colors: list[str], legend: str, map_key: str):
    map_data = data.dropna(subset=["latitude", "longitude", value_col])
    map_size = st.slider(
        "Nombre de communes affichées (les mieux classées)",
        min_value=10,
        max_value=min(2000, len(map_data)) if len(map_data) > 10 else 10,
        value=min(200, len(map_data)) if len(map_data) > 0 else 10,
        step=10,
        key=f"slider_{map_key}",
    )
    map_data = map_data.head(map_size)

    if map_data.empty:
        st.info("Aucune commune géolocalisée à afficher pour ce filtre.")
        return

    colormap = folium.LinearColormap(
        colors=colors,
        vmin=data[value_col].min(),
        vmax=data[value_col].max(),
        caption=legend,
    )
    france_map = folium.Map(location=[46.6, 2.6], zoom_start=6, tiles="cartodbpositron")
    for _, row in map_data.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color=colormap(row[value_col]),
            fill=True,
            fill_color=colormap(row[value_col]),
            fill_opacity=0.85,
            popup=(
                f"<b>{row['ville']}</b> ({row['departement']})<br>"
                f"{legend} : {row[value_col]:.2f}<br>"
                f"Score : {row['score_attractivite']:.1f}/100"
            ),
        ).add_to(france_map)
    colormap.add_to(france_map)
    st_folium(france_map, use_container_width=True, height=520, returned_objects=[], key=f"map_{map_key}")


# Section 0 : indicateurs cles (moyennes sur le filtre courant)
st.subheader("Vue d'ensemble")
st.caption(
    "Score d'attractivité = 35% rendement brut + 25% ratio d'effort fiscal (inversé) "
    "+ 20% revenu fiscal moyen + 20% taux de vacance (inversé), chaque composante "
    "normalisée de 0 à 100 au niveau national."
)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Communes évaluées", f"{len(df_filtered):,}")
kpi2.metric("Score moyen", f"{df_filtered['score_attractivite'].mean():.1f}/100")
kpi3.metric("Rendement brut moyen", f"{df_filtered['rendement_brut'].mean():.2f} %")
kpi4.metric("Taux de vacance moyen", f"{df_filtered['taux_vacance'].mean():.2f} %")

st.markdown("---")

# Section 1 : Le Top 10 National / Filtré
st.subheader("🏆 Top 10 des Communes les plus attractives")
st.caption(
    "Classement par score_attractivite décroissant, parmi les communes ayant ≥ 5 "
    "transactions sur la dernière année disponible (marché actuel, pas une moyenne "
    "pluriannuelle)."
)
top_10 = df_filtered.head(10)

# Affichage d'un tableau propre et dynamique
st.dataframe(
    top_10,
    column_config={
        "ville": "Ville",
        "departement": "Département",
        "code_insee": None,
        "latitude": None,
        "longitude": None,
        "prix_m2_median": st.column_config.NumberColumn("Prix médian (€/m²)", format="%d €"),
        "loyer_m2_moyen": st.column_config.NumberColumn("Loyer moyen (€/m²)", format="%.2f €"),
        "rendement_brut": st.column_config.NumberColumn("Rendement Brut", format="%.2f %%"),
        "taux_vacance": st.column_config.NumberColumn("Taux de Vacance", format="%.2f %%"),
        "ratio_effort_fiscal": st.column_config.NumberColumn("Effort fiscal", format="%.2f"),
        "n_transactions": "Nb transactions",
        "score_attractivite": st.column_config.ProgressColumn("Score Attractivité", format="%.1f", min_value=0, max_value=100)
    },
    hide_index=True,
    use_container_width=True
)

st.markdown("---")

# Section 2 : Carte interactive (Folium) — colormap du score d'attractivite
st.subheader("🗺️ Carte du score d'attractivité")
st.caption("score_attractivite (0-100) — voir la formule dans la section *Vue d'ensemble* ci-dessus.")
render_commune_map(
    df_filtered, "score_attractivite",
    colors=["#d73027", "#fee08b", "#1a9850"],
    legend="Score d'attractivité (0-100)",
    map_key="score",
)

st.markdown("---")

# Section 3 : Carte du ratio d'effort fiscal (indicateur de risque locataire)
st.subheader("🗺️ Carte du ratio d'effort fiscal")
st.caption(
    "ratio_effort_fiscal = (loyer_m2_moyen × 12 × 50) / revenu_fiscal_moyen — "
    "indicateur de risque locataire : plus il est élevé, plus le loyer pèse lourd "
    "dans le revenu des habitants de la commune (plus bas = mieux)."
)
render_commune_map(
    df_filtered, "ratio_effort_fiscal",
    colors=["#1a9850", "#fee08b", "#d73027"],
    legend="Ratio d'effort fiscal",
    map_key="effort",
)

st.markdown("---")

# Section 4 : Occupé vs vacant, pour une commune du Top 10
st.subheader("Occupé vs vacant — commune sélectionnée")
st.caption("taux_vacance = logements vacants / logements totaux × 100, sur l'année de référence du score.")
selected_ville = st.selectbox("Commune du Top 10", top_10["ville"])
taux_vacance_selection = top_10.loc[top_10["ville"] == selected_ville, "taux_vacance"].iloc[0]
fig, ax = plt.subplots()
ax.pie(
    [100 - taux_vacance_selection, taux_vacance_selection],
    labels=["Occupé", "Vacant"],
    autopct="%.1f%%",
    colors=["#1a9850", "#d73027"],
    startangle=90,
)
ax.axis("equal")
st.pyplot(fig)

st.markdown("---")

# Section 5 : Choroplethes prix au m2 / densite — par commune si un
# departement est selectionne (contour reel de chaque ville), sinon par
# departement pour garder une carte nationale lisible et rapide.
DEPARTEMENTS_GEOJSON = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"


def render_choropleth(data: pd.DataFrame, columns: list[str], fill_color: str, legend: str, map_key: str):
    carte = folium.Map(location=[46.6, 2.6], zoom_start=5, tiles="cartodbpositron")
    choropleth = folium.Choropleth(
        geo_data=DEPARTEMENTS_GEOJSON,
        data=data,
        columns=columns,
        key_on="feature.properties.code",
        fill_color=fill_color,
        fill_opacity=0.8,
        line_opacity=0.3,
        nan_fill_color="white",
        legend_name=legend,
    ).add_to(carte)
    # Survol : nom du departement (le contour seul ne le montre pas)
    choropleth.geojson.add_child(folium.GeoJsonTooltip(fields=["nom"], aliases=["Département :"]))
    st_folium(carte, use_container_width=True, height=450, returned_objects=[], key=f"choropleth_{map_key}")


st.subheader("🗺️ Cartes par département")

col3, col4 = st.columns(2)
with col3:
    st.markdown(f"**Prix médian au m² — année {derniere_annee_prix} (dernière année disponible)**")
    st.caption(
        f"Médiane du prix au m² des transactions {derniere_annee_prix} par département. "
        "Pas de projection sur les années suivantes tant que les données ne sont pas "
        "publiées (DVF publié avec ~6 mois de retard) : donnée réelle uniquement."
    )
    prix_dept_filtre = prix_dept_derniere_annee[
        prix_dept_derniere_annee["departement"].isin(selected_dept)
    ] if selected_dept else prix_dept_derniere_annee
    render_choropleth(
        prix_dept_filtre, ["departement", "prix_m2_median"],
        "YlOrRd", "Prix médian (€/m²)", "prix_dept",
    )
with col4:
    st.markdown("**Densité de population (hab/km², moyenne par département)**")
    st.caption("population / superficie_km2, moyenne des communes du département (source geo.api.gouv.fr).")
    densite_dept_filtre = densite_dept[
        densite_dept["departement"].isin(selected_dept)
    ] if selected_dept else densite_dept
    render_choropleth(
        densite_dept_filtre, ["departement", "densite"],
        "PuBu", "Densité (habitants/km²)", "densite_dept",
    )

st.caption(
    "Cartes limitées à la France métropolitaine (contours des départements "
    "d'outre-mer non disponibles dans le fond de carte utilisé)."
)
