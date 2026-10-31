import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Trading Lab", page_icon="📊", layout="wide")

ASSETS = ["BTC", "ETH", "BNB", "SOL", "LINK", "XRP", "AVAX", "HYPE", "SUI"]
SEEDS = {a: i + 11 for i, a in enumerate(ASSETS)}
STARTING_BALANCE = 10_000.0  # unités fictives de laboratoire

@st.cache_data
def make_demo_data(asset: str, periods: int = 240) -> pd.DataFrame:
    """Prix déterministes entièrement synthétiques, sans source externe."""
    rng = np.random.default_rng(SEEDS[asset])
    drift = rng.normal(0.00015, 0.00025)
    shocks = rng.normal(drift, 0.012, periods)
    start = {"BTC": 65000, "ETH": 3200, "BNB": 600, "SOL": 150,
             "LINK": 15, "XRP": 0.55, "AVAX": 35, "HYPE": 25, "SUI": 1.2}[asset]
    close = start * np.exp(np.cumsum(shocks))
    index = pd.date_range(end=pd.Timestamp.now().floor("15min"), periods=periods, freq="15min")
    high = close * (1 + rng.uniform(0.001, 0.009, periods))
    low = close * (1 - rng.uniform(0.001, 0.009, periods))
    volume = rng.uniform(100, 1000, periods) * (1 + np.abs(shocks) * 30)
    return pd.DataFrame({"Close": close, "High": high, "Low": low, "Volume": volume}, index=index)

def add_indicators(df):
    out = df.copy()
    out["EMA20"] = out["Close"].ewm(span=20, adjust=False).mean()
    out["EMA50"] = out["Close"].ewm(span=50, adjust=False).mean()
    delta = out["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out["RSI14"] = 100 - (100 / (1 + rs))
    ema12 = out["Close"].ewm(span=12, adjust=False).mean()
    ema26 = out["Close"].ewm(span=26, adjust=False).mean()
    out["MACD"] = ema12 - ema26
    out["MACD_signal"] = out["MACD"].ewm(span=9, adjust=False).mean()
    return out

def observation(row):
    points, reasons = 0, []
    if row["EMA20"] > row["EMA50"]:
        points += 1
        reasons.append("EMA20 au-dessus de EMA50 : tendance courte relativement positive.")
    else:
        points -= 1
        reasons.append("EMA20 sous EMA50 : tendance courte relativement faible.")
    if row["MACD"] > row["MACD_signal"]:
        points += 1
        reasons.append("MACD au-dessus de sa ligne de signal : momentum positif.")
    else:
        points -= 1
        reasons.append("MACD sous sa ligne de signal : momentum négatif.")
    if pd.notna(row["RSI14"]):
        if row["RSI14"] >= 70:
            reasons.append("RSI élevé : le mouvement récent peut être déjà étendu.")
        elif row["RSI14"] <= 30:
            reasons.append("RSI faible : le mouvement récent peut être déjà étendu à la baisse.")
        else:
            reasons.append("RSI dans une zone intermédiaire.")
    label = "Biais positif" if points == 2 else "Biais négatif" if points == -2 else "Signaux mixtes"
    return label, reasons

def init_portfolio():
    if "cash_demo" not in st.session_state:
        st.session_state.cash_demo = STARTING_BALANCE
    if "holdings_demo" not in st.session_state:
        st.session_state.holdings_demo = {a: 0.0 for a in ASSETS}
    if "ledger_demo" not in st.session_state:
        st.session_state.ledger_demo = []

def portfolio_value(prices):
    return st.session_state.cash_demo + sum(
        st.session_state.holdings_demo[a] * prices[a] for a in ASSETS
    )

init_portfolio()

st.title("📊 AI Trading Lab")
st.caption("Prototype éducatif — données synthétiques, aucune connexion à une plateforme, aucun ordre réel.")
st.warning("Tous les prix, soldes et résultats sont fictifs. Les opérations ci-dessous sont uniquement des exercices de simulation.")

with st.sidebar:
    st.header("Paramètres du laboratoire")
    asset = st.selectbox("Actif étudié", ASSETS)
    window = st.slider("Nombre de bougies affichées", 40, 240, 120, 20)
    st.divider()
    st.markdown("**Mode :** simulation pédagogique")
    st.caption("Aucune donnée de marché en direct.")

all_data = {a: add_indicators(make_demo_data(a)) for a in ASSETS}
prices = {a: float(all_data[a]["Close"].iloc[-1]) for a in ASSETS}
data = all_data[asset].tail(window)
last = data.iloc[-1]
label, reasons = observation(last)

st.subheader("Portefeuille virtuel")
total_value = portfolio_value(prices)
invested_value = total_value - st.session_state.cash_demo
pnl = total_value - STARTING_BALANCE
pnl_pct = (pnl / STARTING_BALANCE) * 100

p1, p2, p3, p4 = st.columns(4)
p1.metric("Solde disponible", f"{st.session_state.cash_demo:,.2f} unités")
p2.metric("Valeur des actifs", f"{invested_value:,.2f} unités")
p3.metric("Valeur totale", f"{total_value:,.2f} unités")
p4.metric("Résultat simulé", f"{pnl:+,.2f} ({pnl_pct:+.2f} %)")

st.caption(f"Capital initial fictif : {STARTING_BALANCE:,.0f} unités de laboratoire. Ce montant n'est ni de l'argent réel ni une devise.")

st.markdown("#### Exercice d'achat ou de vente simulé")
trade_col1, trade_col2, trade_col3 = st.columns([1, 1, 1])
with trade_col1:
    trade_asset = st.selectbox("Actif de l'exercice", ASSETS, key="trade_asset")
with trade_col2:
    amount = st.number_input("Montant fictif (unités)", min_value=1.0, max_value=1_000_000.0, value=500.0, step=50.0)
with trade_col3:
    st.metric("Prix DEMO unitaire", f"{prices[trade_asset]:,.4f}")

buy_col, sell_col = st.columns(2)
with buy_col:
    if st.button("Simuler un achat", use_container_width=True):
        if amount > st.session_state.cash_demo:
            st.error("Solde virtuel insuffisant pour cet exercice.")
        else:
            quantity = amount / prices[trade_asset]
            st.session_state.cash_demo -= amount
            st.session_state.holdings_demo[trade_asset] += quantity
            st.session_state.ledger_demo.insert(0, {
                "Date/heure": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Opération": "Achat simulé", "Actif": trade_asset,
                "Quantité fictive": quantity, "Prix DEMO": prices[trade_asset],
                "Montant fictif": amount
            })
            st.rerun()
with sell_col:
    if st.button("Simuler une vente", use_container_width=True):
        quantity = amount / prices[trade_asset]
        if quantity > st.session_state.holdings_demo[trade_asset]:
            st.error("Quantité virtuelle détenue insuffisante pour cet exercice.")
        else:
            st.session_state.holdings_demo[trade_asset] -= quantity
            st.session_state.cash_demo += amount
            st.session_state.ledger_demo.insert(0, {
                "Date/heure": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Opération": "Vente simulée", "Actif": trade_asset,
                "Quantité fictive": quantity, "Prix DEMO": prices[trade_asset],
                "Montant fictif": amount
            })
            st.rerun()

st.divider()
st.subheader(f"Historique synthétique — {asset}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Actif", asset)
c2.metric("Prix DEMO", f"{last['Close']:,.4f}")
c3.metric("RSI (14)", f"{last['RSI14']:.1f}")
c4.metric("Observation", label)
st.line_chart(data[["Close", "EMA20", "EMA50"]], height=320)

left, right = st.columns(2)
with left:
    st.subheader("Indicateurs")
    st.line_chart(data[["RSI14"]], height=180)
    st.line_chart(data[["MACD", "MACD_signal"]], height=180)
with right:
    st.subheader("Explication pédagogique")
    st.info("Les observations illustrent des règles simples. Elles ne prédisent pas l'évolution des prix et ne constituent pas des recommandations.")
    for reason in reasons:
        st.write("• " + reason)

st.divider()
st.subheader("Composition du portefeuille virtuel")
holdings_rows = []
for a in ASSETS:
    qty = st.session_state.holdings_demo[a]
    holdings_rows.append({
        "Actif": a, "Quantité fictive": qty,
        "Prix DEMO": prices[a], "Valeur fictive": qty * prices[a]
    })
st.dataframe(pd.DataFrame(holdings_rows), use_container_width=True, hide_index=True)

st.subheader("Journal des opérations simulées")
if st.session_state.ledger_demo:
    st.dataframe(pd.DataFrame(st.session_state.ledger_demo), use_container_width=True, hide_index=True)
else:
    st.info("Aucune opération simulée pour le moment. Tu peux utiliser les boutons ci-dessus pour apprendre le fonctionnement d'un portefeuille fictif.")

if st.button("Réinitialiser le portefeuille virtuel"):
    st.session_state.cash_demo = STARTING_BALANCE
    st.session_state.holdings_demo = {a: 0.0 for a in ASSETS}
    st.session_state.ledger_demo = []
    st.rerun()

st.caption("Les opérations et le portefeuille sont conservés pendant la session de l'application. Un redémarrage peut réinitialiser les données.")
