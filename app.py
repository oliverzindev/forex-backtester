import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Forex Backtester", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .metric-card { background: #1e1e2e; border: 1px solid #2e2e4e; border-radius: 12px; padding: 1rem 1.25rem; }
    .stMetric { background: #1a1a2e; border-radius: 10px; padding: 0.75rem 1rem; border: 1px solid #2a2a4a; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 600; }
    div[data-testid="stMetricLabel"] { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
    .stSelectbox label, .stSlider label, .stNumberInput label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📈 Forex Backtester")
st.markdown("<p style='color:#888; margin-top:-0.75rem; margin-bottom:1.5rem;'>Testa estratégias de médias móveis com dados reais do mercado</p>", unsafe_allow_html=True)

with st.container():
    col1, col2, col3, col4 = st.columns([2, 2, 3, 3])
    with col1:
        pair = st.selectbox("Par de moedas", ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCHF=X"])
    with col2:
        capital = st.number_input("Capital inicial (€)", min_value=100, value=10000, step=500)
    with col3:
        fast = st.slider("Média rápida (dias)", 3, 30, 10)
    with col4:
        slow = st.slider("Média lenta (dias)", 10, 100, 30)

st.divider()

with st.spinner("A carregar dados do mercado..."):
    raw = yf.download(pair, period="1y", interval="1d", auto_adjust=True, progress=False)
    data = raw.copy()
    data.columns = [c[0] if isinstance(c, tuple) else c for c in data.columns]
    data["SMA_fast"] = data["Close"].rolling(fast).mean()
    data["SMA_slow"] = data["Close"].rolling(slow).mean()
    data = data.dropna(subset=["SMA_fast", "SMA_slow"]).reset_index()

position = 0
cash = float(capital)
trades = []
equity = []
entry_price = 0

for i in range(1, len(data)):
    pf = float(data.loc[i-1, "SMA_fast"])
    ps = float(data.loc[i-1, "SMA_slow"])
    cf = float(data.loc[i, "SMA_fast"])
    cs = float(data.loc[i, "SMA_slow"])
    price = float(data.loc[i, "Close"])
    date = data.loc[i, "Date"]

    if pf <= ps and cf > cs and position == 0:
        position = cash / price
        entry_price = price
        cash = 0
    elif pf >= ps and cf < cs and position > 0:
        proceeds = position * price
        pnl = proceeds - (position * entry_price)
        trades.append({
            "Data": str(date)[:10],
            "Entrada": round(entry_price, 5),
            "Saída": round(price, 5),
            "P&L (€)": round(pnl, 2),
            "Resultado": "✅ Lucro" if pnl > 0 else "❌ Perda"
        })
        cash = proceeds
        position = 0

    equity.append(cash + position * price)

final = cash + position * float(data["Close"].iloc[-1])
ret = (final - float(capital)) / float(capital) * 100
wins = sum(1 for t in trades if t["P&L (€)"] > 0)
winrate = (wins / len(trades) * 100) if trades else 0
best = max((t["P&L (€)"] for t in trades), default=0)
worst = min((t["P&L (€)"] for t in trades), default=0)

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Capital final", f"€{final:,.0f}", f"{ret:+.1f}%")
m2.metric("Retorno total", f"{ret:+.1f}%")
m3.metric("Trades totais", len(trades))
m4.metric("Taxa de acerto", f"{winrate:.0f}%")
m5.metric("Melhor trade", f"€{best:+.0f}")
m6.metric("Pior trade", f"€{worst:+.0f}")

st.markdown("<br>", unsafe_allow_html=True)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=data["Date"], y=data["Close"],
    name="Preço", line=dict(color="#60a5fa", width=1.5)
))
fig.add_trace(go.Scatter(
    x=data["Date"], y=data["SMA_fast"],
    name=f"SMA {fast}", line=dict(color="#f97316", dash="dash", width=1.5)
))
fig.add_trace(go.Scatter(
    x=data["Date"], y=data["SMA_slow"],
    name=f"SMA {slow}", line=dict(color="#34d399", dash="dash", width=1.5)
))
fig.update_layout(
    height=400,
    margin=dict(l=0, r=0, t=10, b=0),
    plot_bgcolor="#0f0f1a",
    paper_bgcolor="#0f0f1a",
    font=dict(color="#ccc"),
    legend=dict(bgcolor="#1a1a2e", bordercolor="#2a2a4a", borderwidth=1),
    xaxis=dict(gridcolor="#1e1e2e", showgrid=True),
    yaxis=dict(gridcolor="#1e1e2e", showgrid=True),
)
st.plotly_chart(fig, use_container_width=True)

if equity:
    eq_fig = go.Figure()
    eq_fig.add_trace(go.Scatter(
        x=data["Date"].iloc[1:len(equity)+1], y=equity,
        fill="tozeroy", name="Equity",
        line=dict(color="#a78bfa", width=2),
        fillcolor="rgba(167,139,250,0.08)"
    ))
    eq_fig.update_layout(
        height=180,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        plot_bgcolor="#0f0f1a",
        paper_bgcolor="#0f0f1a",
        font=dict(color="#ccc"),
        xaxis=dict(gridcolor="#1e1e2e"),
        yaxis=dict(gridcolor="#1e1e2e", tickprefix="€"),
    )
    st.caption("Curva de equity")
    st.plotly_chart(eq_fig, use_container_width=True)

st.divider()

if trades:
    st.markdown(f"**Histórico de operações** — {len(trades)} trades executados")
    df = pd.DataFrame(trades)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum trade executado com estes parâmetros. Tenta ajustar as médias móveis.")

st.markdown("<br><p style='color:#444; font-size:0.75rem; text-align:center;'>Dados fornecidos pelo Yahoo Finance · Apenas para fins educativos · Não constitui aconselhamento financeiro</p>", unsafe_allow_html=True)