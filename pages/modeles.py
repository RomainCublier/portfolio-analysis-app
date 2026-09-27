"""A guided comparison of illustrative portfolios and documented instruments."""
import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError

from core.catalog import load_catalog, review_status
from core.models import MODELS, EQUITY_EXAMPLES, BOND_EXAMPLES, model_weights, hypothetical_change, keep_model
from core.model_history_ui import render_history
from core.models import saved_choices


def link(page, label):
    try:
        st.page_link(page, label=label)
    except StreamlitPageNotFoundError:
        st.caption(label)


st.title('Mon portefeuille fictif')
st.write('Comparez des répartitions, explorez des supports et gardez votre essai.')
project = st.session_state.get('project')
if project is None:
    st.info('Commencez par votre objectif, votre horizon et votre capacité d’épargne.')
    link('pages/commencer.py', 'Définir mon projet')
    st.stop()

st.write(f'**{project.goal}** · {project.years} ans · {project.initial:,.0f} € au départ · {project.monthly:,.0f} €/mois')
link('pages/commencer.py', 'Modifier mon projet')
st.caption('Les mêmes exemples sont proposés à tous. Votre projet sert ici à exprimer les montants ; aucune adéquation à votre situation n’est validée.')
if project.reserve != 'Déjà disponible' or project.years <= 3 or project.loss_reaction == 'J’aurais besoin de récupérer cet argent':
    st.warning('Votre disponibilité financière reste un point à clarifier avant d’investir. Ces exemples peuvent perdre de la valeur, y compris la partie obligataire.')

st.subheader('1. Comparer trois répartitions')
st.caption('Poids choisis pour illustrer des différences, sans optimisation ni rendement attendu. Actions et obligations peuvent baisser ensemble ; aucune garantie du capital.')
for column, (name, model) in zip(st.columns(3), MODELS.items()):
    with column:
        st.markdown(f'**{name}**')
        st.write(f"{model['equity']:.0%} actions · {1 - model['equity']:.0%} obligations")
        st.write(model['description'])
saved_model, saved_stock, saved_bond = saved_choices(st.session_state.get('allocation_draft', {}))
choice = st.radio('Quelle répartition voulez-vous explorer ?', list(MODELS), index=list(MODELS).index(saved_model) if saved_model else None, horizontal=True)
if choice is None:
    st.info('Choisissez une répartition pour voir sa composition et la tester.')
    st.stop()

equity = MODELS[choice]['equity']
st.dataframe(pd.DataFrame([
    {'Poche': label, 'Part (%)': weight * 100, 'Capital fictif (€)': project.initial * weight,
     'Versement fictif mensuel (€)': project.monthly * weight}
    for label, weight in [('Actions', equity), ('Obligations', 1 - equity)]
]), hide_index=True, width="stretch")
st.caption('Montants théoriques, sans prix de part, arrondis d’achat, courtage ni minimum de souscription. Ce ne sont pas des ordres à passer.')

st.subheader('2. Explorer des exemples de supports')
catalog = load_catalog()
by_isin = {row['isin']: row for row in catalog}
st.write('Une poche actions et une poche obligations. Ouvrez les fiches pour comprendre ce que chaque support contient.')
stocks = [key for key in EQUITY_EXAMPLES if key in by_isin]
bonds = [key for key in BOND_EXAMPLES if key in by_isin]
stock = st.selectbox('Exemple pour la poche actions', stocks,
                     index=stocks.index(saved_stock) if saved_stock in stocks else None, format_func=lambda key: by_isin[key]['name'])
bond = st.selectbox('Exemple pour la poche obligations', bonds,
                    index=bonds.index(saved_bond) if saved_bond in bonds else None, format_func=lambda key: by_isin[key]['name'])
for key in (stock, bond):
    if key:
        row = by_isin[key]
        with st.expander(row['name'], expanded=True):
            st.write(f"{row['instrument_kind']} · {row['category']}")
            st.caption(f"ISIN : {key} · Fiche consultée le {row['reviewed_on']} · {review_status(row)}")
            facts = row['facts']
            st.write(f"{facts['fee_label']} : {facts['fee_percent']} %" if facts['fee_percent'] is not None else 'Frais à documenter.')
            st.caption('Ce chiffre ne représente pas nécessairement tous les coûts. Vérifiez le DIC, le courtage et les éventuels frais d’entrée ou de performance.')
            pea = facts['pea']
            st.write('PEA : indiqué éligible dans la source.' if pea is True else 'PEA : indiqué non éligible.' if pea is False else 'PEA : éligibilité non vérifiée.')
            if row.get('review_note'):
                st.write(row['review_note'])
            st.link_button('Consulter la source du support', row['source_url'])
st.caption('Catalogue limité. Le fonds actif et les ETF actions ont des univers et des méthodes différents : ils ne sont pas équivalents. La disponibilité chez votre courtier reste à vérifier. L’ensemble du portefeuille n’est pas validé pour un PEA.')
if stock == 'IE00B4K48X80':
    st.info('La poche actions de cet exemple est limitée à l’Europe. Elle ne représente pas les marchés mondiaux.')
if stock == 'IE00B441G979':
    st.info('Cet ETF vise les marchés développés avec une couverture des devises vers l’euro. Cette couverture modifie les résultats et ne supprime pas tous les risques de change. Ce n’est pas l’historique d’un ETF Monde non couvert.')

st.subheader('3. Voir l’effet d’une variation')
st.write('Faites varier les deux poches pour observer l’effet sur votre capital de départ.')
a, b = st.columns(2)
action_shock = a.slider('Variation hypothétique des actions (%)', -100, 100, 0, step=5)
bond_shock = b.slider('Variation hypothétique des obligations (%)', -100, 100, 0, step=5)
change = hypothetical_change(choice, action_shock / 100, bond_shock / 100)
a, b = st.columns(2)
a.metric('Variation du portefeuille fictif', f'{change:.1%}')
b.metric('Capital après cette variation', f'{project.initial * (1 + change):,.0f} €')
st.caption('Choc instantané choisi par vous, appliqué aux poches : aucune probabilité, durée, donnée historique ou prévision. Versements, frais et fiscalité exclus. Aucun résultat propre aux supports sélectionnés n’est calculé.')
with st.expander('Projeter mon épargne dans le temps'):
    st.write('Le simulateur du projet utilise un rendement constant choisi par vous, indépendant des supports et du scénario ci-dessus.')
    link('pages/commencer.py', 'Explorer les effets du temps et des versements')

render_history(stock, bond, catalog, project, choice)

st.subheader('Conserver cet essai')
st.caption('Cela remplace votre allocation fictive enregistrée. Vos positions réelles restent distinctes.')
if st.button('Garder ce portefeuille fictif', type='primary', disabled=stock is None or bond is None):
    try:
        keep_model(st.session_state, model_weights(choice, stock, bond, catalog))
        st.success('Répartition conservée dans cette session. Enregistrez votre dossier pour la retrouver plus tard.')
    except ValueError as exc:
        st.error(str(exc))
link('pages/allocation.py', 'Retrouver ou ajuster ma répartition enregistrée')
link('pages/dossier.py', 'Sauvegarder mon dossier')
with st.expander('Méthode et données disponibles'):
    st.write('Exemples pédagogiques version 1 : 30/70, 60/40 et 90/10. Ils ne découlent pas d’un théorème et ne constituent pas un classement. Les compositions détaillées, corrélations, risques consolidés et recouvrements ne sont pas calculés.')
    st.markdown('[Comprendre allocation et diversification : Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)')
    st.write('Les droits de réutilisation commerciale des sources et la documentation destinée aux particuliers restent à valider avant commercialisation.')
