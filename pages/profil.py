import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError

from core.catalog import load_catalog, review_status
from core.planning import Project
from core.profile import matching_catalog_rows, profile_frame


def safe_page_link(path, label, icon):
    try:
        st.page_link(path, label=label, icon=icon)
    except StreamlitPageNotFoundError:
        st.caption(label)


st.title("Comprendre mon profil")
st.warning("Module expérimental non inclus dans la V1 publique.")
st.write("Transformez votre projet en cadre d’investissement explicable avant de construire une allocation.")
st.caption("Cette page ne recommande aucun support. Elle décrit des familles d’investissement possibles, leurs limites et les données à vérifier.")

project = st.session_state.get("project", Project())
if "project" not in st.session_state:
    st.info("Aucun projet enregistré : l’analyse ci-dessous utilise les valeurs par défaut. Enregistrez votre situation dans « Construire mon projet » pour personnaliser ce cadre.")
    safe_page_link("pages/commencer.py", label="Renseigner mon projet", icon="🌱")

frame = profile_frame(project)
left, middle, right = st.columns(3)
left.metric("Horizon", frame.horizon_bucket)
middle.metric("Budget de risque", frame.risk_budget)
right.metric("Complexité utile", frame.complexity)

st.subheader("Cadre de risque")
st.write(frame.reserve_message)
st.write(
    f"Fourchette pédagogique d’exposition actions à étudier : **{frame.equity_floor:.0%} à {frame.equity_ceiling:.0%}**. "
    "Elle sert à organiser les simulations, pas à conclure qu’elle convient définitivement."
)
if frame.stock_picking_cap:
    st.write(f"Poche d’actions individuelles à garder satellite : **jusqu’à {frame.stock_picking_cap:.0%}** du portefeuille modèle.")
else:
    st.write("Poche d’actions individuelles : non prioritaire dans ce cadre. Commencer par des briques diversifiées et compréhensibles.")

with st.expander("PEA, CTO et rôle des enveloppes"):
    for note in frame.envelope_notes:
        st.write(note)
    st.caption("L’éligibilité PEA, la disponibilité courtier et la fiscalité doivent être vérifiées avant toute utilisation réelle.")

st.subheader("Briques de portefeuille à explorer")
rows = load_catalog()
summary = pd.DataFrame(
    [{"Brique": b["role"], "Rôle": b["use"], "Filtre catalogue": b["catalog_filter"]} for b in frame.building_blocks]
)
st.dataframe(summary, hide_index=True, use_container_width=True)

for block in frame.building_blocks:
    matches = matching_catalog_rows(rows, block)
    with st.expander(block["role"]):
        st.write(block["use"])
        if not matches:
            st.info("Aucun support du catalogue actuel ne correspond encore à cette brique.")
            continue
        table = []
        for row in matches:
            fee = row["facts"].get("fee_percent")
            table.append({
                "Nom": row["name"],
                "ISIN": row["isin"],
                "Type": row["instrument_kind"],
                "Catégorie": row["category"],
                "Frais publiés": "Non vérifié" if fee is None else f"{fee:.2f} %",
                "Statut": review_status(row),
            })
        st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
        st.caption("Ces lignes sont des exemples documentés du catalogue de recherche, pas une sélection personnalisée.")

st.subheader("Garde-fous à conserver")
for item in frame.guardrails:
    st.write(f"- {item}")

safe_page_link("pages/allocation.py", label="Tester une allocation à partir de ce cadre", icon="⚖️")
