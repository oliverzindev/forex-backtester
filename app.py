import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Forex Backtester", page_icon="📈", layout="wide")

st.title("Forex Backtester")
st.caption("Testa estratégias de médias móveis com dados reais")

col1, col2, col3, col4 = st.columns(4)

with col1:
    pair = st.selectbox("Par de moedas", ["EURUSD=X", "GBPUSD=X", "USDJPY=X"])
with col2:
    capital = st.number_input("Capital inicial (€)", min_value=100, value=10000, step=500)
with col3:
    fast = st.slider("Média rápida (dias)", 3, 30, 10)
with col4:
    slow = st.slider("Média lenta (dias)", 10, 100, 30)

st.divider()

with st.spinner("A carregar dados..."):
    raw = yf.download(pair, period="1y", interval="1d", auto_adjust=True, progress=False)
    data = raw.copy()
    data.columns = [c[0] if isinstance(c, tuple) else c for c in data.columns]
    data["SMA_fast"] = data["Close"].rolling(fast).mean()
    data["SMA_slow"] = data["Close"].rolling(slow).mean()
    data = data.dropna(subset=["SMA_fast", "SMA_slow"])
    data = data.reset_index()

# Motor de backtest
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

# Métricas
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Capital final", f"€{final:,.0f}")
m2.metric("Retorno", f"{ret:+.1f}%")
m3.metric("Trades totais", len(trades))
m4.metric("Taxa de acerto", f"{winrate:.0f}%")
m5.metric("Capital inicial", f"€{capital:,.0f}")
st.divider()

# Gráfico de preço
fig = go.Figure()
fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], name="Preço", line=dict(color="#378ADD", width=1.5)))
fig.add_trace(go.Scatter(x=data["Date"], y=data["SMA_fast"], name=f"SMA {fast}", line=dict(color="#D85A30", dash="dash")))
fig.add_trace(go.Scatter(x=data["Date"], y=data["SMA_slow"], name=f"SMA {slow}", line=dict(color="#1D9E75", dash="dash")))
fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, use_container_width=True)

# Curva de equity
if equity:
    eq_fig = go.Figure()
    eq_fig.add_trace(go.Scatter(
        x=data["Date"].iloc[1:len(equity)+1], y=equity,
        fill="tozeroy", name="Equity",
        line=dict(color="#534AB7", width=2),
        fillcolor="rgba(83,74,183,0.1)"
    ))
    eq_fig.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.caption("Curva de equity")
    st.plotly_chart(eq_fig, use_container_width=True)

# Tabela de trades
if trades:
    st.caption(f"Histórico de operações ({len(trades)} trades)")
    st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
else:
    st.info("Nenhum trade executado. Tenta ajustar as médias.")