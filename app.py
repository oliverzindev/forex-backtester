import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Forex Backtester", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .stMetric { background: #1a1a2e; border-radius: 10px; padding: 0.75rem 1rem; border: 1px solid #2a2a4a; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 600; }
    div[data-testid="stMetricLabel"] { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
    .stSelectbox label, .stSlider label, .stNumberInput label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

PLOT_BG = "#0f0f1a"
GRID = "#1e1e2e"

st.markdown("## 📈 Forex Backtester")
st.markdown("<p style='color:#888; margin-top:-0.75rem; margin-bottom:1.5rem;'>Testa múltiplas estratégias com dados reais do mercado</p>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
with col1:
    pair = st.selectbox("Par de moedas", ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCHF=X"])
with col2:
    capital = st.number_input("Capital inicial (€)", min_value=100, value=10000, step=500)
with col3:
    strategy = st.selectbox("Estratégia", ["Médias Móveis (SMA)", "RSI", "MACD", "Bollinger Bands"])
with col4:
    period = st.selectbox("Período", ["6mo", "1y", "2y"], index=1)

st.divider()

with st.spinner("A carregar dados..."):
    raw = yf.download(pair, period=period, interval="1d", auto_adjust=True, progress=False)
    data = raw.copy()
    data.columns = [c[0] if isinstance(c, tuple) else c for c in data.columns]

def calc_sma(data):
    col1, col2 = st.columns(2)
    with col1: fast = st.slider("Média rápida (dias)", 3, 30, 10)
    with col2: slow = st.slider("Média lenta (dias)", 10, 100, 30)
    data["SMA_fast"] = data["Close"].rolling(fast).mean()
    data["SMA_slow"] = data["Close"].rolling(slow).mean()
    data = data.dropna().reset_index()
    signals = []
    for i in range(1, len(data)):
        pf, ps = float(data.loc[i-1, "SMA_fast"]), float(data.loc[i-1, "SMA_slow"])
        cf, cs = float(data.loc[i, "SMA_fast"]), float(data.loc[i, "SMA_slow"])
        if pf <= ps and cf > cs: signals.append((i, "buy"))
        elif pf >= ps and cf < cs: signals.append((i, "sell"))
    traces = [
        go.Scatter(x=data["Date"], y=data["Close"], name="Preço", line=dict(color="#60a5fa", width=1.5)),
        go.Scatter(x=data["Date"], y=data["SMA_fast"], name=f"SMA {fast}", line=dict(color="#f97316", dash="dash")),
        go.Scatter(x=data["Date"], y=data["SMA_slow"], name=f"SMA {slow}", line=dict(color="#34d399", dash="dash")),
    ]
    return data, signals, traces

def calc_rsi(data):
    period_rsi = st.slider("Período RSI", 5, 30, 14)
    ob = st.slider("Sobrecomprado", 60, 90, 70)
    os_ = st.slider("Sobrevendido", 10, 40, 30)
    delta = data["Close"].diff()
    gain = delta.clip(lower=0).rolling(period_rsi).mean()
    loss = (-delta.clip(upper=0)).rolling(period_rsi).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))
    data = data.dropna().reset_index()
    signals = []
    for i in range(1, len(data)):
        pr, cr = float(data.loc[i-1, "RSI"]), float(data.loc[i, "RSI"])
        if pr <= os_ and cr > os_: signals.append((i, "buy"))
        elif pr >= ob and cr < ob: signals.append((i, "sell"))
    traces = [
        go.Scatter(x=data["Date"], y=data["Close"], name="Preço", line=dict(color="#60a5fa", width=1.5)),
    ]
    return data, signals, traces

def calc_macd(data):
    col1, col2, col3 = st.columns(3)
    with col1: fast = st.slider("EMA rápida", 5, 20, 12)
    with col2: slow = st.slider("EMA lenta", 15, 40, 26)
    with col3: signal = st.slider("Sinal", 5, 15, 9)
    ema_fast = data["Close"].ewm(span=fast).mean()
    ema_slow = data["Close"].ewm(span=slow).mean()
    data["MACD"] = ema_fast - ema_slow
    data["Signal"] = data["MACD"].ewm(span=signal).mean()
    data = data.dropna().reset_index()
    signals = []
    for i in range(1, len(data)):
        pm, ps = float(data.loc[i-1, "MACD"]), float(data.loc[i-1, "Signal"])
        cm, cs = float(data.loc[i, "MACD"]), float(data.loc[i, "Signal"])
        if pm <= ps and cm > cs: signals.append((i, "buy"))
        elif pm >= ps and cm < cs: signals.append((i, "sell"))
    traces = [
        go.Scatter(x=data["Date"], y=data["Close"], name="Preço", line=dict(color="#60a5fa", width=1.5)),
    ]
    return data, signals, traces

def calc_bb(data):
    col1, col2 = st.columns(2)
    with col1: window = st.slider("Período", 10, 50, 20)
    with col2: std = st.slider("Desvios padrão", 1, 4, 2)
    data["BB_mid"] = data["Close"].rolling(window).mean()
    data["BB_up"] = data["BB_mid"] + std * data["Close"].rolling(window).std()
    data["BB_dn"] = data["BB_mid"] - std * data["Close"].rolling(window).std()
    data = data.dropna().reset_index()
    signals = []
    for i in range(1, len(data)):
        pc, pu, pd_ = float(data.loc[i-1, "Close"]), float(data.loc[i-1, "BB_up"]), float(data.loc[i-1, "BB_dn"])
        cc, cu, cd = float(data.loc[i, "Close"]), float(data.loc[i, "BB_up"]), float(data.loc[i, "BB_dn"])
        if pc <= pd_ and cc > cd: signals.append((i, "buy"))
        elif pc >= pu and cc < cu: signals.append((i, "sell"))
    traces = [
        go.Scatter(x=data["Date"], y=data["Close"], name="Preço", line=dict(color="#60a5fa", width=1.5)),
        go.Scatter(x=data["Date"], y=data["BB_up"], name="Banda sup.", line=dict(color="#f97316", dash="dot", width=1)),
        go.Scatter(x=data["Date"], y=data["BB_mid"], name="Média", line=dict(color="#888", dash="dash", width=1)),
        go.Scatter(x=data["Date"], y=data["BB_dn"], name="Banda inf.", line=dict(color="#34d399", dash="dot", width=1)),
    ]
    return data, signals, traces

st.markdown(f"**Parâmetros — {strategy}**")
if strategy == "Médias Móveis (SMA)":
    data, signals, traces = calc_sma(data)
elif strategy == "RSI":
    data, signals, traces = calc_rsi(data)
elif strategy == "MACD":
    data, signals, traces = calc_macd(data)
else:
    data, signals, traces = calc_bb(data)

# Backtest
position = 0
cash = float(capital)
trades = []
equity = []
entry_price = 0
buy_x, buy_y, sell_x, sell_y = [], [], [], []

for idx, direction in signals:
    price = float(data.loc[idx, "Close"])
    date = data.loc[idx, "Date"]
    if direction == "buy" and position == 0:
        position = cash / price
        entry_price = price
        cash = 0
        buy_x.append(date); buy_y.append(price)
    elif direction == "sell" and position > 0:
        proceeds = position * price
        pnl = proceeds - (position * entry_price)
        trades.append({"Data": str(date)[:10], "Entrada": round(entry_price, 5), "Saída": round(price, 5), "P&L (€)": round(pnl, 2), "Resultado": "✅ Lucro" if pnl > 0 else "❌ Perda"})
        cash = proceeds
        position = 0
        sell_x.append(date); sell_y.append(price)

for i in range(len(data)):
    equity.append(cash + position * float(data.loc[i, "Close"]))

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

if buy_x:
    traces.append(go.Scatter(x=buy_x, y=buy_y, mode="markers", name="Compra", marker=dict(color="#34d399", size=10, symbol="triangle-up")))
if sell_x:
    traces.append(go.Scatter(x=sell_x, y=sell_y, mode="markers", name="Venda", marker=dict(color="#f87171", size=10, symbol="triangle-down")))

fig = go.Figure(data=traces)
fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG, font=dict(color="#ccc"), legend=dict(bgcolor="#1a1a2e", bordercolor="#2a2a4a", borderwidth=1), xaxis=dict(gridcolor=GRID), yaxis=dict(gridcolor=GRID))
st.plotly_chart(fig, use_container_width=True)

if equity:
    eq_fig = go.Figure()
    eq_fig.add_trace(go.Scatter(x=data["Date"], y=equity, fill="tozeroy", line=dict(color="#a78bfa", width=2), fillcolor="rgba(167,139,250,0.08)"))
    eq_fig.update_layout(height=160, margin=dict(l=0, r=0, t=10, b=0), showlegend=False, plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG, font=dict(color="#ccc"), xaxis=dict(gridcolor=GRID), yaxis=dict(gridcolor=GRID, tickprefix="€"))
    st.caption("Curva de equity")
    st.plotly_chart(eq_fig, use_container_width=True)

st.divider()

if trades:
    st.markdown(f"**Histórico de operações** — {len(trades)} trades executados")
    st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
else:
    st.info("Nenhum trade executado. Tenta ajustar os parâmetros.")

st.markdown("<br><p style='color:#444; font-size:0.75rem; text-align:center;'>Dados: Yahoo Finance · Apenas para fins educativos · Não constitui aconselhamento financeiro</p>", unsafe_allow_html=True)