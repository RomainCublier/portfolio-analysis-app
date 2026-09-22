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
    {"Mon espace": [
        st.Page("pages/commencer.py", title="Construire mon projet", icon="🌱", default=True),
        st.Page("pages/catalogue.py", title="Explorer les supports", icon="🔎"),
        st.Page("pages/allocation.py", title="Tester une allocation", icon="⚖️"),
        st.Page("pages/backtest.py", title="Explorer un historique", icon="📈"),
        st.Page("pages/positions_reelles.py", title="Mon portefeuille réel", icon="📊"),
    ], "Laboratoire — fonctions expérimentales": [
        st.Page("pages/portefeuille.py",    title="Diagnostic expérimental",    icon="🧪"),
        st.Page("pages/analyse_actions.py", title="Analyse d'Actions",   icon="🔍"),
        st.Page("pages/secteurs.py",        title="Carte des Secteurs",  icon="🗺️"),
        st.Page("pages/methodologie.py",    title="Méthodologie",        icon="📐"),
    ]},
    position="sidebar",
)

navigation.run()
