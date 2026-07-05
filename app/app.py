import streamlit as st

# Configuration globale de l'application
st.set_page_config(
    page_title="Investissement Immobilier 2026",
    page_icon="🏢",
    layout="wide"
)

st.title("Analyse du Marché Immobilier Résidentiel Français")
st.subheader("Question métier : Dans quelle ville française acheter pour investir en 2026 ?")

st.markdown("""
---
Bienvenue sur l'outil d'aide à la décision pour investisseurs locatifs. 
Ce pipeline ETL analyse plus de 9 millions de transactions immobilières et croise les données de l'INSEE, 
du DVF et de la Banque de France pour vous proposer les meilleures opportunités.

### Navigation
Utilisez la barre latérale à gauche pour naviguer entre les modules :
* **Dashboard** : Visualisez le Top 10 des communes, la carte interactive et les indicateurs clés.
* **Demo ETL** : Module complémentaire (bientôt disponible).
""")