import json
from datetime import date
from pathlib import Path
import streamlit as st
from core.history_import import import_history
from core.history import buy_and_hold, path_metrics
from core.ishares_import import import_europe_export, import_multi_asset_exports, SOURCE_URL, BOND_SOURCE_URL

st.title("Explorer un historique")
st.write("Comparez une allocation initiale conservée sur une période passée, à partir de séries de rendement total net en euros.")
st.info("Version de recherche : aucun flux de marché n’est encore connecté. Les sources et les droits des fichiers importés restent à vérifier indépendamment.")
with st.expander("Préparer mes données"):
    st.write("Importez un CSV (date puis une colonne par identifiant) et son manifeste JSON : calendrier attendu, sources, dates de récupération, origine et empreinte SHA-256 du CSV. Les distributions doivent être réinvesties et les frais des fonds déjà inclus. Un cours brut seul ne convient pas.")
    example = Path(__file__).resolve().parents[1] / "data" / "examples"
    for name in ["synthetic_history.csv", "synthetic_manifest.json"]:
        st.download_button("Télécharger " + name, (example / name).read_bytes(), file_name=name)
    st.caption("Ces fichiers sont entièrement synthétiques : ils expliquent le format et ne décrivent aucun placement réel.")
mode = st.radio("Format de données", ["CSV et manifeste", "Export officiel iShares Europe", "Actions et obligations iShares"])
try:
    if mode == "CSV et manifeste":
        csv_file = st.file_uploader("Historique CSV", type="csv")
        manifest_file = st.file_uploader("Manifeste JSON", type="json")
        if csv_file is None or manifest_file is None:
            st.stop()
        levels, metadata, calendar, report = import_history(csv_file.getvalue(), manifest_file.getvalue())
    elif mode == "Export officiel iShares Europe":
        st.write("Import dédié à iShares Core MSCI Europe EUR Acc (IE00B4K48X80). Utilisez le fichier du bouton Download de l’émetteur, au format XML avec extension .xls.")
        st.link_button("Ouvrir l’export de l’émetteur", SOURCE_URL)
        issuer_file = st.file_uploader("Export iShares", type=["xls", "xml"])
        start = st.date_input("Date initiale exacte", date(2024, 12, 31))
        end = st.date_input("Date finale exacte", date(2025, 12, 31))
        if issuer_file is None:
            st.stop()
        levels, metadata, calendar, report = import_europe_export(issuer_file.getvalue(), date.today().isoformat(), start, end)
        st.warning("Le calendrier est rapproché de la feuille des valeurs liquidatives du même émetteur. Il n’est pas vérifié auprès d’une source indépendante. Les droits commerciaux restent non validés.")
        with st.expander("Contrôles de l’export"):
            st.json(report)
    else:
        st.write("Associez l’ETF actions Europe EUR Acc et l’ETF Global Aggregate EUR Hedged Acc. Les dates doivent être identiques, sans interpolation ni suppression automatique.")
        st.link_button("Export actions Europe", SOURCE_URL)
        st.link_button("Export obligations couvertes EUR", BOND_SOURCE_URL)
        europe_file = st.file_uploader("Fichier actions Europe", type=["xls", "xml"])
        bond_file = st.file_uploader("Fichier obligations", type=["xls", "xml"])
        start = st.date_input("Date initiale exacte", date(2021, 12, 31))
        end = st.date_input("Date finale exacte", date(2022, 12, 30))
        st.caption("2022 est la première période contrôlée pour cette paire. L’export obligataire consulté comporte des lacunes en 2025 : ce calcul doit être refusé tant qu’elles ne sont pas résolues.")
        if europe_file is None or bond_file is None:
            st.stop()
        levels, metadata, calendar, report = import_multi_asset_exports(europe_file.getvalue(), bond_file.getvalue(), date.today().isoformat(), start, end)
        st.warning("Calendriers issus des exports du même émetteur, non vérifiés indépendamment. Les droits commerciaux restent non validés. Ces deux supports ne constituent pas un portefeuille modèle recommandé.")
        with st.expander("Contrôles des deux exports"):
            st.json(report)
except ValueError as exc:
    st.error(f"Import refusé : {exc}")
    st.stop()
st.success(f"Contrôles techniques réussis : {len(levels)} observations, du {report['start']} au {report['end']}.")
st.caption("La complétude est contrôlée par rapport au calendrier fourni. L’authenticité des sources, les prix figés et la qualité économique des séries ne sont pas certifiés.")
if any(m.origin != "fund" for m in metadata.values()):
    st.warning("Cet import contient un proxy ou des données synthétiques. Le résultat n’est pas un historique intégral de placements réels.")
draft = st.session_state.get("allocation_draft", {})
weights = {key: st.number_input(f"Poids initial de {key} (%)", 0., 100., float(draft.get(key, 0.) * 100), key=f"backtest_weight_{key}") / 100 for key in levels}
if draft and set(draft) != set(levels):
    st.warning("Les identifiants importés diffèrent de votre allocation enregistrée. Vérifiez tous les poids ; aucun support absent n’est remplacé.")
st.caption(f"Total : {sum(weights.values()):.1%}. Aucun ajustement automatique.")
if st.button("Calculer sur cet historique", type="primary"):
    try:
        curve, _ = buy_and_hold(levels, weights, metadata, calendar)
        metrics = path_metrics(curve)
        st.line_chart(curve * 100, y_label="Valeur base 100")
        a, b = st.columns(2)
        a.metric("Rendement cumulé", f"{metrics['total_return']:.2%}")
        b.metric("Rendement annualisé géométrique", f"{metrics['cagr']:.2%}")
        st.write(f"Baisse maximale entre points observés : {metrics['max_drawdown']:.2%}.")
        st.caption("Cette baisse peut sous-estimer les pertes entre observations, notamment avec des données mensuelles ou annuelles. Aucun rééquilibrage, versement, fiscalité ou frais de transaction ; frais des fonds déjà inclus dans les séries. Le passé ne prédit pas les performances futures.")
        report.update(weights=weights, metrics=metrics, method="buy_and_hold_no_flows_v1")
        st.download_button("Exporter le rapport de calcul", json.dumps(report, indent=2, ensure_ascii=False), file_name="rapport_historique.json", mime="application/json")
        st.download_button("Exporter la courbe", curve.to_csv(), file_name="courbe_historique.csv", mime="text/csv")
    except ValueError as exc:
        st.error(str(exc))
