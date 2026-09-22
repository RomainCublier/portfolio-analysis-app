import pandas as pd
import streamlit as st
from core.catalog import load_catalog, review_status

st.title("Explorer les supports")
st.write("Comparez ETF, fonds et actions. Le type de support ne suffit pas à déterminer son risque ni le niveau d’expérience nécessaire.")
st.info("Catalogue de recherche non exhaustif, sans classement ni sélection personnalisée. Les historiques de marché ne sont pas encore connectés.")
rows = load_catalog()
kind = st.selectbox("Type de support", ["Tous", "ETF", "Fonds", "Action"])
category = st.selectbox("Quelle exposition souhaitez-vous explorer ?", ["Toutes"] + sorted({r["category"] for r in rows}))
pea_only = st.checkbox("Afficher uniquement les supports dont l’éligibilité PEA est documentée")
query = st.text_input("Rechercher un nom ou un ISIN")
filtered = [r for r in rows if (category == "Toutes" or r["category"] == category)
            and (kind == "Tous" or r["instrument_kind"] == kind)
            and (not pea_only or r["facts"]["pea"] is True)
            and query.casefold().strip() in (r["name"] + r["isin"]).casefold()]
st.caption(f"{len(filtered)} support(s). Une éligibilité inconnue n’est pas une inéligibilité. La disponibilité chez votre courtier n’est pas vérifiée.")
for row in filtered:
    f = row["facts"]
    with st.expander(row["name"]):
        st.write(f"**ISIN :** {row['isin']} · **Exposition :** {row['category']}")
        st.caption(f"{review_status(row)} — consultation le {row['reviewed_on']}" + (f" ; document daté du {row['source_date']}" if row['source_date'] else " ; date de publication non indiquée"))
        fields = {"Type de support": row["instrument_kind"], "Indicateur de référence": f["benchmark"], "Devise de la part": f["share_currency"],
                  "Couverture de change documentée": f["hedging"], "Revenus": f["income"],
                  "Réplication": f["replication"] if row["instrument_kind"] == "ETF" else "Sans objet", "Création de la part": f["launch_date"],
                  "Éligibilité PEA": "Oui, documentée" if f["pea"] is True else "Non, documentée" if f["pea"] is False else None,
                  "Frais annuels publiés": f"{f['fee_percent']:.2f} % — {f['fee_label']}" if f['fee_percent'] is not None else None}
        if row["instrument_kind"] == "Action":
            fields = {"Type de support": "Action individuelle", "Éligibilité PEA": fields["Éligibilité PEA"],
                      "Frais du fonds": "Sans objet — frais de courtage et autres coûts non évalués"}
        for key, label in [("entry_fee_max_percent", "Frais d’entrée maximum"), ("transaction_cost_estimate_percent", "Coûts de transaction estimés du fonds")]:
            if f.get(key) is not None:
                fields[label] = f"{f[key]:.2f} % — voir les conditions de la source"
        st.dataframe(pd.DataFrame({"Caractéristique": fields.keys(), "Information": [v if v is not None else "Non vérifié" for v in fields.values()]}), hide_index=True, use_container_width=True)
        if f.get("benchmark_note"):
            st.write(f["benchmark_note"])
        if row.get("review_note"):
            st.write(row["review_note"])
        if f.get("performance_fee_note"):
            st.write(f["performance_fee_note"])
        st.link_button("Consulter la source officielle", row["source_url"])
st.caption("Les frais publiés ne représentent pas tous les coûts : courtage et écarts achat/vente peuvent s’ajouter. La devise d’une part ne suffit pas à identifier son exposition de change. Aucune de ces fiches ne garantit le capital.")
if not filtered:
    st.info("Aucun support du catalogue ne correspond à ces critères.")
