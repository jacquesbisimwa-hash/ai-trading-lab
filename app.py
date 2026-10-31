import numpy as np
import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="AI Trading Lab", page_icon="📊", layout="wide")

ASSETS = ["BTC", "ETH", "BNB", "SOL", "LINK", "XRP", "AVAX", "HYPE", "SUI"]
SEEDS = {a: i + 11 for i, a in enumerate(ASSETS)}
STARTING_BALANCE = 10_000.0

@st.cache_data
def make_demo_data(asset, periods=240):
    rng = np.random.default_rng(SEEDS[asset])
    shocks = rng.normal(0.0002, 0.012, periods)
    starts = {"BTC":65000, "ETH":3200, "BNB":600, "SOL":150,
              "LINK":15, "XRP":0.55, "AVAX":35, "HYPE":25, "SUI":1.2}
    close = starts[asset] * np.exp(np.cumsum(shocks))
    dates = pd.date_range(end=pd.Timestamp.now().floor("15min"), periods=periods, freq="15min")
    return pd.DataFrame({"Close":close}, index=dates)

def add_indicators(df):
    d = df.copy()
    d["EMA20"] = d.Close.ewm(span=20, adjust=False).mean()
    d["EMA50"] = d.Close.ewm(span=50, adjust=False).mean()
    delta = d.Close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d["RSI14"] = 100 - 100 / (1 + rs)
    macd = d.Close.ewm(span=12, adjust=False).mean() - d.Close.ewm(span=26, adjust=False).mean()
    d["MACD"] = macd
    d["MACD_signal"] = macd.ewm(span=9, adjust=False).mean()
    return d

def get_client():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def login_screen(sb):
    st.title("📊 AI Trading Lab")
    st.caption("Prototype éducatif — données synthétiques, aucune connexion à une plateforme, aucun ordre réel.")
    st.info("Connecte-toi pour retrouver ton portefeuille virtuel et ton historique sauvegardés en ligne.")
    login_tab, signup_tab = st.tabs(["Connexion", "Créer un compte"])
    with login_tab:
        with st.form("login"):
            email = st.text_input("Adresse e-mail")
            password = st.text_input("Mot de passe", type="password")
            ok = st.form_submit_button("Se connecter")
        if ok:
            try:
                response = sb.auth.sign_in_with_password({"email":email.strip(), "password":password})
                st.session_state["user_id"] = str(response.user.id)
                st.session_state["user_email"] = response.user.email or email
                st.rerun()
            except Exception:
                st.error("Connexion impossible. Vérifie tes identifiants et la confirmation de ton adresse e-mail.")
    with signup_tab:
        with st.form("signup"):
            email2 = st.text_input("Adresse e-mail", key="signup_email")
            password2 = st.text_input("Mot de passe (8 caractères minimum)", type="password", key="signup_password")
            ok2 = st.form_submit_button("Créer mon compte")
        if ok2:
            if len(password2) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            else:
                try:
                    result = sb.auth.sign_up({"email":email2.strip(), "password":password2})
                    if result.session:
                        st.session_state["user_id"] = str(result.user.id)
                        st.session_state["user_email"] = result.user.email or email2
                        st.rerun()
                    else:
                        st.success("Compte créé. Confirme ton adresse e-mail, puis connecte-toi.")
                except Exception:
                    st.error("Inscription impossible. Vérifie l'adresse e-mail ou réessaie.")
    st.caption("Garde ton mot de passe privé. Ne le partage pas dans cette conversation.")

def load_portfolio(sb, uid):
    p = sb.table("paper_portfolios").select("cash_balance").eq("user_id", uid).execute()
    if p.data:
        cash = float(p.data[0]["cash_balance"])
    else:
        sb.table("paper_portfolios").insert({"user_id":uid, "cash_balance":STARTING_BALANCE}).execute()
        cash = STARTING_BALANCE
    t = sb.table("paper_trades").select("*").eq("user_id",uid).order("created_at",desc=True).execute()
    holdings = {a:0.0 for a in ASSETS}
    for row in reversed(t.data or []):
        q = float(row["quantity"])
        if row["operation"] == "Achat simulé":
            holdings[row["asset"]] += q
        else:
            holdings[row["asset"]] -= q
    return cash, holdings, t.data or []

def record_trade(sb, uid, cash, holdings, prices, asset, amount, operation):
    quantity = amount / prices[asset]
    if operation == "Achat simulé":
        if amount > cash:
            st.error("Solde virtuel insuffisant.")
            return
        new_cash = cash - amount
    else:
        if quantity > holdings[asset]:
            st.error("Quantité virtuelle détenue insuffisante.")
            return
        new_cash = cash + amount
    try:
        sb.table("paper_trades").insert({
            "user_id":uid, "asset":asset, "operation":operation,
            "quantity":quantity, "demo_price":prices[asset], "amount":amount
        }).execute()
        sb.table("paper_portfolios").update({
            "cash_balance":new_cash, "updated_at":pd.Timestamp.now(tz="UTC").isoformat()
        }).eq("user_id",uid).execute()
        st.rerun()
    except Exception:
        st.error("La sauvegarde a échoué. Vérifie les tables et les politiques RLS dans Supabase.")

st.title("📊 AI Trading Lab")
st.caption("Prototype éducatif — données synthétiques, aucune connexion à une plateforme, aucun ordre réel.")
st.warning("Tous les prix, soldes et résultats sont fictifs. Les opérations sont uniquement des exercices pédagogiques.")

try:
    sb = get_client()
except Exception:
    st.error("Secrets Supabase introuvables ou incorrects. Vérifie SUPABASE_URL et SUPABASE_KEY dans Streamlit.")
    st.stop()

if "user_id" not in st.session_state:
    login_screen(sb)
    st.stop()

uid = st.session_state["user_id"]
with st.sidebar:
    st.markdown("### Compte")
    st.write(st.session_state.get("user_email", "Utilisateur connecté"))
    if st.button("Se déconnecter"):
        st.session_state.pop("user_id", None)
        st.session_state.pop("user_email", None)
        st.rerun()
    st.divider()
    chart_asset = st.selectbox("Actif étudié", ASSETS)
    periods = st.slider("Bougies affichées", 40, 240, 120, 20)

try:
    cash, holdings, trades = load_portfolio(sb, uid)
except Exception:
    st.error("Impossible de lire les données. Vérifie les tables et les règles RLS de Supabase.")
    st.stop()

frames = {a:add_indicators(make_demo_data(a)) for a in ASSETS}
prices = {a:float(frames[a]["Close"].iloc[-1]) for a in ASSETS}
total = cash + sum(holdings[a]*prices[a] for a in ASSETS)
invested = total - cash
pnl = total - STARTING_BALANCE

st.subheader("Portefeuille virtuel sauvegardé en ligne")
a,b,c,d = st.columns(4)
a.metric("Solde disponible", f"{cash:,.2f} unités")
b.metric("Valeur des actifs", f"{invested:,.2f} unités")
c.metric("Valeur totale", f"{total:,.2f} unités")
d.metric("Résultat simulé", f"{pnl:+,.2f} unités", f"{pnl/STARTING_BALANCE*100:+.2f}%")
st.caption("Capital initial fictif : 10 000 unités de laboratoire. Ce n'est ni de l'argent réel ni une devise.")

st.markdown("#### Exercice de simulation")
c1,c2,c3 = st.columns(3)
with c1:
    trade_asset = st.selectbox("Actif", ASSETS, key="trade_asset")
with c2:
    amount = st.number_input("Montant fictif", min_value=1.0, value=500.0, step=50.0)
with c3:
    st.metric("Prix DEMO", f"{prices[trade_asset]:,.4f}")
buy,sell = st.columns(2)
with buy:
    if st.button("Simuler un achat", use_container_width=True):
        record_trade(sb,uid,cash,holdings,prices,trade_asset,amount,"Achat simulé")
with sell:
    if st.button("Simuler une vente", use_container_width=True):
        record_trade(sb,uid,cash,holdings,prices,trade_asset,amount,"Vente simulée")

st.divider()
chart = frames[chart_asset].tail(periods)
last = chart.iloc[-1]
st.subheader(f"Graphique pédagogique — {chart_asset}")
x1,x2,x3 = st.columns(3)
x1.metric("Prix DEMO", f"{last.Close:,.4f}")
x2.metric("RSI (14)", f"{last.RSI14:.1f}")
x3.metric("EMA20 / EMA50", "EMA20 au-dessus" if last.EMA20 > last.EMA50 else "EMA20 en dessous")
st.line_chart(chart[["Close","EMA20","EMA50"]], height=300)
left,right = st.columns(2)
with left:
    st.subheader("RSI")
    st.line_chart(chart[["RSI14"]], height=180)
with right:
    st.subheader("MACD")
    st.line_chart(chart[["MACD","MACD_signal"]], height=180)
st.info("Les indicateurs illustrent des notions d'analyse technique. Ils ne prédisent pas les prix et ne constituent pas des recommandations.")

st.divider()
st.subheader("Composition du portefeuille")
portfolio_rows = [{"Actif":a,"Quantité fictive":holdings[a],"Prix DEMO":prices[a],
                   "Valeur fictive":holdings[a]*prices[a]} for a in ASSETS]
st.dataframe(pd.DataFrame(portfolio_rows), use_container_width=True, hide_index=True)

st.subheader("Historique des simulations")
if trades:
    history = [{"Date/heure":t["created_at"],"Opération":t["operation"],"Actif":t["asset"],
                "Quantité fictive":float(t["quantity"]),"Prix DEMO":float(t["demo_price"]),
                "Montant fictif":float(t["amount"])} for t in trades]
    st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
else:
    st.info("Aucune opération simulée pour le moment. Tes opérations seront sauvegardées ici.")
