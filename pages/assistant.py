"""Fact-based session overview. No generated advice or background agent."""
from datetime import date
import streamlit as st
from core.journey import journey_progress, next_step

st.title('Mon assistant')
st.write('Retrouvez votre projet, vos essais et vos positions. Faites le point à votre rythme et gardez une trace de vos décisions.')
st.caption('Cet espace utilise vos saisies enregistrées. Les cours, les actualités et les comptes courtiers ne sont pas connectés.')

project = st.session_state.get('project')
allocation = st.session_state.get('allocation_draft', {})
snapshot = st.session_state.get('real_snapshot')
step = next_step(project, allocation, snapshot)
progress = journey_progress(project, allocation, snapshot)

st.subheader('Votre parcours')
st.progress(progress.completed / 3, text=f'{progress.completed} étape(s) sur 3 enregistrée(s) dans cette session')
for column, label, complete, page, action in zip(
    st.columns(3),
    ('1. Définir mon projet', '2. Tester une répartition', '3. Suivre mon portefeuille'),
    (progress.project, progress.allocation, progress.portfolio),
    ('pages/commencer.py', 'pages/modeles.py', 'pages/positions_reelles.py'),
    ('Commencer', 'Explorer', 'Renseigner'),
):
    with column:
        st.markdown(f"**{'✓' if complete else '○'} {label}**")
        st.caption('Étape enregistrée' if complete else 'À faire quand vous êtes prêt')
        st.page_link(page, label='Revoir' if complete else action)

st.caption('À faire ensuite')
st.subheader(step.title)
st.write(step.description)
st.page_link(step.page, label=step.action)
st.caption('Pour retrouver votre travail à la prochaine visite, conservez-le dans Mon dossier.')
st.divider()
left, right = st.columns(2)
with left:
    st.subheader('Préparer mes investissements')
    if project:
        st.write(project.goal)
        st.write(f'Horizon : {project.years} ans · Versement prévu : {project.monthly:,.0f} €/mois')
    else:
        st.info('Définissez votre objectif, votre horizon et votre capacité d’épargne pour commencer.')
    st.page_link('pages/commencer.py', label='Construire ou revoir mon projet', icon='🌱')
    st.write(f'{len(allocation)} supports dans votre allocation fictive enregistrée.' if allocation else 'Aucune allocation fictive enregistrée.')
    st.page_link('pages/modeles.py', label='Explorer les portefeuilles fictifs', icon='⚖️')
    if allocation:
        st.page_link('pages/allocation.py', label='Retrouver ma répartition enregistrée')
with right:
    st.subheader('Suivre mon portefeuille')
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
st.page_link('pages/dossier.py', label='Ouvrir Mon dossier')
st.caption('Téléchargez votre dossier ou reprenez un fichier existant depuis cet espace. La sauvegarde n’est pas automatique.')
