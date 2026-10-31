import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Trading Lab", page_icon="📊", layout="wide")

ASSETS = ["BTC", "ETH", "BNB", "SOL", "LINK", "XRP", "AVAX", "HYPE", "SUI"]
SEEDS = {a: i + 11 for i, a in enumerate(ASSETS)}

@st.cache_data
def make_demo_data(asset: str, periods: int = 240) -> pd.DataFrame:
    """Create deterministic DEMO prices. These are not real market prices."""
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

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
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
    points = 0
    reasons = []
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
            reasons.append("RSI élevé : mouvement potentiellement déjà étendu.")
        elif row["RSI14"] <= 30:
            reasons.append("RSI faible : mouvement potentiellement déjà étendu à la baisse.")
        else:
            reasons.append("RSI dans une zone intermédiaire.")
    label = "Biais positif" if points == 2 else "Biais négatif" if points == -2 else "Signaux mixtes"
    return label, reasons

st.title("📊 AI Trading Lab")
st.caption("Prototype éducatif — données synthétiques, aucune connexion à une plateforme, aucun ordre réel.")

with st.sidebar:
    st.header("Paramètres du laboratoire")
    asset = st.selectbox("Actif étudié", ASSETS)
    window = st.slider("Nombre de bougies affichées", 40, 240, 120, 20)
    st.divider()
    st.markdown("**Mode :** simulation pédagogique")
    st.warning("Les prix affichés sont artificiels. Ils ne représentent pas les cours actuels.")

data = add_indicators(make_demo_data(asset)).tail(window)
last = data.iloc[-1]
label, reasons = observation(last)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Actif", asset)
c2.metric("Prix DEMO", f"{last['Close']:,.4f}")
c3.metric("RSI (14)", f"{last['RSI14']:.1f}")
c4.metric("Observation", label)

st.subheader(f"Historique synthétique — {asset}")
st.line_chart(data[["Close", "EMA20", "EMA50"]], height=340)

left, right = st.columns([1, 1])
with left:
    st.subheader("Indicateurs")
    st.line_chart(data[["RSI14"]], height=190)
    st.line_chart(data[["MACD", "MACD_signal"]], height=190)
with right:
    st.subheader("Explication de l'agent")
    st.info("Cette conclusion est une démonstration de règles simples, pas une prévision.")
    for reason in reasons:
        st.write("• " + reason)
    st.subheader("État des données")
    st.write(f"- Bougies analysées : {len(data)}")
    st.write("- Intervalle artificiel : 15 minutes")
    st.write("- Source : générateur local déterministe")
    st.write("- Frais, liquidité et glissement : non modélisés dans ce prototype")

st.divider()
st.subheader("Univers de surveillance")
st.dataframe(pd.DataFrame({
    "Actif": ASSETS,
    "Données": ["Synthétiques"] * len(ASSETS),
    "Connexion réelle": ["Désactivée"] * len(ASSETS)
}), use_container_width=True, hide_index=True)

st.caption("Prochaine évolution : import de fichiers historiques, tests hors échantillon, frais simulés, journal des observations et tableau de performance.")
