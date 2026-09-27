"""Public landing page used before authentication or subscription."""
import streamlit as st


st.title("Construire un plan d’investissement compréhensible")
st.write(
    "Définissez votre projet, comprenez le PEA et le CTO, puis comparez des "
    "portefeuilles fictifs et suivez vos propres décisions."
)
st.info(
    "QuantDesk est un outil pédagogique : aucun ordre n’est transmis et aucun "
    "rendement n’est garanti."
)

first, second, third = st.columns(3)
first.subheader("1. Votre projet")
first.write("Capital, versements, horizon et disponibilité de votre épargne.")
second.subheader("2. Vos possibilités")
second.write("Enveloppes, répartitions fictives et supports documentés.")
third.subheader("3. Votre suivi")
third.write("Positions déclarées, apports, évolution et revue périodique.")

st.page_link("pages/commencer.py", label="Commencer gratuitement", icon="🌱")
st.page_link("pages/offre.py", label="Découvrir l’accès complet")
st.page_link("pages/informations.py", label="Lire les informations et limites")
