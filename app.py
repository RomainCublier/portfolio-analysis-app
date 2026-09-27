import sqlite3

import streamlit as st
from cryptography.fernet import InvalidToken
from streamlit.errors import StreamlitSecretNotFoundError

from config.consumer_ui import CSS
from core.access import BillingConfig, access_status
from core.billing import BillingError
from core.catalog import load_catalog
from core.release import ReleaseSettings, laboratory_enabled, readiness

st.set_page_config(
    page_title="QuantDesk | Mon assistant investisseur",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

settings = ReleaseSettings.from_environ()
try:
    billing = BillingConfig.from_mapping(dict(st.secrets.get("billing", {})))
except (StreamlitSecretNotFoundError, BillingError):
    billing = BillingConfig()
release_blockers = readiness(settings, load_catalog(), billing.enabled) if settings.production else []

paid_access = True
if billing.enabled:
    paid_access = False
    if st.user.is_logged_in:
        try:
            _, _, paid_access = access_status(billing, dict(st.user), st.session_state)
        except (BillingError, InvalidToken, OSError, sqlite3.Error):
            paid_access = False

full_pages = {"Mon espace": [
        st.Page("pages/assistant.py", title="Mon assistant", icon="🧭", default=True),
        st.Page("pages/dossier.py", title="Mon dossier"),
        st.Page("pages/offre.py", title="Mon abonnement"),
        st.Page("pages/informations.py", title="Informations et limites"),
    ], "Préparer mes investissements": [
        st.Page("pages/commencer.py", title="Construire mon projet", icon="🌱"),
        st.Page("pages/enveloppes.py", title="Comprendre PEA et CTO"),
        st.Page("pages/modeles.py", title="Mon portefeuille fictif"),
    ], "Suivre mon portefeuille": [
        st.Page("pages/revue.py", title="Faire le point"),
        st.Page("pages/positions_reelles.py", title="Mon portefeuille réel", icon="📊"),
        st.Page("pages/suivi.py", title="Suivre mon évolution", icon="🗓️"),
    ], "Pour approfondir": [
        st.Page("pages/catalogue.py", title="Explorer les supports", icon="🔎"),
        st.Page("pages/allocation.py", title="Personnaliser ma répartition", icon="⚖️"),
    ]}

if billing.enabled and not paid_access:
    pages = {"Découvrir": [
        st.Page("pages/accueil.py", title="Accueil", icon="◈", default=True),
        st.Page("pages/commencer.py", title="Construire mon projet", icon="🌱"),
        st.Page("pages/enveloppes.py", title="Comprendre PEA et CTO"),
        st.Page("pages/offre.py", title="Accès complet"),
        st.Page("pages/informations.py", title="Informations et limites"),
    ]}
else:
    pages = full_pages
if laboratory_enabled():
    show_lab = st.sidebar.checkbox("Afficher le laboratoire interne", value=False)
else:
    show_lab = False
if show_lab:
    pages["Laboratoire — fonctions expérimentales"] = [
        st.Page("pages/profil.py", title="Cadre de profil expérimental", icon="🧩"),
        st.Page("pages/backtest.py", title="Import historique", icon="📈"),
        st.Page("pages/portefeuille.py",    title="Diagnostic expérimental",    icon="🧪"),
        st.Page("pages/analyse_actions.py", title="Analyse d'Actions",   icon="🔍"),
        st.Page("pages/secteurs.py",        title="Carte des Secteurs",  icon="🗺️"),
        st.Page("pages/methodologie.py",    title="Méthodologie",        icon="📐"),
    ]

if release_blockers:
    pages = {"Ouverture bloquée": [
        st.Page("pages/informations.py", title="Configuration incomplète", default=True),
    ]}

navigation = st.navigation(
    pages,
    position="sidebar",
)

navigation.run()
