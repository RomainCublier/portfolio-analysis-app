"""Short portfolio review using declared data only."""
from datetime import date

import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError

from core.review import review_summary
from core.tracking import session_valuations


def page_link(page, label):
    try:
        st.page_link(page, label=label)
    except StreamlitPageNotFoundError:
        st.caption(label)


def euros(value):
    return f'{value:,.2f} €'.replace(',', ' ')


st.title('Faire le point')
st.write('Retrouvez vos chiffres, vérifiez ce qui a changé et gardez une trace de votre réflexion.')
summary = review_summary(session_valuations(st.session_state), st.session_state.get('external_flows', []))
latest = summary['latest']
if latest is None:
    st.info('Votre premier bilan commence avec la valeur de vos investissements et de vos liquidités.')
    page_link('pages/positions_reelles.py', 'Renseigner mon portefeuille')
    page_link('pages/commencer.py', 'Je prépare encore mon premier investissement')
    st.stop()

first, second = st.columns(2)
first.metric('Dernière valeur déclarée', euros(latest['total']))
second.metric('Ancienneté du relevé', f"{summary['age_days']} jour(s)")
st.caption(f"Relevé du {date.fromisoformat(latest['date']):%d/%m/%Y}. Les valeurs ne se mettent pas à jour automatiquement.")

st.subheader('1. Mes chiffres sont-ils à jour ?')
if summary['pending_count']:
    st.info(f"{summary['pending_count']} mouvement(s) saisi(s) après ce relevé. Ils ne sont pas couverts par la dernière valeur déclarée.")
page_link('pages/positions_reelles.py', 'Actualiser la valeur de mon portefeuille')

st.subheader('2. Ai-je renseigné mes apports et retraits ?')
previous = summary['previous']
if previous:
    st.write(f"Entre les relevés du {date.fromisoformat(previous['date']):%d/%m/%Y} et du {date.fromisoformat(latest['date']):%d/%m/%Y} : {summary['movement_count']} mouvement(s) saisi(s), soit {euros(summary['declared_net_flows'])} d’apports nets des retraits.")
    st.caption('Ce total porte uniquement sur les mouvements renseignés. Il ne confirme pas que la liste est complète et ne mesure pas votre performance.')
else:
    st.write('Vous avez un premier relevé. Un second, à une autre date, permettra de comparer une période.')
page_link('pages/suivi.py', 'Vérifier mes mouvements et comprendre mon résultat')

st.subheader('3. Mon projet a-t-il changé ?')
project = st.session_state.get('project')
if project:
    st.write(f'{project.goal} · Horizon : {project.years} ans · Épargne prévue : {euros(project.monthly)}/mois')
st.write('Un nouveau projet, un besoin de liquidités ou un changement de revenus mérite de revoir les informations renseignées.')
page_link('pages/commencer.py', 'Revoir mon projet')

st.subheader('Mon bilan')
with st.form('review_note', clear_on_submit=True):
    note = st.text_area('Ce que je retiens', max_chars=1800,
                        placeholder='Mes chiffres sont-ils complets ? Quelles questions me restent ? Mon projet a-t-il changé ?')
    if st.form_submit_button('Conserver mon bilan'):
        journal = st.session_state.get('decision_journal', [])
        if not note.strip():
            st.error('Ajoutez une note pour conserver votre bilan.')
        elif len(journal) >= 500:
            st.error('Votre journal a atteint sa limite de 500 notes.')
        else:
            st.session_state.decision_journal = journal + [{
                'date': date.today().isoformat(),
                'note': f"Bilan du portefeuille — relevé du {latest['date']}\n{note.strip()}",
            }]
            st.success('Bilan ajouté au journal de cette session. Enregistrez ou téléchargez votre dossier pour le retrouver.')
page_link('pages/dossier.py', 'Conserver mon dossier')
page_link('pages/assistant.py', 'Retrouver mon journal')
