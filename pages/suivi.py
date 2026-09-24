"""Explicitly confirmed, cash-flow-adjusted analysis of manual valuations."""
from datetime import date
import hashlib
import json
from uuid import uuid4
import pandas as pd
import streamlit as st
from core.tracking import session_valuations, validate_tracking, period_result, SOURCE

st.title('Suivre mon évolution')
st.write('Distinguez ce que vous avez ajouté à votre portefeuille de ce qu’il a gagné ou perdu. Les calculs reposent sur vos déclarations en euros.')
valuations = sorted(session_valuations(st.session_state), key=lambda row: row['date'])
flows = st.session_state.get('external_flows', [])
st.subheader('1. Mes valorisations enregistrées')
st.caption('Chaque état enregistré dans « Mon portefeuille réel » conserve une valeur totale datée, liquidités comprises. Seule la composition du dernier état saisi est conservée. Aucune valeur intermédiaire n’est reconstituée.')
if valuations:
    table = pd.DataFrame(valuations).rename(columns={'date': 'Date', 'total': 'Valeur totale déclarée (€)'})
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.download_button('Exporter mes valorisations (CSV)', table.to_csv(index=False).encode('utf-8-sig'), 'valorisations.csv', 'text/csv')
else:
    st.info('Enregistrez votre premier état dans « Mon portefeuille réel » pour démarrer le suivi.')

st.subheader('2. Mes apports et retraits')
st.write('Saisissez uniquement l’argent qui entre dans l’ensemble des comptes suivis ou en sort. Un transfert entre deux comptes déjà suivis ne change pas cet ensemble.')
with st.expander('Quels mouvements renseigner ?'):
    st.write('Un virement depuis votre compte courant vers un compte suivi est un apport. Le mouvement inverse est un retrait. Les achats/ventes de titres et les dividendes conservés sur un compte suivi ne sont pas des apports/retraits. Les frais prélevés sur ces comptes restent inclus dans le résultat ; ne les classez pas comme retraits.')
    st.write('Cette version ne traite que les mouvements en espèces. Pour des transferts de titres, des changements de comptes inclus, du levier ou des opérations difficiles à rapprocher, ne confirmez pas la complétude : ce calcul ne convient pas encore.')
with st.form('tracking_flow_form', clear_on_submit=True):
    when = st.date_input('Date du mouvement', date.today(), max_value=date.today())
    kind = st.radio('Nature du mouvement', ['Apport', 'Retrait'], horizontal=True)
    amount = st.number_input('Montant (€)', min_value=0.0, max_value=100_000_000.0, value=0.0, step=100.0)
    note = st.text_input('Libellé facultatif', max_chars=200)
    if st.form_submit_button('Enregistrer le mouvement'):
        candidate = flows + [{'id': uuid4().hex, 'date': when.isoformat(), 'amount': amount if kind == 'Apport' else -amount, 'note': note.strip()}]
        try:
            validate_tracking(valuations, candidate)
            st.session_state.external_flows = candidate
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
if flows:
    display = pd.DataFrame(sorted(flows, key=lambda f: f['date']))
    st.dataframe(display[['date', 'amount', 'note']].rename(columns={'date': 'Date', 'amount': 'Apport (+) / retrait (−) en €', 'note': 'Libellé'}), hide_index=True)
    st.download_button('Exporter mes mouvements (CSV)', display.to_csv(index=False).encode('utf-8-sig'), 'mouvements.csv', 'text/csv')
    with st.expander('Corriger une erreur de saisie'):
        st.caption('Supprimez la ligne erronée puis saisissez le mouvement corrigé. Deux virements distincts peuvent avoir la même date et le même montant : vérifiez les doublons avec votre relevé.')
        choices = {f['id']: f for f in flows}
        selected = st.selectbox('Mouvement à supprimer', list(choices), format_func=lambda k: f"{choices[k]['date']} · {choices[k]['amount']:,.2f} € · {choices[k]['note']} · {k[:6]}")
        if st.button('Supprimer ce mouvement'):
            st.session_state.external_flows = [f for f in flows if f['id'] != selected]
            st.rerun()
else:
    st.caption('Aucun mouvement renseigné. Cela ne prouve pas qu’il n’y en a eu aucun.')

st.subheader('3. Comprendre le résultat sur une période')
if len(valuations) < 2:
    st.info('Il faut au moins deux valorisations à des dates différentes pour comparer une période.')
else:
    by_date = {v['date']: v for v in valuations}
    dates = list(by_date)
    start = st.selectbox('Début — valeur de fin de journée', dates[:-1], key='tracking_start')
    ends = [d for d in dates if d > start]
    end = st.selectbox('Fin — valeur de fin de journée', ends, index=len(ends) - 1, key='tracking_end')
    included = [f for f in flows if start < f['date'] <= end]
    st.write(f'{len(included)} mouvement(s) renseigné(s) après le {start} et jusqu’au {end} inclus. Les mouvements du jour de départ sont déjà inclus dans la valeur initiale.')
    fingerprint = hashlib.sha256(json.dumps([by_date[start], by_date[end], included], sort_keys=True).encode()).hexdigest()[:16]
    complete = st.checkbox('Je confirme : mêmes comptes suivis aux deux dates, toutes les positions et liquidités incluses, et tous les apports/retraits en espèces de la période renseignés (ou aucun s’il n’y en a pas eu). Aucun transfert de titres ni levier.', key=f'tracking_complete_{fingerprint}')
    if complete:
        result = period_result(by_date[start], by_date[end], flows, complete=True)
        a, b, c = st.columns(3)
        a.metric('Apports nets des retraits', f"{result['net_external_flows']:,.2f} €".replace(',', ' '))
        b.metric('Gain / perte hors apports et retraits', f"{result['gain_loss_eur']:,.2f} €".replace(',', ' '))
        c.metric('Performance estimée sur la période', 'Indisponible' if result['estimated_return'] is None else f"{result['estimated_return']:.2%}")
        if result['unavailable_reason']:
            st.warning(result['unavailable_reason'])
        st.warning('Le pourcentage est une estimation par Dietz modifié, non annualisée. Des apports/retraits importants et des marchés volatils peuvent la rendre imprécise. Les données restent déclaratives.')
        with st.expander('Comprendre et vérifier le calcul'):
            st.write('Gain/perte = valeur finale − valeur initiale − apports nets. Le pourcentage rapporte ce résultat à la valeur initiale augmentée des flux pondérés par leur durée de présence. Convention : mouvements en fin de journée.')
            st.write(f"Durée : {result['days']} jours calendaires · Capital pondéré : {result['weighted_capital']:,.2f} €.")
            if result['flows']:
                st.dataframe(pd.DataFrame(result['flows'])[['date', 'amount', 'weight']], hide_index=True)
            st.caption('Frais et fiscalité reflétés seulement dans les valeurs saisies. Aucun ajustement ajouté, aucune conformité GIPS revendiquée.')
            st.markdown(f'[Méthode : CFA Institute, GIPS Standards Handbook for Firms — section 2]({SOURCE})')
        st.download_button('Exporter ce calcul et ses données (JSON)', json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), 'suivi-periode.json', 'application/json')
    else:
        st.info('Le gain et la performance restent masqués tant que vous n’avez pas confirmé la complétude des données de cette période.')
st.caption('Pour conserver valorisations et mouvements après cette session, téléchargez votre dossier depuis « Mon assistant ».')
