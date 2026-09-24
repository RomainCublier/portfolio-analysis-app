"""Dated manual EUR snapshot, deliberately not a performance history."""
from datetime import date
from core.tracking import session_valuations, upsert_valuation
import pandas as pd
import streamlit as st

st.title("Mon portefeuille réel")
st.write("Renseignez uniquement les investissements que vous détenez. Retrouvez leur valeur actuelle dans votre espace courtier.")
st.info("Chaque état enregistré conserve sa valeur totale dans « Suivre mon évolution ». Les valorisations et les mouvements restent déclaratifs, sans connexion à votre courtier.")
previous = st.session_state.get("real_snapshot")
snapshot_date = st.date_input("Date des valorisations", previous[2] if previous is not None else date.today(), max_value=date.today())
st.caption("Saisissez toutes les valeurs en euros, y compris pour les titres cotés dans une autre devise. Utilisez la valorisation en euros de votre courtier à la date choisie.")
empty = pd.DataFrame({"Compte": pd.Series(dtype=str), "Support / ISIN": pd.Series(dtype=str),
                      "Valeur actuelle (€)": pd.Series(dtype=float)})
positions = st.data_editor(st.session_state.get("real_positions", empty), num_rows="dynamic",
    column_config={"Compte": st.column_config.SelectboxColumn(options=["PEA", "CTO"], required=True),
                   "Support / ISIN": st.column_config.TextColumn(required=True),
                   "Valeur actuelle (€)": st.column_config.NumberColumn(min_value=0.0, required=True)},
    use_container_width=True, key=f"real_positions_editor_{st.session_state.get('positions_revision', 0)}")
cash = st.number_input("Liquidités totales disponibles sur ces comptes (€)", 0.0, 100_000_000.0, float(previous[1]) if previous is not None else 0.0)
st.caption("Les liquidités sont affichées séparément des supports détenus. Saisissez des valeurs de fin de journée, après les mouvements du jour. Un nouvel enregistrement à la même date corrige la valeur totale conservée pour cette date.")
if st.button("Afficher mon état des positions", type="primary"):
    import numpy as np
    clean = positions.dropna(how="all").copy()
    values = pd.to_numeric(clean["Valeur actuelle (€)"], errors="coerce")
    labels = clean["Support / ISIN"].fillna("").astype(str).str.strip()
    if (clean["Compte"].isin(["PEA", "CTO"]).all() and labels.ne("").all()
            and labels.str.len().le(200).all() and len(clean) <= 1000
            and np.isfinite(values).all() and values.between(0, 100_000_000).all()):
        clean["Valeur actuelle (€)"] = values
        clean["Support / ISIN"] = labels
        try:
            history = upsert_valuation(session_valuations(st.session_state), snapshot_date.isoformat(), float(values.sum()) + cash)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        st.session_state.portfolio_valuations = history
        st.session_state.real_snapshot = (clean, cash, snapshot_date)
        st.session_state.real_positions = clean.copy()
        st.session_state.positions_revision = st.session_state.get("positions_revision", 0) + 1
        st.rerun()
    else:
        st.error("Complétez chaque ligne : compte, support (200 caractères maximum) et valeur entre 0 et 100 millions d’euros. Maximum : 1 000 lignes.")
if "real_snapshot" in st.session_state:
    saved, saved_cash, saved_date = st.session_state.real_snapshot
    total = saved["Valeur actuelle (€)"].sum() + saved_cash
    st.subheader(f"État calculé au {saved_date:%d/%m/%Y}")
    st.metric("Valeur totale déclarée", f"{total:,.2f} €".replace(",", " "))
    if total > 0:
        display = saved.groupby(["Compte", "Support / ISIN"], as_index=False)["Valeur actuelle (€)"].sum()
        display["Part du total (%)"] = display["Valeur actuelle (€)"] / total * 100
        st.dataframe(display, hide_index=True, use_container_width=True)
        st.write(f"Liquidités : {saved_cash:,.2f} € ({saved_cash / total:.1%} du total).")
    else:
        st.info("Votre portefeuille est vide. Vous pouvez préparer un projet depuis « Construire mon projet ».")
    export = saved.copy()
    export.loc[len(export)] = ["Tous comptes", "Liquidités", saved_cash]
    export["Date de valorisation"] = saved_date.isoformat()
    st.download_button("Exporter cet état (CSV)", export.to_csv(index=False).encode("utf-8-sig"), "positions.csv", "text/csv")
    st.caption("Valeurs déclarées, sans vérification de cours. Après une modification, cliquez sur « Afficher » pour recalculer. Cet export est un état des positions, pas un historique de performance.")
st.caption("Les données restent dans cette session et ne sont pas sauvegardées dans un compte utilisateur. Exportez votre état avant de quitter.")
