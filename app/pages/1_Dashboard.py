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
        SELECT c.ville, trim(c.departement) AS departement, c.latitude, c.longitude,
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
def load_transactions_vs_taux_interet():
    query_transactions = """
        SELECT extract(year FROM date_transaction)::int AS annee,
               extract(month FROM date_transaction)::int AS mois,
               count(*) AS nb_transactions,
               avg(prix) AS montant_moyen
        FROM operationnel.transactions
        GROUP BY 1, 2;
    """
    query_macro = """
        SELECT annee, mois, taux_interet
        FROM operationnel.indicateurs_macro
        WHERE taux_interet IS NOT NULL AND mois IS NOT NULL;
    """
    transactions_mensuelles = pd.read_sql(query_transactions, engine)
    taux_interet = pd.read_sql(query_macro, engine)
    return transactions_mensuelles.merge(taux_interet, on=["annee", "mois"], how="inner")


try:
    df = load_dashboard_data()
    densite_dept = load_densite_par_departement()
    transactions_taux = load_transactions_vs_taux_interet()
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

# Section 0 : indicateurs cles (moyennes sur le filtre courant)
st.subheader("Vue d'ensemble")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Communes évaluées", f"{len(df_filtered):,}")
kpi2.metric("Score moyen", f"{df_filtered['score_attractivite'].mean():.1f}/100")
kpi3.metric("Rendement brut moyen", f"{df_filtered['rendement_brut'].mean():.2f} %")
kpi4.metric("Taux de vacance moyen", f"{df_filtered['taux_vacance'].mean():.2f} %")

st.markdown("---")

# Section 1 : Le Top 10 National / Filtré
st.subheader("🏆 Top 10 des Communes les plus attractives")
top_10 = df_filtered.head(10)

# Affichage d'un tableau propre et dynamique
st.dataframe(
    top_10,
    column_config={
        "ville": "Ville",
        "departement": "Département",
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
map_data = df_filtered.dropna(subset=["latitude", "longitude"])
map_size = st.slider(
    "Nombre de communes affichées sur la carte (les mieux classées)",
    min_value=10, max_value=min(2000, len(map_data)) if len(map_data) > 10 else 10,
    value=min(200, len(map_data)) if len(map_data) > 0 else 10,
    step=10,
)
map_data = map_data.head(map_size)

if map_data.empty:
    st.info("Aucune commune géolocalisée à afficher pour ce filtre.")
else:
    colormap = folium.LinearColormap(
        colors=["#d73027", "#fee08b", "#1a9850"],
        vmin=df_filtered["score_attractivite"].min(),
        vmax=df_filtered["score_attractivite"].max(),
        caption="Score d'attractivité (0-100)",
    )
    france_map = folium.Map(location=[46.6, 2.6], zoom_start=6, tiles="cartodbpositron")
    for _, row in map_data.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color=colormap(row["score_attractivite"]),
            fill=True,
            fill_color=colormap(row["score_attractivite"]),
            fill_opacity=0.85,
            popup=(
                f"<b>{row['ville']}</b> ({row['departement']})<br>"
                f"Score : {row['score_attractivite']:.1f}/100<br>"
                f"Rendement brut : {row['rendement_brut']:.2f} %<br>"
                f"Prix médian : {row['prix_m2_median']:.0f} €/m²"
            ),
        ).add_to(france_map)
    colormap.add_to(france_map)
    st_folium(france_map, use_container_width=True, height=520, returned_objects=[])

st.markdown("---")

# Section 3 : Graphiques Métier (Effort fiscal et Vacance)
st.subheader("Analyses des indicateurs clés (Top 10)")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Ratio d'effort fiscal (Top 10)**")
    # Le rendement brut est deja visible dans le tableau du Top 10 ci-dessus ;
    # le ratio d'effort fiscal (loyer / revenu fiscal) apporte une info neuve.
    st.bar_chart(top_10.set_index("ville")["ratio_effort_fiscal"])

with col2:
    st.markdown("**Occupé vs vacant — commune sélectionnée**")
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

# Section 4 : Cartes choroplethes par departement (prix au m2, densite)
st.subheader("🗺️ Cartes par département")
DEPARTEMENTS_GEOJSON = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"

col3, col4 = st.columns(2)

with col3:
    st.markdown("**Prix médian au m² (moyenne par département)**")
    prix_dept = df_filtered.groupby("departement", as_index=False)["prix_m2_median"].mean()
    carte_prix = folium.Map(location=[46.6, 2.6], zoom_start=5, tiles="cartodbpositron")
    folium.Choropleth(
        geo_data=DEPARTEMENTS_GEOJSON,
        data=prix_dept,
        columns=["departement", "prix_m2_median"],
        key_on="feature.properties.code",
        fill_color="YlOrRd",
        fill_opacity=0.8,
        line_opacity=0.3,
        nan_fill_color="white",
        legend_name="Prix médian (€/m²)",
    ).add_to(carte_prix)
    st_folium(carte_prix, use_container_width=True, height=450, returned_objects=[])

with col4:
    st.markdown("**Densité de population (hab/km², moyenne par département)**")
    carte_densite = folium.Map(location=[46.6, 2.6], zoom_start=5, tiles="cartodbpositron")
    folium.Choropleth(
        geo_data=DEPARTEMENTS_GEOJSON,
        data=densite_dept,
        columns=["departement", "densite"],
        key_on="feature.properties.code",
        fill_color="PuBu",
        fill_opacity=0.8,
        line_opacity=0.3,
        nan_fill_color="white",
        legend_name="Densité (habitants/km²)",
    ).add_to(carte_densite)
    st_folium(carte_densite, use_container_width=True, height=450, returned_objects=[])

st.caption(
    "Cartes limitées à la France métropolitaine (contours des départements d'outre-mer "
    "non disponibles dans le fond de carte utilisé)."
)

st.markdown("---")

# Section 5 : Annexe — taux d'interet vs volume de transactions (hors score d'attractivite)
st.subheader("📎 Annexe — Marché du crédit vs volume de transactions")
st.caption(
    "Hors périmètre du score d'attractivité, mais utile en contexte : le nombre de "
    "transactions mensuelles suit-il le taux d'intérêt moyen des crédits immobiliers ?"
)

fig2, ax2 = plt.subplots()
scatter = ax2.scatter(
    transactions_taux["taux_interet"],
    transactions_taux["nb_transactions"],
    c=transactions_taux["annee"],
    cmap="viridis",
    alpha=0.75,
)
ax2.set_xlabel("Taux d'intérêt moyen des crédits (%)")
ax2.set_ylabel("Nombre de transactions (par mois)")
fig2.colorbar(scatter, ax=ax2, label="Année")
st.pyplot(fig2)
