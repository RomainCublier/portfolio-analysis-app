import streamlit as st

from config import assumptions
from gpt_allocation import generate_portfolio_allocation
from portfolio_engine import backtest_portfolio
from utils.streamlit_helpers import handle_network_error

st.title("🤖 AI Portfolio Generator (No API Needed)")

st.subheader("Investor Profile")

col1, col2 = st.columns(2)

with col1:
    capital = st.number_input("Capital to invest (€)", min_value=100, value=10000)

with col2:
    risk = st.selectbox("Risk Level", assumptions.RISK_LEVELS)

horizon = st.selectbox("Investment Horizon", assumptions.INVESTMENT_HORIZONS)
esg = st.checkbox("Include ESG constraints (exclude BTC)?")

if st.button("Generate Portfolio"):
    try:
        df_alloc = generate_portfolio_allocation(capital, risk, horizon, esg)

        st.success("Portfolio generated successfully!")
        st.subheader("📊 Allocation Results")
        st.dataframe(df_alloc)

        weights_series = df_alloc.set_index("Ticker")["Allocation (%)"].astype(float) / 100
        weights_series = weights_series / weights_series.sum()
        st.session_state["portfolio_weights"] = weights_series

        st.subheader("📈 Performance preview of generated portfolio")
        fig, stats = backtest_portfolio(df_alloc)
        st.plotly_chart(fig, use_container_width=True)
        st.write(stats)

    except Exception as exc:  # noqa: BLE001
        st.error(f"❌ Error during calculation: {handle_network_error(exc)}")
