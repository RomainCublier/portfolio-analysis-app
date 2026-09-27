"""Historical comparison embedded in the central portfolio page."""
import streamlit as st
from datetime import date
from core.issuer_fetch import fetch_europe_bonds, fetch_world_bonds, fetch_wpea_bonds
from core.wpea_import import ISIN as WPEA_ISIN
from core.ishares_import import ISIN, BOND_ISIN, WORLD_ISIN

from core.history_import import import_history
from core.model_history import coverage, compare_models, comparison_key, comparison_summary


def render_history(stock, bond, catalog, project, model):
    st.subheader('Comparer sur une période passée')
    if stock in (ISIN, WORLD_ISIN, WPEA_ISIN) and bond == BOND_ISIN:
        st.write('Récupération directe disponible pour les deux supports choisis.')
        st.caption('Usage de recherche ; droits commerciaux non validés. La période initiale proposée sert à vérifier la connexion, sans représenter les marchés en général.')
        if stock == WPEA_ISIN:
            st.info('WPEA existe depuis 2024. Son export contient des rendements manquants. La période courte proposée est choisie pour sa complétude, pas pour sa performance ; elle ne permet pas de juger une stratégie à long terme.')
        with st.form('issuer_history_period_' + stock):
            a, b = st.columns(2)
            start = a.date_input('Début de la période historique', date(2024, 8, 9) if stock == WPEA_ISIN else date(2021, 12, 31), max_value=date.today(), key='issuer_start_' + stock)
            end = b.date_input('Fin de la période historique', date(2024, 12, 31) if stock == WPEA_ISIN else date(2022, 12, 30), max_value=date.today(), key='issuer_end_' + stock)
            submitted = st.form_submit_button('Récupérer les historiques officiels')
        if submitted:
            try:
                with st.spinner('Récupération et vérification des deux historiques…'):
                    fetch = {WORLD_ISIN: fetch_world_bonds, WPEA_ISIN: fetch_wpea_bonds, ISIN: fetch_europe_bonds}[stock]
                    dataset = fetch(start, end)
                st.session_state['research_history'] = dataset
                st.success('Les deux historiques ont passé les contrôles techniques.')
            except ValueError as exc:
                st.session_state.pop('research_history', None)
                st.error(str(exc))
        st.caption('Les dates choisies doivent exister dans les deux exports. Les lacunes bloquent le calcul ; aucune date n’est déplacée automatiquement.')
    with st.expander('Ajouter un historique documenté'):
        st.caption('Import de recherche : CSV de rendement total net en euros et manifeste de provenance. Les droits commerciaux ne sont pas validés par cet import.')
        csv = st.file_uploader('Historique des supports (CSV)', type='csv', key='model_history_csv')
        manifest = st.file_uploader('Sources et calendrier (JSON)', type='json', key='model_history_manifest')
        if st.button('Vérifier et utiliser ces données', disabled=csv is None or manifest is None):
            try:
                dataset = import_history(csv.getvalue(), manifest.getvalue())
                st.session_state['research_history'] = dataset
                st.success('Historique chargé pour cette session.')
            except ValueError as exc:
                # A rejected replacement must not leave old results visible.
                st.session_state.pop('research_history', None)
                st.error(f'Import refusé : {exc}')
    dataset = st.session_state.get('research_history')
    if not stock or not bond:
        st.session_state.pop('model_comparison', None)
        st.info('Choisissez les deux supports pour vérifier la disponibilité de leur historique.')
        return
    missing, report = coverage({stock: 1, bond: 1}, dataset)
    names = {row['isin']: row['name'] for row in catalog}
    if missing:
        st.session_state.pop('model_comparison', None)
        st.info('Historique à connecter : ' + ' ; '.join(names[key] for key in missing))
        st.caption('Aucune performance passée n’est calculée tant que les deux supports ne sont pas couverts.')
        return
    st.caption(f"Période importée : {report['start']} au {report['end']} · {report['observations']} observations · EUR. Votre horizon de projet n’allonge pas cet historique.")
    direct = dataset[3].get('retrieval') == 'direct_issuer_download'
    st.warning(('Exports récupérés directement chez l’émetteur. ' if direct else 'Sources déclarées par l’import. ') + 'Comparaison de recherche : calendrier non vérifié indépendamment et droits commerciaux non validés. Le passé ne prédit pas les performances futures.')
    with st.expander('Sources et règles de calcul'):
        for key in (stock, bond):
            meta = dataset[1][key]
            st.write(names[key])
            st.link_button('Source ' + key, meta.source_url)
            st.caption(f'Récupéré le {meta.retrieved_at} · Origine : {meta.origin}')
        st.write('Capital de départ et versements du projet appliqués au passé. Versement au dernier point de chaque mois après le mois initial, y compris le dernier mois incomplet. Répartition des nouveaux apports selon les poids de départ, sans vente ni rééquilibrage. Parts fractionnaires ; frais des fonds inclus dans les séries ; courtage, spread et fiscalité exclus.')
    key = comparison_key(dataset, stock, bond, project)
    saved = st.session_state.get('model_comparison')
    if saved and saved['key'] != key:
        st.session_state.pop('model_comparison', None)
        saved = None
        st.info('Votre projet, vos supports ou vos données ont changé. Relancez la comparaison pour obtenir un résultat à jour.')
    if st.button('Comparer les trois répartitions sur cet historique'):
        try:
            table, curves, flows = compare_models(dataset, stock, bond, catalog, project)
            saved = {'key': key, 'table': table, 'curves': curves, 'flows': flows}
            st.session_state['model_comparison'] = saved
        except ValueError as exc:
            st.session_state.pop('model_comparison', None)
            saved = None
            st.error(str(exc))
    if saved:
        summary = comparison_summary(saved['table'], saved['curves'], saved['flows'], project, model)
        st.subheader(f'Votre essai {model} sur cette période')
        a, b, c = st.columns(3)
        money = lambda value: f'{value:,.2f} €'.replace(',', ' ')
        a.metric('Votre argent versé', money(summary['paid']))
        b.metric('Valeur finale simulée', money(summary['final']))
        c.metric('Gain / perte simulé(e)', money(summary['gain']))
        st.write(f"Sur les {summary['days']} jours de cet historique, vos versements auraient totalisé {money(summary['paid'])}, pour une valeur finale simulée de {money(summary['final'])}.")
        if summary['shorter_than_project']:
            st.info(f"Cette période est plus courte que votre projet de {project.years} ans. Le résultat n’est pas extrapolé à votre horizon.")
        st.line_chart(summary['chart'], y_label='Euros')
        with st.expander('Comparer les trois répartitions en détail'):
            st.line_chart(saved['curves'], y_label='Valeur simulée (€)')
            st.dataframe(saved['table'], hide_index=True, width='stretch')
        st.caption('La performance neutralise les apports (TWR). La baisse maximale est mesurée entre les observations et peut sous-estimer les pertes intermédiaires. Aucune répartition n’est désignée gagnante ou recommandée.')
        with st.expander('Vérifier les dates des versements'):
            st.dataframe(saved['flows'].rename('Versement (€)'))
        st.download_button('Télécharger la comparaison', saved['table'].to_csv(index=False).encode('utf-8-sig'), 'comparaison-historique.csv', 'text/csv')
        st.caption('Résultat conservé pendant cette session. Les historiques et ce calcul ne sont pas inclus dans la sauvegarde du dossier.')
