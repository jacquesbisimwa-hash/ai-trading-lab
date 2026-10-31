import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Trading Lab", page_icon="📊", layout="wide")

ASSETS = ["BTC", "ETH", "BNB", "SOL", "LINK", "XRP", "AVAX", "HYPE", "SUI"]
SEEDS = {a: i + 11 for i, a in enumerate(ASSETS)}
STARTING_BALANCE = 10_000.0
STORAGE_KEY = "ai_trading_lab_demo_v1"

# V2 component runs in the app page (not in a sandboxed iframe), so it can use
# the browser's localStorage. The first run restores saved data; later reruns save it.
LOCAL_STORAGE_JS = r"""
export default function(component) {
    const { data, setStateValue } = component;
    const key = "ai_trading_lab_demo_v1";
    if (!window.__aiTradingLabStorageInitialized) {
        window.__aiTradingLabStorageInitialized = true;
        try {
            const raw = window.localStorage.getItem(key);
            if (raw) {
                setStateValue("stored", JSON.parse(raw));
            } else {
                window.localStorage.setItem(key, JSON.stringify(data));
            }
        } catch (err) {
            setStateValue("storage_error", String(err));
        }
    } else {
        try {
            window.localStorage.setItem(key, JSON.stringify(data));
        } catch (err) {
            setStateValue("storage_error", String(err));
        }
    }
}
"""

browser_storage = st.components.v2.component(
    "ai_trading_lab_local_storage",
    js=LOCAL_STORAGE_JS,
)


def empty_portfolio():
    return {
        "cash": STARTING_BALANCE,
        "holdings": {a: 0.0 for a in ASSETS},
        "trades": [],
    }


def normalize_portfolio(value):
    """Validate browser data before using it in the educational simulation."""
    if not isinstance(value, dict):
        return empty_portfolio()
    try:
        cash = float(value.get("cash", STARTING_BALANCE))
        if not np.isfinite(cash) or cash < 0:
            return empty_portfolio()
        raw_holdings = value.get("holdings", {})
        holdings = {a: max(0.0, float(raw_holdings.get(a, 0.0))) for a in ASSETS}
        trades = value.get("trades", [])
        if not isinstance(trades, list):
            trades = []
        clean_trades = []
        for trade in trades[-500:]:
            if not isinstance(trade, dict) or trade.get("asset") not in ASSETS:
                continue
            if trade.get("operation") not in ("Achat simulé", "Vente simulée"):
                continue
            clean_trades.append({
                "created_at": str(trade.get("created_at", "")),
                "asset": trade["asset"],
                "operation": trade["operation"],
                "quantity": max(0.0, float(trade.get("quantity", 0))),
                "demo_price": max(0.0, float(trade.get("demo_price", 0))),
                "amount": max(0.0, float(trade.get("amount", 0))),
            })
        return {"cash": cash, "holdings": holdings, "trades": clean_trades}
    except (TypeError, ValueError, OverflowError):
        return empty_portfolio()


@st.cache_data
def make_demo_data(asset, periods=240):
    rng = np.random.default_rng(SEEDS[asset])
    shocks = rng.normal(0.0002, 0.012, periods)
    starts = {"BTC": 65000, "ETH": 3200, "BNB": 600, "SOL": 150,
              "LINK": 15, "XRP": 0.55, "AVAX": 35, "HYPE": 25, "SUI": 1.2}
    close = starts[asset] * np.exp(np.cumsum(shocks))
    dates = pd.date_range(end=pd.Timestamp.now().floor("15min"), periods=periods, freq="15min")
    return pd.DataFrame({"Close": close}, index=dates)


def add_indicators(df):
    d = df.copy()
    d["EMA20"] = d.Close.ewm(span=20, adjust=False).mean()
    d["EMA50"] = d.Close.ewm(span=50, adjust=False).mean()
    delta = d.Close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d["RSI14"] = 100 - 100 / (1 + rs)
    macd = d.Close.ewm(span=12, adjust=False).mean() - d.Close.ewm(span=26, adjust=False).mean()
    d["MACD"] = macd
    d["MACD_signal"] = macd.ewm(span=9, adjust=False).mean()
    return d


st.title("📊 AI Trading Lab")
st.caption("Prototype éducatif — données synthétiques, aucune connexion à une plateforme, aucun ordre réel.")
st.warning("Tous les prix, soldes et résultats sont fictifs. Les opérations sont uniquement des exercices pédagogiques.")

# Initial browser snapshot. The component reports a saved snapshot on its first run.
if "portfolio" not in st.session_state:
    st.session_state.portfolio = empty_portfolio()

snapshot = browser_storage(data=st.session_state.portfolio, key="atl_browser_storage")
if "stored" in snapshot and snapshot.stored and not st.session_state.get("storage_restored", False):
    st.session_state.portfolio = normalize_portfolio(snapshot.stored)
    st.session_state.storage_restored = True
    st.rerun()

if getattr(snapshot, "storage_error", None):
    st.error("Le stockage local du navigateur n'est pas accessible. Vérifie les réglages de Safari et quitte la navigation privée.")

portfolio = st.session_state.portfolio
cash = float(portfolio["cash"])
holdings = portfolio["holdings"]
trades = portfolio["trades"]

with st.sidebar:
    st.markdown("### Mode démonstration")
    st.caption("Aucun compte ni mot de passe requis.")
    chart_asset = st.selectbox("Actif étudié", ASSETS)
    periods = st.slider("Bougies affichées", 40, 240, 120, 20)
    if st.button("Réinitialiser le portefeuille", use_container_width=True):
        st.session_state.portfolio = empty_portfolio()
        st.session_state.storage_restored = True
        st.rerun()

frames = {a: add_indicators(make_demo_data(a)) for a in ASSETS}
prices = {a: float(frames[a]["Close"].iloc[-1]) for a in ASSETS}
total = cash + sum(holdings[a] * prices[a] for a in ASSETS)
invested = total - cash
pnl = total - STARTING_BALANCE

st.subheader("Portefeuille virtuel enregistré sur cet appareil")
a, b, c, d = st.columns(4)
a.metric("Solde disponible", f"{cash:,.2f} unités")
b.metric("Valeur des actifs", f"{invested:,.2f} unités")
c.metric("Valeur totale", f"{total:,.2f} unités")
d.metric("Résultat simulé", f"{pnl:+,.2f} unités", f"{pnl / STARTING_BALANCE * 100:+.2f}%")
st.caption("Capital initial fictif : 10 000 unités de laboratoire. Ce n'est ni de l'argent réel ni une devise.")

st.markdown("#### Exercice de simulation")
c1, c2, c3 = st.columns(3)
with c1:
    trade_asset = st.selectbox("Actif", ASSETS, key="trade_asset")
with c2:
    amount = st.number_input("Montant fictif", min_value=1.0, value=500.0, step=50.0)
with c3:
    st.metric("Prix DEMO", f"{prices[trade_asset]:,.4f}")

buy, sell = st.columns(2)
with buy:
    if st.button("Simuler un achat", use_container_width=True):
        if amount > cash:
            st.error("Solde virtuel insuffisant.")
        else:
            quantity = amount / prices[trade_asset]
            portfolio["cash"] = cash - amount
            portfolio["holdings"][trade_asset] += quantity
            portfolio["trades"].insert(0, {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "operation": "Achat simulé", "asset": trade_asset,
                "quantity": quantity, "demo_price": prices[trade_asset], "amount": amount,
            })
            st.session_state.portfolio = portfolio
            st.rerun()
with sell:
    if st.button("Simuler une vente", use_container_width=True):
        quantity = amount / prices[trade_asset]
        if quantity > holdings[trade_asset]:
            st.error("Quantité virtuelle détenue insuffisante.")
        else:
            portfolio["cash"] = cash + amount
            portfolio["holdings"][trade_asset] -= quantity
            portfolio["trades"].insert(0, {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "operation": "Vente simulée", "asset": trade_asset,
                "quantity": quantity, "demo_price": prices[trade_asset], "amount": amount,
            })
            st.session_state.portfolio = portfolio
            st.rerun()

st.divider()
chart = frames[chart_asset].tail(periods)
last = chart.iloc[-1]
st.subheader(f"Graphique pédagogique — {chart_asset}")
x1, x2, x3 = st.columns(3)
x1.metric("Prix DEMO", f"{last.Close:,.4f}")
x2.metric("RSI (14)", f"{last.RSI14:.1f}")
x3.metric("EMA20 / EMA50", "EMA20 au-dessus" if last.EMA20 > last.EMA50 else "EMA20 en dessous")
st.line_chart(chart[["Close", "EMA20", "EMA50"]], height=300)
left, right = st.columns(2)
with left:
    st.subheader("RSI")
    st.line_chart(chart[["RSI14"]], height=180)
with right:
    st.subheader("MACD")
    st.line_chart(chart[["MACD", "MACD_signal"]], height=180)
st.info("Les indicateurs illustrent des notions d'analyse technique. Ils ne prédisent pas les prix et ne constituent pas des recommandations.")

st.divider()
st.subheader("Composition du portefeuille")
portfolio_rows = [{"Actif": a, "Quantité fictive": holdings[a], "Prix DEMO": prices[a],
                   "Valeur fictive": holdings[a] * prices[a]} for a in ASSETS]
portfolio_df = pd.DataFrame(portfolio_rows)
held_df = portfolio_df[portfolio_df["Valeur fictive"] > 0].copy()

if not held_df.empty and invested > 0:
    held_df["Répartition (%)"] = held_df["Valeur fictive"] / invested * 100
    st.markdown("##### Répartition des actifs détenus")
    allocation = held_df.set_index("Actif")[["Valeur fictive"]].sort_values("Valeur fictive", ascending=False)
    st.bar_chart(allocation, height=230)
    allocation_display = held_df[["Actif", "Valeur fictive", "Répartition (%)"]].sort_values(
        "Valeur fictive", ascending=False
    )
    st.dataframe(allocation_display, use_container_width=True, hide_index=True)
else:
    st.info("La répartition apparaîtra ici après une première opération d'achat simulé.")

with st.expander("Afficher le détail des neuf actifs"):
    st.dataframe(portfolio_df, use_container_width=True, hide_index=True)

# Reconstitute the average simulated acquisition cost from the local trade history.
# Trades are stored newest-first, so replay them from oldest to newest.
average_cost = {a: 0.0 for a in ASSETS}
position_qty = {a: 0.0 for a in ASSETS}
for trade in reversed(trades):
    asset = trade["asset"]
    quantity = float(trade["quantity"])
    price = float(trade["demo_price"])
    if trade["operation"] == "Achat simulé":
        old_qty = position_qty[asset]
        new_qty = old_qty + quantity
        if new_qty > 0:
            average_cost[asset] = ((old_qty * average_cost[asset]) + (quantity * price)) / new_qty
        position_qty[asset] = new_qty
    elif trade["operation"] == "Vente simulée":
        position_qty[asset] = max(0.0, position_qty[asset] - quantity)
        if position_qty[asset] == 0:
            average_cost[asset] = 0.0

st.divider()
st.subheader("Performance fictive par actif")
performance_rows = []
for asset in ASSETS:
    qty = holdings[asset]
    if qty > 0:
        market_value = qty * prices[asset]
        cost_basis = qty * average_cost[asset]
        unrealized = market_value - cost_basis
        performance_rows.append({
            "Actif": asset,
            "Quantité virtuelle": qty,
            "Prix moyen d'achat": average_cost[asset],
            "Prix DEMO actuel": prices[asset],
            "Valeur fictive": market_value,
            "Gain/perte non réalisé(e)": unrealized,
        })

if performance_rows:
    performance_df = pd.DataFrame(performance_rows)
    st.dataframe(
        performance_df.style.format({
            "Quantité virtuelle": "{:,.6f}",
            "Prix moyen d'achat": "{:,.4f}",
            "Prix DEMO actuel": "{:,.4f}",
            "Valeur fictive": "{:,.2f}",
            "Gain/perte non réalisé(e)": "{:+,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
    total_unrealized = sum(row["Gain/perte non réalisé(e)"] for row in performance_rows)
    st.metric("Résultat non réalisé total", f"{total_unrealized:+,.2f} unités")
else:
    st.info("La performance par actif apparaîtra après une première opération d'achat simulé.")
st.caption("Le prix moyen est reconstitué à partir des achats et ventes simulés enregistrés. Tous les résultats restent fictifs.")

st.subheader("Historique des simulations")
if trades:
    history = [{"Date/heure": t["created_at"], "Opération": t["operation"], "Actif": t["asset"],
                "Quantité fictive": float(t["quantity"]), "Prix DEMO": float(t["demo_price"]),
                "Montant fictif": float(t["amount"])} for t in trades]
    history_df = pd.DataFrame(history)
    st.dataframe(history_df, use_container_width=True, hide_index=True)
    csv_data = history_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Exporter l'historique en CSV",
        data=csv_data,
        file_name="ai_trading_lab_historique.csv",
        mime="text/csv",
        use_container_width=True,
    )
else:
    st.info("Aucune opération simulée pour le moment.")

st.divider()
st.subheader("Sauvegarde et restauration")

backup_payload = {
    "app": "AI Trading Lab",
    "format_version": 1,
    "exported_at": datetime.now(timezone.utc).isoformat(),
    "portfolio": portfolio,
}
backup_bytes = json.dumps(backup_payload, ensure_ascii=False, indent=2).encode("utf-8")

st.download_button(
    "Télécharger une sauvegarde du portefeuille",
    data=backup_bytes,
    file_name="ai_trading_lab_sauvegarde.json",
    mime="application/json",
    use_container_width=True,
)

uploaded_backup = st.file_uploader(
    "Restaurer une sauvegarde JSON",
    type=["json"],
    help="Choisis un fichier de sauvegarde créé depuis AI Trading Lab.",
)
if uploaded_backup is not None:
    try:
        imported = json.loads(uploaded_backup.getvalue().decode("utf-8"))
        if imported.get("app") != "AI Trading Lab" or "portfolio" not in imported:
            st.error("Ce fichier ne semble pas être une sauvegarde AI Trading Lab valide.")
        else:
            restored = normalize_portfolio(imported["portfolio"])
            if st.button("Confirmer la restauration", type="primary"):
                st.session_state.portfolio = restored
                st.session_state.storage_restored = True
                st.success("Sauvegarde restaurée dans ce navigateur.")
                st.rerun()
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        st.error("Impossible de lire ce fichier. Vérifie qu'il s'agit d'une sauvegarde JSON valide.")

st.caption("Les données sont stockées dans le localStorage du navigateur utilisé. Elles ne sont pas synchronisées entre appareils. Télécharge régulièrement une sauvegarde JSON et conserve-la dans un endroit sûr. Évite la navigation privée et ne vide pas les données du site si tu souhaites conserver cet historique.")

st.divider()
st.subheader("Réinitialiser le portefeuille")
st.warning("Cette action efface le solde, les positions et l'historique enregistrés dans ce navigateur. Télécharge d'abord une sauvegarde JSON si tu souhaites les conserver.")
confirm_reset = st.checkbox("Je confirme vouloir réinitialiser tout le portefeuille virtuel.")
if st.button("Réinitialiser le portefeuille", type="secondary", disabled=not confirm_reset):
    st.session_state.portfolio = empty_portfolio()
    st.session_state.storage_restored = True
    st.success("Le portefeuille virtuel a été réinitialisé.")
    st.rerun()
