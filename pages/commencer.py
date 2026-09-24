"""Beginner entry point, independent of legacy market-data calculations."""
import pandas as pd
import streamlit as st
from core.planning import Project, export_project, import_project, project_path

st.title("Construire mon projet")
st.write("Avancez à votre rythme : posez votre objectif, comprenez les chiffres et explorez vos possibilités.")
st.caption("Première étape : votre projet et des scénarios de capital. Retrouvez ensuite le catalogue, les allocations fictives et les historiques dans le menu.")

with st.expander("Reprendre un projet enregistré"):
    upload = st.file_uploader("Votre fichier projet (.json)", type="json")
    if st.button("Charger le projet", disabled=upload is None):
        try:
            st.session_state.project = import_project(upload.getvalue())
            st.success("Projet chargé. Vous pouvez modifier les champs ci-dessous.")
        except ValueError as exc:
            st.error(str(exc))

p = st.session_state.get("project", Project())
st.subheader("1. Votre point de départ")
with st.form("project_form"):
    goal = st.text_input("Pour quel projet souhaitez-vous investir ?", value=p.goal, max_chars=200)
    left, right = st.columns(2)
    initial = left.number_input("Capital de départ (€)", 0.0, 100_000_000.0, float(p.initial), step=100.0)
    monthly = right.number_input("Versement mensuel envisagé (€)", 0.0, 1_000_000.0, float(p.monthly), step=50.0)
    years = st.slider("Dans combien d’années aurez-vous besoin de cet argent ?", 1, 50, p.years)
    reserves = ["À constituer", "Déjà disponible", "Je ne sais pas encore"]
    reserve = st.selectbox("Avez-vous une épargne disponible pour les imprévus ?", reserves,
                           index=reserves.index(p.reserve) if p.reserve in reserves else 2)
    experiences = ["Je débute", "J’ai déjà investi"]
    experience = st.radio("Votre expérience", experiences, index=experiences.index(p.experience) if p.experience in experiences else 0)
    reactions = ["Je ne sais pas encore", "J’aurais besoin de récupérer cet argent", "Je pourrais attendre malgré la baisse"]
    reaction = st.selectbox("Si 10 000 € devenaient 7 000 €, comment réagiriez-vous ?", reactions,
                            index=reactions.index(p.loss_reaction) if p.loss_reaction in reactions else 0)
    submitted = st.form_submit_button("Enregistrer mon projet", type="primary")
if submitted:
    try:
        p = Project(goal, initial, monthly, years, reserve, experience, reaction)
        st.session_state.project = p
        st.success("Projet enregistré pour cette session.")
    except ValueError as exc:
        st.error(str(exc))

if p.reserve != "Déjà disponible":
    st.info("L’épargne de précaution sert à payer les imprévus sans vendre vos investissements. Séparez-la du capital que vous souhaitez investir.")
if p.years <= 3 or p.loss_reaction == "J’aurais besoin de récupérer cet argent":
    st.info("La disponibilité de votre argent compte : une baisse peut durer au-delà de votre échéance. Une projection de rendement ne garantit pas de retrouver votre capital.")
st.caption("Ces réponses décrivent votre projet ; elles ne déterminent pas encore une allocation ni un profil de risque complet.")

st.subheader("2. Comprendre l’effet du temps et des versements")
st.write("Choisissez une hypothèse pour observer son effet. Aucun rendement n’est déduit de votre profil.")
a, b, c = st.columns(3)
rate = a.number_input("Rendement annuel hypothétique (%)", -50.0, 30.0, 0.0, step=0.5)
fee = b.number_input("Frais annuels simulés (%)", 0.0, 10.0, 0.0, step=0.1)
inflation = c.number_input("Inflation annuelle supposée (%)", 0.0, 20.0, 0.0, step=0.5)
rows = project_path(p, rate / 100, fee / 100, inflation / 100)
end = rows[-1]
a, b, c = st.columns(3)
money = lambda v: f"{v:,.0f} €".replace(",", " ")
a.metric("Votre argent versé", money(end["Versements cumulés"]))
b.metric("Capital simulé à l’échéance", money(end["Capital simulé"]))
c.metric("Gain / perte simulé(e)", money(end["Gain / perte simulé(e)"]))
st.line_chart(pd.DataFrame(rows).set_index("Mois")[["Versements cumulés", "Capital simulé"]])
st.caption(f"Projet enregistré : {p.years} ans, {money(p.initial)} au départ et {money(p.monthly)} par mois. Modifiez puis enregistrez le formulaire pour le mettre à jour.")
st.write(f"Pouvoir d’achat final avec votre hypothèse d’inflation : **{money(end['Capital en euros d’aujourd’hui'])}** en euros d’aujourd’hui.")
with st.expander("Comprendre les hypothèses et les limites"):
    st.write("Projection mathématique à rendement constant : ce n’est ni un backtest historique ni une prévision. Les marchés peuvent subir des pertes importantes et ne progressent pas régulièrement.")
    st.write("Versements constants en fin de mois ; taux annuel effectif converti en taux mensuel. Facteur annuel net = (1 + rendement) × (1 − frais). Fiscalité, courtage et variation des rendements exclus. L’inflation réduit le pouvoir d’achat, pas le solde nominal.")
    st.write("Le fichier projet conserve vos réponses. Les hypothèses de rendement, frais et inflation restent propres à l’écran et ne sont pas enregistrées dans ce fichier.")

st.subheader("3. Les mots utiles pour la suite")
with st.expander("Un compte, un support, une allocation : quelle différence ?"):
    st.write("L’enveloppe est le compte qui accueille vos investissements. Le support est ce que vous détenez, par exemple une action ou une part de fonds. L’allocation est la répartition de votre argent entre ces investissements.")
    st.write("Un ETF est un fonds coté en bourse. Une action représente une part d’une entreprise. Une obligation est un titre de dette. Aucun de ces mots ne suffit à déterminer le niveau de risque : il dépend de ce que vous achetez.")

st.download_button("Télécharger mon projet", export_project(p), "mon-projet.json", "application/json")
st.caption("Votre projet reste dans cette session. Téléchargez-le pour le retrouver après fermeture ou rechargement de l’application.")
