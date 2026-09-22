import json
from pathlib import Path
import streamlit as st
from core.history_import import import_history
from core.history import buy_and_hold, path_metrics

st.title("Explorer un historique")
st.write("Comparez une allocation initiale conservée sur une période passée, à partir de séries de rendement total net en euros.")
st.info("Version de recherche : aucun flux de marché n’est encore connecté. Les sources et les droits des fichiers importés restent à vérifier indépendamment.")
with st.expander("Préparer mes données"):
    st.write("Importez un CSV (date puis une colonne par identifiant) et son manifeste JSON : calendrier attendu, sources, dates de récupération, origine et empreinte SHA-256 du CSV. Les distributions doivent être réinvesties et les frais des fonds déjà inclus. Un cours brut seul ne convient pas.")
    example = Path(__file__).resolve().parents[1] / "data" / "examples"
    for name in ["synthetic_history.csv", "synthetic_manifest.json"]:
        st.download_button("Télécharger " + name, (example / name).read_bytes(), file_name=name)
    st.caption("Ces fichiers sont entièrement synthétiques : ils expliquent le format et ne décrivent aucun placement réel.")
csv_file = st.file_uploader("Historique CSV", type="csv")
manifest_file = st.file_uploader("Manifeste JSON", type="json")
if csv_file is None or manifest_file is None:
    st.stop()
try:
    levels, metadata, calendar, report = import_history(csv_file.getvalue(), manifest_file.getvalue())
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
