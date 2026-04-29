import streamlit as st
from config.settings import CSS

st.set_page_config(
    page_title="QuantDesk — Aide à la Décision",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

navigation = st.navigation(
    [
        st.Page("pages/portefeuille.py",    title="Mon Portefeuille",    icon="📊"),
        st.Page("pages/analyse_actions.py", title="Analyse d'Actions",   icon="🔍"),
        st.Page("pages/secteurs.py",        title="Carte des Secteurs",  icon="🗺️"),
        st.Page("pages/methodologie.py",    title="Méthodologie",        icon="📐"),
    ],
    position="sidebar",
)

navigation.run()
