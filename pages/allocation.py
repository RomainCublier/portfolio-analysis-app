from datetime import date
import pandas as pd
import streamlit as st
from core.catalog import load_catalog
from core.allocation import allocation_diagnostics

st.title("Tester une allocation")
st.write("Assemblez des supports et examinez leur répartition. Il s’agit d’un portefeuille fictif, distinct de vos positions réelles.")
catalog = {r["isin"]: r for r in load_catalog()}
selected = st.multiselect("Quels supports voulez-vous comparer ensemble ?", list(catalog),
                          format_func=lambda k: f"{catalog[k]['name']} — {k}")
if not selected:
    st.info("Commencez par choisir des supports. Aucun portefeuille n’est présélectionné.")
    st.stop()
weights = {}
for key in selected:
    weights[key] = st.number_input(f"Part de {catalog[key]['name']} (%)", min_value=0., max_value=100., value=0., step=1., key=f"allocation_{key}") / 100
st.caption(f"Total saisi : {sum(weights.values()):.1%}. Les poids ne sont pas ajustés automatiquement.")

limits = {}
with st.expander("Définir mes limites de concentration (facultatif)"):
    st.write("Ces limites sont vos choix de simulation, pas des règles universelles ni une validation de votre profil. Un ETF très diversifié et une action individuelle n’ont pas le même risque à poids égal.")
    for key, label in [("position", "Poids maximum d’un support"), ("stock_picking", "Poids maximum des actions détenues directement"), ("issuer", "Exposition maximum à un émetteur, fonds inclus")]:
        if st.checkbox(label, key=f"enable_{key}"):
            limits[key] = st.number_input(label + " (%)", 0., 100., 100., key=f"cap_{key}") / 100
if st.button("Examiner cette allocation", type="primary"):
    try:
        kinds = {key: catalog[key]["instrument_kind"] for key in weights}
        # No current consolidated holdings dataset connected: do not infer it
        # from benchmark weights, marketing category or stale top holdings.
        report = allocation_diagnostics(weights, kinds, {}, date.today(), limits)
        st.session_state.allocation_draft = dict(weights)
        st.subheader("Répartition par type de support")
        st.dataframe(pd.DataFrame([{"Type": k, "Poids (%)": v * 100} for k, v in report["by_kind"].items()]), hide_index=True)
        st.warning("Les compositions sous-jacentes et identifiants émetteurs consolidés ne sont pas encore connectés. Les recouvrements entre fonds et actions ne sont donc pas mesurés. Le nombre de supports ne permet pas de conclure que ce portefeuille est diversifié.")
        if report["checks"]:
            labels = {"position": "Support individuel", "stock_picking": "Actions détenues directement", "issuer": "Émetteur (fonds inclus)"}
            st.dataframe(pd.DataFrame([{"Critère": labels[c['criterion']], "Valeur (%)": None if c['criterion'] == 'issuer' else c['observed'] * 100,
                "Limite (%)": c['limit'] * 100, "Résultat": c['status']} for c in report['checks']]), hide_index=True)
        st.caption("Allocation conservée pour cette session. Aucune mesure de volatilité, corrélation, risque obligataire ou liquidité n’est déduite des seuls poids. Les critères ci-dessus ne constituent pas une validation globale du risque.")
    except ValueError as exc:
        st.error(str(exc))
