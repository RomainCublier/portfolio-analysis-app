"""Plain-language PEA/CTO comparison based on current official references."""
import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError


AMF_PEA = "https://www.amf-france.org/fr/espace-epargnants/comprendre-les-produits-financiers/supports-dinvestissement/pea-tout-savoir-sur-le-plan-depargne-en-actions"
AMF_CTO = "https://www.amf-france.org/fr/espace-epargnants/comprendre-les-produits-financiers/supports-dinvestissement/compte-titres"
SERVICE_PUBLIC_PEA = "https://www.service-public.fr/particuliers/vosdroits/F2385"

st.title("Comprendre le PEA et le CTO")
st.write(
    "L’enveloppe est le compte qui accueille vos investissements. Elle détermine les "
    "supports accessibles, les règles de retrait et la fiscalité ; elle ne détermine "
    "pas à elle seule le risque de votre portefeuille."
)
st.caption("Informations générales vérifiées le 27 septembre 2026. Votre situation fiscale personnelle n’est pas analysée.")

st.subheader("Les différences essentielles")
st.dataframe(pd.DataFrame([
    {
        "Question": "Quels supports ?",
        "PEA": "Actions européennes et certains fonds ou ETF éligibles",
        "CTO": "Univers plus large : actions, obligations, ETF et fonds selon le courtier",
    },
    {
        "Question": "Versements",
        "PEA": "Plafond réglementaire de versements ; gains non comptés dans le plafond",
        "CTO": "Pas de plafond réglementaire général de versements",
    },
    {
        "Question": "Retraits",
        "PEA": "Règles particulières, notamment avant cinq ans ; exceptions possibles",
        "CTO": "Retraits possibles sans règle d’ancienneté propre au CTO",
    },
    {
        "Question": "Fiscalité",
        "PEA": "Régime dépendant notamment de la durée du plan et des retraits",
        "CTO": "Revenus et plus-values imposés selon les règles en vigueur et votre situation",
    },
]), hide_index=True, width="stretch")

st.info(
    "Le PEA et le CTO peuvent coexister. Avant un achat, vérifiez toujours "
    "l’éligibilité exacte du support, les frais de l’intermédiaire et le document officiel du produit."
)

st.subheader("Trois points à retenir")
st.markdown(
    """
1. Un ETF coté en euros n’est pas automatiquement éligible au PEA.
2. L’avantage fiscal du PEA ne protège pas contre une baisse des marchés.
3. Le CTO donne accès à davantage de supports, mais cette liberté ne garantit pas une meilleure diversification.
"""
)

with st.expander("Consulter les références officielles"):
    st.link_button("AMF — comprendre le PEA", AMF_PEA)
    st.link_button("Service-Public — règles du PEA", SERVICE_PUBLIC_PEA)
    st.link_button("AMF — comprendre le compte-titres", AMF_CTO)
    st.caption(
        "Les règles peuvent évoluer. Les liens officiels priment sur ce résumé, notamment "
        "pour les plafonds, les cas de retrait anticipé et la fiscalité."
    )

try:
    st.page_link("pages/modeles.py", label="Continuer : explorer les portefeuilles fictifs")
except StreamlitPageNotFoundError:
    st.caption("Suite : Mon portefeuille fictif, dans le menu.")
