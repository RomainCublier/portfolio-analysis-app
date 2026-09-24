"""Fact-based session overview. No generated advice or background agent."""
from datetime import date
import streamlit as st
from core.dossier import export_dossier, import_dossier, restore_dossier

st.title('Mon assistant')
st.write('Retrouvez votre projet, vos essais et vos positions. Faites le point à votre rythme et gardez une trace de vos décisions.')
st.caption('Cet espace utilise vos saisies enregistrées. Les cours, les actualités et les comptes courtiers ne sont pas connectés.')

project = st.session_state.get('project')
allocation = st.session_state.get('allocation_draft', {})
snapshot = st.session_state.get('real_snapshot')
left, right = st.columns(2)
with left:
    st.subheader('Mon projet et mes essais')
    if project:
        st.write(project.goal)
        st.write(f'Horizon : {project.years} ans · Versement prévu : {project.monthly:,.0f} €/mois')
    else:
        st.info('Définissez votre objectif, votre horizon et votre capacité d’épargne pour commencer.')
    st.page_link('pages/commencer.py', label='Construire ou revoir mon projet', icon='🌱')
    st.write(f'{len(allocation)} supports dans votre allocation fictive enregistrée.' if allocation else 'Aucune allocation fictive enregistrée.')
    st.page_link('pages/allocation.py', label='Reprendre mon allocation fictive', icon='⚖️')
    st.page_link('pages/backtest.py', label='Explorer un historique et des versements', icon='📈')
with right:
    st.subheader('Mes positions déclarées')
    if snapshot is not None:
        positions, cash, valued_at = snapshot
        total = positions['Valeur actuelle (€)'].sum() + cash
        st.metric('Valeur totale déclarée', f'{total:,.2f} €'.replace(',', ' '))
        st.write(f'Valorisations au {valued_at:%d/%m/%Y} · {(date.today() - valued_at).days} jour(s) écoulé(s).')
        st.caption('Cette valeur n’est pas une performance. Elle inclut vos liquidités et ne se met pas à jour automatiquement.')
    else:
        st.info('Vous détenez déjà des investissements ? Renseignez leurs valorisations et leur date.')
    st.page_link('pages/positions_reelles.py', label='Renseigner ou actualiser mes positions', icon='📊')
    st.page_link('pages/suivi.py', label='Suivre mes apports et mon évolution', icon='🗓️')

st.subheader('Mon journal de décisions')
st.write('Notez ce que vous avez vérifié, ce qui a changé dans votre situation ou les questions à approfondir. Une revue peut aussi se terminer sans opération.')
with st.form('journal_form', clear_on_submit=True):
    note = st.text_area('Ma note', max_chars=2000, placeholder='Quel était mon objectif ? Qu’ai-je observé ? Pourquoi ai-je décidé d’agir ou d’attendre ?')
    if st.form_submit_button('Enregistrer ma note'):
        journal = st.session_state.get('decision_journal', [])
        if not note.strip():
            st.error('Ajoutez une note avant d’enregistrer.')
        elif len(journal) >= 500:
            st.error('Le journal a atteint sa limite de 500 notes.')
        else:
            st.session_state.decision_journal = journal + [{'date': date.today().isoformat(), 'note': note.strip()}]
            st.success('Note enregistrée dans cette session. Exportez votre dossier pour la conserver.')
for entry in reversed(st.session_state.get('decision_journal', [])):
    with st.container(border=True):
        st.caption(entry['date'])
        st.text(entry['note'])

st.subheader('Conserver et reprendre mon dossier')
st.info('Il n’y a pas encore de compte utilisateur ni de sauvegarde automatique. Téléchargez votre dossier avant de quitter, puis importez-le à votre prochaine visite. Le fichier contient vos données personnelles en clair : conservez-le dans un endroit privé.')
try:
    st.download_button('Télécharger mon dossier', export_dossier(st.session_state), 'mon-dossier-investisseur.json', 'application/json')
except ValueError as exc:
    st.error(f'Export impossible : {exc}')
st.caption('Inclus : projet, dernière allocation fictive enregistrée, dernier état des positions, historique des valeurs totales, apports/retraits et journal. Les historiques importés, résultats de backtest et limites de concentration ne sont pas inclus.')
upload = st.file_uploader('Reprendre un dossier enregistré', type=['json'])
st.caption('Le chargement remplace le projet, l’allocation, les positions, l’historique de suivi et le journal de cette session.')
if st.button('Charger ce dossier', disabled=upload is None):
    try:
        restore_dossier(st.session_state, import_dossier(upload.getvalue()))
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))
