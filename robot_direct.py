streamlit>=1.40,<2
yfinance>=0.2.58,<2
pandas>=2.2,<4
altair>=5,<7

"""Robot A : 100 titres, TP/SL configurables, 100 % FICTIF, aucun acces au courtier.

Conserve portefeuille_fictif.json (positions et historique anciens).
Demontrer d'abord la robustesse en simulation avant d'envisager tout compte reel.
"""
import json
import os
import math
import threading
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st
import yfinance as yf

MODE_CLOUD = False  # Community Cloud gratuit : demonstration active uniquement pendant la visite
CAPITAL_INITIAL = 5000.0
FRAIS = 0.001
MAX_PAR_ACTION = 0.20  # max 1000 $ au prix d'achat par entreprise
FICHIER = Path(__file__).with_name("portefeuille_fictif.json")
FICHIER_PARAMETRES = Path(__file__).with_name("parametres_robot.json")
FICHIER_COTATIONS = Path(__file__).with_name("dernieres_cotations.json")
FICHIER_ETAT = Path(__file__).with_name("etat_robot.json")  # pause / reprise
NEW_YORK = ZoneInfo("America/New_York")
PARAMETRES_DEFAUT = {"take_profit": 10.0, "stop_loss": 5.0, "vente_mm": True}


UNIVERS_100 = {
    'MMM': '3M',
    'ABT': 'Abbott Laboratories',
    'ABBV': 'AbbVie',
    'ACN': 'Accenture',
    'ADBE': 'Adobe',
    'GOOGL': 'Alphabet (Google)',
    'MO': 'Altria',
    'AMZN': 'Amazon',
    'AMD': 'AMD',
    'AXP': 'American Express',
    'AMT': 'American Tower',
    'AMGN': 'Amgen',
    'AAPL': 'Apple',
    'AMAT': 'Applied Materials',
    'ANET': 'Arista Networks',
    'T': 'AT&T',
    'BRK-B': 'Berkshire Hathaway',
    'BLK': 'BlackRock',
    'BNY': 'BNY Mellon',
    'BA': 'Boeing',
    'BKNG': 'Booking Holdings',
    'BMY': 'Bristol Myers Squibb',
    'AVGO': 'Broadcom',
    'COF': 'Capital One',
    'CAT': 'Caterpillar',
    'SCHW': 'Charles Schwab',
    'CVX': 'Chevron',
    'CSCO': 'Cisco',
    'C': 'Citigroup',
    'KO': 'Coca-Cola',
    'CMCSA': 'Comcast',
    'COP': 'ConocoPhillips',
    'COST': 'Costco',
    'CVS': 'CVS Health',
    'DHR': 'Danaher',
    'DE': 'Deere',
    'DELL': 'Dell Technologies',
    'DUK': 'Duke Energy',
    'LLY': 'Eli Lilly',
    'EMR': 'Emerson',
    'XOM': 'ExxonMobil',
    'FDX': 'FedEx',
    'GEV': 'GE Vernova',
    'GD': 'General Dynamics',
    'GE': 'GE Aerospace',
    'GM': 'General Motors',
    'GILD': 'Gilead Sciences',
    'GS': 'Goldman Sachs',
    'HD': 'Home Depot',
    'INTC': 'Intel',
    'IBM': 'IBM',
    'INTU': 'Intuit',
    'ISRG': 'Intuitive Surgical',
    'JNJ': 'Johnson & Johnson',
    'JPM': 'JPMorgan Chase',
    'LRCX': 'Lam Research',
    'LIN': 'Linde',
    'LMT': 'Lockheed Martin',
    'LOW': "Lowe's",
    'MA': 'Mastercard',
    'MCD': "McDonald's",
    'MDT': 'Medtronic',
    'MRK': 'Merck',
    'META': 'Meta',
    'MU': 'Micron',
    'MSFT': 'Microsoft',
    'MDLZ': 'Mondelez',
    'MS': 'Morgan Stanley',
    'NFLX': 'Netflix',
    'NEE': 'NextEra Energy',
    'NVDA': 'Nvidia',
    'ORCL': 'Oracle',
    'PLTR': 'Palantir',
    'PANW': 'Palo Alto Networks',
    'PEP': 'PepsiCo',
    'PFE': 'Pfizer',
    'PM': 'Philip Morris',
    'PG': 'Procter & Gamble',
    'QCOM': 'Qualcomm',
    'RTX': 'RTX',
    'CRM': 'Salesforce',
    'SNDK': 'Sandisk',
    'NOW': 'ServiceNow',
    'SO': 'Southern Company',
    'SBUX': 'Starbucks',
    'TMUS': 'T-Mobile US',
    'TSLA': 'Tesla',
    'TXN': 'Texas Instruments',
    'BAC': 'Bank of America',
    'TMO': 'Thermo Fisher',
    'USB': 'U.S. Bancorp',
    'UBER': 'Uber',
    'UNP': 'Union Pacific',
    'UPS': 'UPS',
    'UNH': 'UnitedHealth',
    'VZ': 'Verizon',
    'V': 'Visa',
    'WMT': 'Walmart',
    'DIS': 'Walt Disney',
    'WFC': 'Wells Fargo',
}

st.set_page_config(page_title="Robot A - Trading fictif", layout="wide", initial_sidebar_state="expanded")

# -----------------------------------------------------------------------------
# THEME MARKET TERMINAL — présentation uniquement, aucune logique de trading touchée
# L'identité visuelle fonctionne même sans le fichier .streamlit/config.toml.
# Les couleurs natives de Streamlit (graphiques, tableaux, menus) seront plus
# cohérentes si vous installez aussi .streamlit/config.toml du pack.
# -----------------------------------------------------------------------------
CSS_FINANCE = r"""
<style>
:root {
  --mt-bg:#080F1E;
  --mt-card:#111E31;
  --mt-border:rgba(143,180,215,.18);
  --mt-text:#EBF4FF;
  --mt-muted:#9CAFC5;
  --mt-accent:#37D6AC;
  --mt-blue:#64AFFF;
}
/* Fond trading / fintech : halos, quadrillage discret, aucune image externe */
[data-testid="stAppViewContainer"] {
  background-color:var(--mt-bg) !important;
  background-image:
    radial-gradient(ellipse 60% 40% at 80% 2%,rgba(25,157,137,.16),transparent 75%),
    radial-gradient(ellipse 50% 40% at 16% 88%,rgba(55,108,190,.12),transparent 78%),
    linear-gradient(rgba(93,143,181,.042) 1px, transparent 1px),
    linear-gradient(90deg,rgba(93,143,181,.042) 1px, transparent 1px) !important;
  background-size:auto,auto,52px 52px,52px 52px !important;
}
[data-testid="stHeader"] {
  background:rgba(8,15,30,.80) !important;
  backdrop-filter:blur(14px);
  border-bottom:1px solid rgba(100,140,172,.10);
}
/* Colonne gauche : cockpit de réglages */
[data-testid="stSidebar"] > div:first-child,
section[data-testid="stSidebar"] {
  background:linear-gradient(180deg,#0C1729 0%,#0A1423 100%) !important;
  border-right:1px solid rgba(77,127,171,.25) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {color:#EDF6FF !important;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color:#A6BAD0 !important;
}
/* Typographie et respiration */
[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3 {letter-spacing:-.025em;}
[data-testid="stAppViewContainer"] h1 {
  font-weight:750 !important;
  font-size:clamp(1.65rem,2.5vw,2.65rem) !important;
  color:#F3F8FF !important;
}
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3 {color:#EAF3FF !important;}
[data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] {
  color:#A4B8CE !important;
}
.block-container {
  max-width:1650px !important;
  padding-top:2.5rem !important;
  padding-bottom:3rem !important;
}
/* Cartes de chiffres : effet "terminal financier" */
[data-testid="stMetric"] {
  background:linear-gradient(140deg,rgba(22,40,61,.95),rgba(13,25,43,.95)) !important;
  border:1px solid var(--mt-border) !important;
  border-radius:15px !important;
  padding:17px 20px 15px !important;
  min-height:112px;
  box-shadow:inset 0 1px rgba(255,255,255,.035),0 9px 26px rgba(0,0,0,.14);
  transition:border-color .2s ease,transform .2s ease;
}
[data-testid="stMetric"]:hover {
  border-color:rgba(55,214,172,.48) !important;
  transform:translateY(-1px);
}
[data-testid="stMetricLabel"] {color:#A8BDD3 !important;}
[data-testid="stMetricLabel"] p {
  color:#A8BDD3 !important;
  font-size:.88rem !important;
  font-weight:550 !important;
}
[data-testid="stMetricValue"] {color:#F3F9FF !important;}
[data-testid="stMetricValue"] div {
  color:#F3F9FF !important;
  font-variant-numeric:tabular-nums;
  letter-spacing:-.035em;
}
/* Navigation : onglets façon application bancaire */
.stTabs [data-baseweb="tab-list"] {
  background:rgba(15,30,50,.92) !important;
  border:1px solid var(--mt-border);
  border-radius:14px;
  padding:6px;
  gap:5px;
  overflow-x:auto;
}
.stTabs [data-baseweb="tab"] {
  background:transparent;
  color:#A8BED4;
  padding:10px 17px;
  border-radius:9px;
  font-weight:600;
}
.stTabs [data-baseweb="tab"]:hover {
  background:rgba(55,214,172,.09) !important;
  color:#D5F8ED !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  background:linear-gradient(90deg,rgba(32,159,132,.25),rgba(20,112,135,.17)) !important;
  color:#65F0CC !important;
  box-shadow:inset 0 0 0 1px rgba(55,214,172,.31);
}
.stTabs [data-baseweb="tab-highlight"] {background:transparent !important;}
.stTabs [data-baseweb="tab-border"] {background:transparent !important;}
/* Champs, formulaires et tableaux */
[data-testid="stForm"] {
  background:rgba(15,29,48,.72) !important;
  border:1px solid rgba(110,157,190,.20) !important;
  border-radius:14px !important;
  padding:15px 14px !important;
}
[data-testid="stDataFrame"],
[data-testid="stTable"] {
  border:1px solid var(--mt-border);
  border-radius:12px;
  overflow:hidden;
  box-shadow:0 10px 25px rgba(0,0,0,.1);
}
[data-baseweb="input"]>div,
[data-baseweb="select"]>div {
  border-radius:10px !important;
}
[data-testid="stButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
  background:linear-gradient(110deg,#1AAE8B,#148A91) !important;
  border:1px solid rgba(92,237,203,.28) !important;
  border-radius:10px !important;
  color:#F8FFFF !important;
  font-weight:700 !important;
  box-shadow:0 6px 18px rgba(9,116,99,.18);
}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
  filter:brightness(1.13);
}
[data-testid="stAlert"] {
  border-radius:12px !important;
  border-color:rgba(87,151,181,.27) !important;
}
hr {border-color:rgba(143,180,215,.17) !important;}
/* Bandeau de marque finance */
.market-identity {
  display:flex;align-items:center;gap:10px;
  font-size:.70rem;line-height:1.4;
  color:#AED5D0;letter-spacing:.16em;font-weight:800;
  margin:0 0 9px 2px;
  text-transform:uppercase;
}
.market-identity .market-dot {
  display:inline-block;width:9px;height:9px;border-radius:100%;
  background:#37D6AC;box-shadow:0 0 0 4px rgba(55,214,172,.11),0 0 15px rgba(55,214,172,.43);
}
.market-identity .market-separator {color:#4F6882;}
.market-identity .market-lite {color:#849DB8;letter-spacing:.12em;font-weight:600;}
@media (max-width:820px) {
  .block-container {padding-top:1.75rem !important;}
  [data-testid="stMetric"] {padding:13px !important;min-height:95px;}
  .stTabs [data-baseweb="tab"] {padding:8px 10px;}
}
</style>
"""
st.markdown(CSS_FINANCE, unsafe_allow_html=True)
st.markdown(
    '<div class="market-identity">'
    '<span class="market-dot"></span>'
    'MARKET TERMINAL <span class="market-separator">/</span>'
    '<span class="market-lite">PAPER TRADING · VIRTUAL PORTFOLIO</span>'
    '</div>', unsafe_allow_html=True
)
st.title("📊 Robot A — Tableau de bord")
st.info("100 % fictif : aucun compte bancaire ou courtier n'est connecte.")
st.warning("☁️ DÉMO GRATUITE : aucun traitement pendant la veille de l'application. "
           "Les opérations et paramètres enregistrés sur ce serveur peuvent DISPARAÎTRE "
           "après une mise en veille, un redémarrage ou un redéploiement. "
           "Ne pas utiliser pour un suivi continu ni comme seule sauvegarde.")
st.caption(
    "Cours Yahoo Finance parfois differes ou indisponibles. "
    "Le tableau se rafraichit environ toutes les 5 minutes pendant que la page reste ouverte. "
    "Les signaux reposent sur les dernieres seances quotidiennes terminees."
)


@st.cache_resource
def verrou_portefeuille():
    return threading.RLock()


def charger_parametres():
    """Lire les parametres enregistres ; ne jamais modifier le portefeuille."""
    if not FICHIER_PARAMETRES.exists():
        return PARAMETRES_DEFAUT.copy()
    try:
        source = json.loads(FICHIER_PARAMETRES.read_text(encoding="utf-8"))
        tp = float(source.get("take_profit", 10.0))
        sl = float(source.get("stop_loss", 5.0))
        mm = source.get("vente_mm", True)
        if not (math.isfinite(tp) and 1 <= tp <= 50 and math.isfinite(sl) and 1 <= sl <= 30
                and isinstance(mm, bool)):
            raise ValueError("parametres hors limites")
        return {"take_profit": tp, "stop_loss": sl, "vente_mm": mm}
    except (OSError, ValueError, TypeError, AttributeError):
        st.error("Parametres invalides. Aucun ordre fictif ne sera execute. ")
        st.error("Corrige ou supprime parametres_robot.json avant de reprendre.")
        st.stop()


def sauvegarder_parametres(parametres):
    tmp = FICHIER_PARAMETRES.with_suffix(".tmp")
    tmp.write_text(json.dumps(parametres, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FICHIER_PARAMETRES)


def charger_etat_robot():
    """Par precaution, un nouveau robot demarre en PAUSE jusqu'a confirmation.

    L'etat est independant du portefeuille, et survive aux redemarrages du PC.
    """
    if not FICHIER_ETAT.exists():
        return {"en_pause": True, "modifie_le": None}
    try:
        source = json.loads(FICHIER_ETAT.read_text(encoding="utf-8"))
        if not isinstance(source.get("en_pause"), bool):
            raise ValueError("pause invalide")
        return {"en_pause": source["en_pause"],
                "modifie_le": source.get("modifie_le")}
    except (OSError, TypeError, ValueError):
        # Comportement prudent : ne pas autoriser d'ordres si le fichier est illisible.
        return {"en_pause": True, "modifie_le": None}


def sauvegarder_etat_robot(en_pause):
    tmp = FICHIER_ETAT.with_suffix(".tmp")
    payload = {"en_pause": bool(en_pause),
               "modifie_le": datetime.now(NEW_YORK).isoformat(timespec="seconds")}
    with verrou_portefeuille():
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(FICHIER_ETAT)


def afficher_parametres():
    """Panneau lateral : securites, pause/reprise et seuils persistants."""
    p = charger_parametres()
    with st.sidebar:
        st.title("⚙️ Paramètres")
        st.caption("Robot A · 100 entreprises · simulation")
        st.divider()
        etat = charger_etat_robot()
        st.subheader("⏯️ Contrôle des ordres fictifs")
        if etat["en_pause"]:
            st.warning("EN PAUSE : aucun achat ni aucune vente fictive.")
            if st.button("▶️ Reprendre les ordres fictifs", type="primary",
                         use_container_width=True, key="reprendre_robot"):
                sauvegarder_etat_robot(False)
                st.rerun()
        else:
            st.success("ACTIF : achats et ventes fictifs autorisés si marché ouvert.")
            if st.button("⏸️ Mettre le robot en pause", use_container_width=True,
                         key="pause_robot"):
                sauvegarder_etat_robot(True)
                st.rerun()
        st.caption("En pause, les prix peuvent encore s'actualiser, mais "
                   "aucun ordre fictif n'est exécuté, même un Stop-Loss.")
        st.divider()
        st.subheader("Règles de vente")
        st.caption("Les seuils s'appliquent aux positions fictives existantes et futures.")
        with st.form("parametres_ventes"):
            take_profit = st.slider(
                "Take Profit — bénéfice net (%)", 1, 50, int(p["take_profit"]), 1
            )
            stop_loss = st.slider(
                "Stop-Loss — perte nette (%)", 1, 30, int(p["stop_loss"]), 1
            )
            vente_mm = st.checkbox(
                "Vendre si MM20 ≤ MM50", value=p["vente_mm"]
            )
            valide = st.form_submit_button(
                "💾 Enregistrer les paramètres", type="primary", use_container_width=True
            )
        if valide:
            nouveaux = {
                "take_profit": float(take_profit),
                "stop_loss": float(stop_loss),
                "vente_mm": bool(vente_mm),
            }
            sauvegarder_parametres(nouveaux)
            p = nouveaux
            st.success("Paramètres enregistrés !")
        st.caption(
            f"Actifs : TP +{p['take_profit']:g} % · SL -{p['stop_loss']:g} % · "
            f"Vente MM {'activée' if p['vente_mm'] else 'désactivée'}."
        )
        st.divider()
        st.subheader("Configuration du robot")
        st.write("**Capital de départ :** 5 000 $ fictifs")
        st.write("**Entreprises suivies :** 100")
        st.write("**Frais simulés :** 0,1 % par ordre")
        st.caption("Les pourcentages sont estimés après frais et ne garantissent pas un prix d'exécution.")
        st.info("Mode simulation : aucun compte bancaire ou courtier connecté.")
        st.divider()
        st.subheader("💾 Sauvegarde de cette démo")
        st.caption("Les fichiers du serveur gratuit ne sont pas permanents. "
                   "Télécharge une sauvegarde après tes essais.")
        if FICHIER.exists():
            st.download_button("⬇️ Exporter le portefeuille (JSON)",
                               data=FICHIER.read_bytes(),
                               file_name="portefeuille_demo_cloud.json",
                               mime="application/json", use_container_width=True,
                               key="export_portefeuille_demo")
    return p


def charger_portefeuille():
    if FICHIER.exists():
        try:
            donnees = json.loads(FICHIER.read_text(encoding="utf-8"))
            if not all(k in donnees for k in ("cash", "positions", "trades")):
                raise ValueError("champs manquants")
            donnees.setdefault("last_prices", {})
            donnees.setdefault("history", [])
            donnees.setdefault("attente_nouveau_signal", [])
            if not isinstance(donnees["attente_nouveau_signal"], list):
                raise ValueError("champ attente_nouveau_signal invalide")
            return donnees
        except (OSError, ValueError, TypeError):
            st.error("Portefeuille illisible : aucun ordre fictif. Restaurer la sauvegarde si necessaire.")
            st.stop()
    return {"cash": CAPITAL_INITIAL, "positions": {}, "trades": [],
            "last_prices": {}, "history": [], "attente_nouveau_signal": []}


def sauvegarder_portefeuille(donnees):
    temp = FICHIER.with_suffix(".tmp")
    temp.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(FICHIER)


def marche_ouvert(instant):
    # Horaire standard americain. La fraicheur de la cotation bloque les jours feries.
    return instant.weekday() < 5 and time(9, 30) <= instant.time() < time(16, 0)


def lire_lots(intervalle, periode):
    """Telechargement groupe, pour eviter 100 appels individuels."""
    resultat = {}
    tickers = list(UNIVERS_100)
    for debut in range(0, len(tickers), 20):
        lot = tickers[debut:debut + 20]
        try:
            brut = yf.download(
                tickers=lot, period=periode, interval=intervalle,
                group_by="ticker", auto_adjust=True,
                progress=False, threads=False, timeout=15, prepost=False
            )
            if brut is None or brut.empty:
                continue
            for symbole in lot:
                try:
                    if not isinstance(brut.columns, pd.MultiIndex):
                        continue
                    historique = brut[symbole].copy()
                    historique = historique.dropna(subset=["Close"])
                    if not historique.empty:
                        resultat[symbole] = historique
                except (KeyError, ValueError, TypeError):
                    continue
        except Exception:
            # Interdire toute operation sur les titres sans donnees fiables.
            continue
    return resultat


@st.cache_data(ttl=1800, show_spinner=False)
def donnees_journalieres():
    return lire_lots("1d", "6mo")


@st.cache_data(ttl=240, show_spinner=False)
def donnees_intraday():
    return lire_lots("5m", "1d")


def calcule_signaux(daily, recent, maintenant, ouvert):
    lignes = []
    graphiques = {}
    etats = {}
    for symbole, nom in UNIVERS_100.items():
        df = daily.get(symbole)
        if df is None or df.empty:
            continue
        try:
            dates = pd.to_datetime(df.index)
            termine = df[dates.date < maintenant.date()].copy()
            if len(termine) < 50:
                continue
            termine["MM20"] = termine["Close"].rolling(20).mean()
            termine["MM50"] = termine["Close"].rolling(50).mean()
            mm20 = float(termine["MM20"].iloc[-1])
            mm50 = float(termine["MM50"].iloc[-1])
            if not (math.isfinite(mm20) and math.isfinite(mm50) and mm50 > 0):
                continue
            signal = "ACHAT" if mm20 > mm50 else "VENTE"
            ecart = (mm20 / mm50 - 1) * 100
            dernier_prix = float(df["Close"].iloc[-1])
            heure_cours = df.index[-1]
            cote_recente = False
            intraday = recent.get(symbole)
            if intraday is not None and not intraday.empty:
                candidat = float(intraday["Close"].iloc[-1])
                horaire = pd.Timestamp(intraday.index[-1])
                if horaire.tzinfo is not None:
                    heure_ny = horaire.tz_convert(NEW_YORK).to_pydatetime()
                    minutes = (maintenant - heure_ny).total_seconds() / 60
                    cote_recente = (ouvert and heure_ny.date() == maintenant.date()
                                   and 0 <= minutes <= 30)
                    if math.isfinite(candidat) and candidat > 0:
                        dernier_prix = candidat
                        heure_cours = horaire
            if not (math.isfinite(dernier_prix) and dernier_prix > 0):
                continue
            etats[symbole] = {"nom": nom, "prix": dernier_prix, "signal": signal,
                              "ecart": ecart, "frais_donnees": cote_recente}
            # OHLC pour chandeliers + volumes + moyennes mobiles.
            colonnes = ["Open", "High", "Low", "Close", "MM20", "MM50"]
            if "Volume" in termine.columns:
                colonnes.append("Volume")
            graphiques[symbole] = termine[colonnes].tail(110)
            try:
                h = pd.Timestamp(heure_cours)
                date_affichee = (h.tz_convert(NEW_YORK) if h.tzinfo else h).strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                date_affichee = "Indisponible"
            lignes.append({"Symbole": symbole, "Entreprise": nom,
                           "Cours disponible ($)": round(dernier_prix, 2),
                           "MM20 ($)": round(mm20, 2), "MM50 ($)": round(mm50, 2),
                           "Ecart (%)": round(ecart, 2), "Signal": signal,
                           "Cotation assez recente pour simuler": "Oui" if cote_recente else "Non",
                           "Heure dernier cours": date_affichee})
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return lignes, graphiques, etats


def ordre_simule(trades, maintenant, sens, symbole, quantite, prix, frais, pnl=None,
                  motif=None):
    trades.append({
        "Heure NY": maintenant.strftime("%Y-%m-%d %H:%M"),
        "Operation": sens, "Action": symbole, "Quantite": quantite,
        "Prix ($)": round(prix, 2), "Frais ($)": round(frais, 2),
        "Resultat realise ($)": round(pnl, 2) if pnl is not None else None,
        "Motif": motif,
    })


def appliquer_ordres_fictifs(portefeuille, etats, maintenant, parametres):
    """Simulations uniquement, VENTES avant ACHATS, sans levier ni double achat.

    TP/SL se calculent sur la rentabilite estimee, frais compris.
    Apres TP ou SL, attendre un signal baissier puis un nouveau signal haussier
    avant de reprendre cette entreprise : evite de revendre et racheter en boucle.
    """
    ajouts = []
    attente = set(portefeuille.get("attente_nouveau_signal", []))
    # Une phase baissiere remet a zero le verrou de re-entree.
    for symbole in list(attente):
        info = etats.get(symbole)
        if info and info["signal"] == "VENTE":
            attente.discard(symbole)

    # VENTES : signal ou resultat net de frais ; jamais sur cours trop ancien.
    for symbole, position in list(portefeuille["positions"].items()):
        info = etats.get(symbole)
        if not info or not info["frais_donnees"]:
            continue
        quantite = int(position.get("qty", 0))
        prix = float(info["prix"])
        cout = float(position.get("cost", 0))
        if quantite <= 0 or prix <= 0 or cout <= 0:
            continue
        frais_vente = quantite * prix * FRAIS
        recette = quantite * prix - frais_vente
        resultat_net_pct = ((recette - cout) / cout) * 100
        # Priorite au stop-loss ; si le signal est egalement baissier, on bloque
        # le rachat jusqu'a un nouveau cycle haussier de toute facon.
        motif = None
        if resultat_net_pct <= -parametres["stop_loss"]:
            motif = "STOP-LOSS"
        elif resultat_net_pct >= parametres["take_profit"]:
            motif = "TAKE PROFIT"
        elif parametres["vente_mm"] and info["signal"] == "VENTE":
            motif = "MM20/MM50"
        if motif is None:
            continue
        pnl = recette - cout
        portefeuille["cash"] += recette
        del portefeuille["positions"][symbole]
        ordre_simule(ajouts, maintenant, "VENTE", symbole, quantite, prix,
                     frais_vente, pnl, motif)
        if motif in ("STOP-LOSS", "TAKE PROFIT"):
            attente.add(symbole)

    # ACHATS : plusieurs entreprises si solde suffisant, jamais une position en double.
    candidats = [(s, x) for s, x in etats.items()
                 if x["frais_donnees"] and x["signal"] == "ACHAT"
                 and s not in attente
                 and s not in portefeuille["positions"] and x["prix"] > 0]
    candidats.sort(key=lambda item: (-item[1]["ecart"], item[0]))
    plans = {s: 0 for s, _ in candidats}
    cash = float(portefeuille["cash"])
    plafond = CAPITAL_INITIAL * MAX_PAR_ACTION
    for _ in range(2000):
        trouve = False
        for symbole, info in candidats:
            prix = info["prix"]
            cout_unitaire = prix * (1 + FRAIS)
            if (cash + 1e-8 >= cout_unitaire and
                (plans[symbole] + 1) * cout_unitaire <= plafond + 1e-8):
                plans[symbole] += 1
                cash -= cout_unitaire
                trouve = True
        if not trouve:
            break

    for symbole, info in candidats:
        qty = plans[symbole]
        if qty <= 0:
            continue
        prix = info["prix"]
        brut = qty * prix
        frais = brut * FRAIS
        total = brut + frais
        portefeuille["cash"] -= total
        portefeuille["positions"][symbole] = {"qty": qty, "cost": total}
        ordre_simule(ajouts, maintenant, "ACHAT", symbole, qty, prix, frais,
                     motif="MM20 > MM50")
    if -1e-7 < portefeuille["cash"] < 0:
        portefeuille["cash"] = 0.0
    assert portefeuille["cash"] >= -1e-7, "Cash negatif — ordre annule"
    portefeuille["attente_nouveau_signal"] = sorted(attente)
    portefeuille["trades"].extend(ajouts)
    return ajouts

# =============================================================================
# Analyse visuelle / statistiques (AUCUNE modification des regles de trading)
# =============================================================================

def preparer_historique(portefeuille):
    hist = pd.DataFrame(portefeuille.get("history", []))
    if hist.empty or not {"Date", "Valeur ($)"}.issubset(hist.columns):
        return pd.DataFrame(columns=["Date", "Valeur ($)"])
    hist["Date"] = pd.to_datetime(hist["Date"], utc=True, errors="coerce")
    hist["Valeur ($)"] = pd.to_numeric(hist["Valeur ($)"], errors="coerce")
    hist = hist.dropna(subset=["Date", "Valeur ($)"])
    hist = hist[hist["Valeur ($)"] > 0]
    return (hist.sort_values("Date")
            .drop_duplicates("Date", keep="last")
            .reset_index(drop=True))


def variation_historique(hist, jours):
    """Rendement depuis la valeur observee au moins N jours auparavant.

    Retourne None en cas d'historique insuffisant ; n'invente aucune mesure.
    """
    if len(hist) < 2:
        return None
    fin = hist["Date"].iloc[-1]
    cible = fin - pd.Timedelta(days=jours)
    debut_possible = hist.loc[hist["Date"] <= cible]
    if debut_possible.empty:
        return None
    point = debut_possible.iloc[-1]
    reference = float(point["Valeur ($)"])
    actuel = float(hist["Valeur ($)"].iloc[-1])
    if reference <= 0:
        return None
    return 100 * (actuel / reference - 1)


def statistiques_portefeuille(portefeuille):
    hist = preparer_historique(portefeuille)
    sorties = [t for t in portefeuille.get("trades", []) if t.get("Operation") == "VENTE"]
    resultats = [float(t.get("Resultat realise ($)") or 0) for t in sorties]
    frais_total = sum(float(t.get("Frais ($)") or 0)
                      for t in portefeuille.get("trades", []))
    drawdown = None
    if len(hist) >= 2:
        valeurs = hist["Valeur ($)"].astype(float)
        drawdown = float(((valeurs / valeurs.cummax()) - 1).min() * 100)
    return {
        "historique": hist,
        "drawdown": drawdown,
        "nb_ventes": len(sorties),
        "taux_reussite": (100 * sum(r > 0 for r in resultats) / len(resultats)) if resultats else None,
        "pnl_realise": sum(resultats),
        "frais_total": frais_total,
        "performance_1j": variation_historique(hist, 1),
        "performance_7j": variation_historique(hist, 7),
        "performance_30j": variation_historique(hist, 30),
    }


def montrer_chandeliers(df, jours):
    """Chandeliers OHLC Altair et lignes MM20 / MM50, base jour TERMINE."""
    courbes = df.tail(jours).copy()
    if courbes.empty or not {"Open", "High", "Low", "Close"}.issubset(courbes.columns):
        st.info("Pas assez de cours OHLC pour afficher les chandeliers.")
        return
    horodatage = pd.to_datetime(courbes.index, utc=True, errors="coerce")
    courbes["Date"] = horodatage.tz_convert(NEW_YORK).tz_localize(None)
    courbes = courbes.reset_index(drop=True)  # evite une collision du nom Date avec l'index
    courbes = courbes.dropna(subset=["Open", "High", "Low", "Close", "Date"])
    if courbes.empty:
        st.info("Cours incomplets pour les chandeliers.")
        return
    base = alt.Chart(courbes).encode(
        x=alt.X("Date:T", title="Séance (New York)", axis=alt.Axis(format="%d/%m")),
        tooltip=[
            alt.Tooltip("Date:T", title="Date", format="%d/%m/%Y"),
            alt.Tooltip("Open:Q", title="Ouverture", format=",.2f"),
            alt.Tooltip("High:Q", title="Plus haut", format=",.2f"),
            alt.Tooltip("Low:Q", title="Plus bas", format=",.2f"),
            alt.Tooltip("Close:Q", title="Clôture", format=",.2f"),
        ]
    )
    couleurs = alt.condition("datum.Close >= datum.Open", alt.value("#37D6AC"), alt.value("#FB7185"))
    meches = base.mark_rule(size=1.6).encode(
        y=alt.Y("Low:Q", title="Prix ($)", scale=alt.Scale(zero=False)),
        y2="High:Q", color=couleurs
    )
    bougies = base.mark_bar(size=7).encode(
        y=alt.Y("Open:Q", title="Prix ($)", scale=alt.Scale(zero=False)),
        y2="Close:Q", color=couleurs
    )
    mm20 = alt.Chart(courbes).mark_line(color="#60A5FA", strokeWidth=1.7).encode(
        x="Date:T", y=alt.Y("MM20:Q", scale=alt.Scale(zero=False)))
    mm50 = alt.Chart(courbes).mark_line(color="#FBBF24", strokeWidth=1.7).encode(
        x="Date:T", y=alt.Y("MM50:Q", scale=alt.Scale(zero=False)))
    graphique = alt.layer(meches, bougies, mm20, mm50).properties(height=390).interactive()
    st.altair_chart(graphique, use_container_width=True)
    st.caption("Vert : clôture ≥ ouverture · Rouge : clôture < ouverture · "
               "Bleu : MM20 · Jaune : MM50. Dernières séances terminées, pas de temps réel.")
    if "Volume" in courbes.columns and courbes["Volume"].notna().any():
        volumes = alt.Chart(courbes).mark_bar(color="#4F91C8", opacity=0.65).encode(
            x=alt.X("Date:T", title="Séance"),
            y=alt.Y("Volume:Q", title="Volume"),
            tooltip=[alt.Tooltip("Date:T", title="Date", format="%d/%m/%Y"), "Volume:Q"]
        ).properties(height=100)
        st.altair_chart(volumes, use_container_width=True)


def montrer_rendements_periodiques(hist, identifiant):
    st.subheader("🗓️ Historique par période")
    if len(hist) < 2:
        st.info("Il faut au moins deux observations de portefeuille.")
        return
    granularite = st.radio("Regrouper par", ["Jour", "Semaine", "Mois"],
                           horizontal=True, key=identifiant)
    pas = {"Jour": "D", "Semaine": "W-FRI", "Mois": "MS"}[granularite]
    groupe = (hist.set_index("Date")["Valeur ($)"]
              .resample(pas).last().dropna())
    if len(groupe) < 2:
        st.info(f"Pas assez de données pour comparer plusieurs périodes ({granularite.lower()}).")
        return
    synthese = pd.DataFrame({"Date": groupe.index,
                              "Valeur fin période ($)": groupe.values})
    synthese["Évolution ($)"] = synthese["Valeur fin période ($)"].diff()
    synthese["Rendement période (%)"] = synthese["Valeur fin période ($)"].pct_change() * 100
    synthese["Date"] = synthese["Date"].dt.tz_convert(NEW_YORK).dt.strftime("%d/%m/%Y")
    st.dataframe(synthese.tail(40).iloc[::-1].round(2), hide_index=True, use_container_width=True)
    st.caption("Valeur de la dernière observation disponible de chaque période. "
               "Les périodes sans suivi sont omises ; ce n'est pas une série de prix continus.")


# Les parametres sont ajustes manuellement dans le tableau, puis persistants.
PARAMETRES_ACTUELS = afficher_parametres()


def charger_cotations_cloud():
    """Lire l'etat du marche publie atomiquement par le worker autonome."""
    if not FICHIER_COTATIONS.exists():
        return [], {}, {}, None
    try:
        paquet = json.loads(FICHIER_COTATIONS.read_text(encoding="utf-8"))
        lignes = paquet.get("lignes", [])
        etats = paquet.get("etats", {})
        graphiques = {}
        for symbole, rows in paquet.get("graphiques", {}).items():
            if not rows:
                continue
            df = pd.DataFrame(rows)
            df["Date"] = pd.to_datetime(df["Date"], utc=True)
            df = df.set_index("Date")
            graphiques[symbole] = df
        mis_a_jour = pd.to_datetime(paquet.get("mis_a_jour"), utc=True)
        return lignes, graphiques, etats, mis_a_jour
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError):
        return [], {}, {}, None


@st.fragment(run_every="5m")
def mettre_a_jour():
    maintenant = datetime.now(NEW_YORK)
    ouvert = marche_ouvert(maintenant)
    if MODE_CLOUD:
        # En cloud, SEUL robot_worker.py peut simuler des transactions et sauver le portefeuille.
        lignes, graphiques, etats, maj_cotations = charger_cotations_cloud()
        if maj_cotations is None:
            st.warning("Le moteur autonome n'a pas encore publie de cotations. "
                       "Le tableau s'affichera apres son premier cycle.")
        else:
            age = (datetime.now(ZoneInfo("UTC")) - maj_cotations.to_pydatetime()).total_seconds() / 60
            st.caption(f"Derniere actualisation du moteur : {maj_cotations.tz_convert(NEW_YORK):%d/%m %H:%M} (New York)")
            if age > (20 if ouvert else 70):
                st.warning("Les cotations du serveur sont anciennes. Verifie les journaux du moteur.")
    else:
        with st.spinner("Chargement des cotations des 100 entreprises..."):
            daily = donnees_journalieres()
            intraday = donnees_intraday() if ouvert else {}
        lignes, graphiques, etats = calcule_signaux(daily, intraday, maintenant, ouvert)

    with verrou_portefeuille():
        portefeuille = charger_portefeuille()
        parametres = charger_parametres()
        en_pause = charger_etat_robot()["en_pause"]
        # Jamais d'ordre depuis le navigateur lorsque le worker serveur est actif.
        nouveaux = []
        if not MODE_CLOUD:
            for symbole, info in etats.items():
                portefeuille["last_prices"][symbole] = info["prix"]
            nouveaux = (appliquer_ordres_fictifs(portefeuille, etats, maintenant, parametres)
                        if ouvert and not en_pause else [])
        valeur_positions = sum(
            int(pos["qty"]) * float(portefeuille["last_prices"].get(
                symbole, float(pos["cost"]) / max(int(pos["qty"]), 1)))
            for symbole, pos in portefeuille["positions"].items()
        )
        total = float(portefeuille["cash"]) + valeur_positions
        gain = total - CAPITAL_INITIAL
        if not MODE_CLOUD:
            if (not portefeuille["history"] or
                portefeuille["history"][-1].get("Date") != maintenant.isoformat(timespec="minutes")):
                portefeuille["history"].append({
                    "Date": maintenant.isoformat(timespec="minutes"), "Valeur ($)": round(total, 2)})
            portefeuille["history"] = portefeuille["history"][-20000:]
            sauvegarder_portefeuille(portefeuille)

    if en_pause:
        st.warning("⏸️ ROBOT EN PAUSE — les cotations restent consultables, mais aucun ordre fictif n'est envoyé, y compris les ventes de protection.")
    else:
        st.success("▶️ Robot actif en mode simulation : les règles d'achat et de vente sont autorisées pendant la séance.")
    st.caption(
        "Heure New York : " + maintenant.strftime("%d/%m/%Y %H:%M") +
        (" | Horaires habituels ouverts" if ouvert else " | Marché fermé : aucun ordre fictif")
    )

    tab_vue, tab_scanner, tab_positions, tab_historique, tab_stats = st.tabs([
        "🏠 Vue d'ensemble", "🔎 Scanner 100 actions", "💼 Mes positions",
        "📋 Historique", "📊 Statistiques"
    ])
    stats = statistiques_portefeuille(portefeuille)

    with tab_vue:
        st.subheader("Vue d'ensemble du portefeuille")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valeur du portefeuille", f"{total:,.2f} $")
        c2.metric("Gain / perte", f"{gain:+,.2f} $", f"{gain / CAPITAL_INITIAL:+.2%}")
        c3.metric("Argent disponible", f"{portefeuille['cash']:,.2f} $")
        c4.metric("Opérations fictives", len(portefeuille["trades"]))
        c5, c6, c7 = st.columns(3)
        c5.metric("Actions analysées", len(lignes))
        c6.metric("Signaux d'achat", sum(x["Signal"] == "ACHAT" for x in lignes))
        c7.metric("Positions détenues", len(portefeuille["positions"]))
        st.caption("Rendement total depuis le capital de départ : "
                   f"{100 * gain / CAPITAL_INITIAL:+.2f} %. Les autres rendements "
                   "sont dans l'onglet Statistiques.")

        if len(lignes) < 100:
            st.warning(f"Données complètes pour {len(lignes)} actions sur 100. Les autres ne seront pas négociées fictivement.")
        if nouveaux:
            st.success(f"{len(nouveaux)} opération(s) fictive(s) enregistrée(s) à cette actualisation.")
        if ouvert:
            st.caption(
                f"{sum(x['frais_donnees'] for x in etats.values())} cotation(s) assez récentes "
                "pour autoriser une simulation d'ordre."
            )

        st.subheader("📈 Évolution du portefeuille fictif")
        historique = stats["historique"].copy()
        if len(historique) >= 2:
            historique["Heure NY"] = historique["Date"].dt.tz_convert(NEW_YORK)
            mini = float(historique["Valeur ($)"].min())
            maxi = float(historique["Valeur ($)"].max())
            marge = max((maxi - mini) * 0.2, 2.0)
            graph = (alt.Chart(historique).mark_line(point=True, color="#37D6AC").encode(
                x=alt.X("Heure NY:T", title="Date et heure New York"),
                y=alt.Y("Valeur ($):Q", title="Portefeuille ($)",
                        scale=alt.Scale(domain=[max(0.0, mini-marge), maxi+marge], zero=False)),
                tooltip=[alt.Tooltip("Heure NY:T"), alt.Tooltip("Valeur ($):Q", format=",.2f")]
            ).properties(height=330).interactive())
            st.altair_chart(graph, use_container_width=True)
        else:
            st.caption("Le graphique se construira après plusieurs actualisations du robot.")

    with tab_scanner:
        st.subheader("🏆 Classement et scanner des 100 entreprises")
        st.caption("Classement technique fondé sur l'écart MM20/MM50. "
                   "Un score élevé ne garantit pas une hausse future.")
        classement = sorted(lignes, key=lambda x: (-x["Ecart (%)"], x["Symbole"]))
        rangs = {x["Symbole"]: rang for rang, x in enumerate(classement, 1)}
        c_filtre, c_tri = st.columns(2)
        with c_filtre:
            filtre = st.radio("Signaux", ["Tous", "ACHAT", "VENTE"], horizontal=True)
        with c_tri:
            tri = st.selectbox("Trier par", ["Force de tendance ↓", "Force de tendance ↑", "Nom A-Z"])
        recherche = st.text_input("Rechercher une entreprise / un ticker", placeholder="Tesla, Nvidia, AMD...")
        affichees = [x.copy() for x in lignes
                    if (filtre == "Tous" or x["Signal"] == filtre)
                    and (not recherche or recherche.lower() in x["Entreprise"].lower()
                         or recherche.upper() in x["Symbole"])]
        for x in affichees:
            x["Rang MM20/MM50"] = rangs[x["Symbole"]]
            x["Position fictive"] = int(portefeuille["positions"].get(x["Symbole"], {}).get("qty", 0))
        if tri == "Force de tendance ↓":
            affichees.sort(key=lambda x: (-x["Ecart (%)"], x["Symbole"]))
        elif tri == "Force de tendance ↑":
            affichees.sort(key=lambda x: (x["Ecart (%)"], x["Symbole"]))
        else:
            affichees.sort(key=lambda x: x["Entreprise"].lower())
        cols_tableau = ["Rang MM20/MM50", "Symbole", "Entreprise", "Cours disponible ($)",
                        "MM20 ($)", "MM50 ($)", "Ecart (%)", "Signal",
                        "Cotation assez recente pour simuler", "Heure dernier cours", "Position fictive"]
        st.dataframe(pd.DataFrame(affichees, columns=cols_tableau),
                     hide_index=True, use_container_width=True, height=440)
        st.subheader("🕯️ Graphique des actions")
        symboles = [x["Symbole"] for x in affichees if x["Symbole"] in graphiques]
        if not symboles:
            symboles = list(graphiques.keys())
        if symboles:
            choix = st.selectbox("Entreprise", symboles, key="action_chart",
                                 format_func=lambda ticker: f"{UNIVERS_100[ticker]} ({ticker})")
            type_graph = st.radio("Affichage", ["Chandeliers japonais", "Courbes MM20/MM50"],
                                  horizontal=True, key="chart_kind")
            nb_jours = st.select_slider("Nombre de séances", options=[20, 50, 100],
                                       value=50, key="chart_days")
            if type_graph == "Chandeliers japonais":
                montrer_chandeliers(graphiques[choix], nb_jours)
            else:
                st.line_chart(graphiques[choix][["Close", "MM20", "MM50"]].tail(nb_jours),
                              use_container_width=True)
                st.caption("Données des séances terminées uniquement.")
        else:
            st.info("Aucun cours exploitable pour le graphique.")

    with tab_positions:
        st.subheader("💼 Positions et gains / pertes par entreprise")
        profits_realises = {}
        for trade in portefeuille["trades"]:
            symbole = trade.get("Action")
            if trade.get("Operation") == "VENTE":
                profits_realises[symbole] = profits_realises.get(symbole, 0.0) + float(trade.get("Resultat realise ($)") or 0)
        bilan = []
        for symbole, pos in portefeuille["positions"].items():
            quantite = int(pos.get("qty", 0))
            cout = float(pos.get("cost", 0))
            prix = portefeuille["last_prices"].get(symbole)
            valeur = quantite * float(prix) if prix is not None else cout
            bilan.append({
                "Entreprise": UNIVERS_100.get(symbole, symbole),
                "Symbole": symbole,
                "Quantité": quantite,
                "Prix actuel approx. ($)": round(float(prix or 0), 2),
                "Valeur position ($)": round(valeur, 2),
                "Gain/perte latent ($)": round(valeur - cout, 2),
                "Gain/perte réalisé ($)": round(profits_realises.get(symbole, 0), 2),
            })
        if bilan:
            st.dataframe(pd.DataFrame(bilan), hide_index=True, use_container_width=True)
        else:
            st.write("Aucune action détenue pour le moment.")

    with tab_historique:
        st.subheader("📋 Historique des transactions fictives")
        if portefeuille["trades"]:
            st.dataframe(pd.DataFrame(portefeuille["trades"][::-1]), hide_index=True, use_container_width=True)
        else:
            st.write("Aucune transaction pour le moment.")
        st.caption("Les achats et ventes historiques restent sauvegardés dans portefeuille_fictif.json.")
        montrer_rendements_periodiques(stats["historique"], "hist_group_historique")

    with tab_stats:
        st.subheader("📊 Statistiques avancées du portefeuille")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rendement total", f"{gain / CAPITAL_INITIAL * 100:+.2f} %")
        m2.metric("Drawdown maximal observé",
                  f"{stats['drawdown']:.2f} %" if stats["drawdown"] is not None else "—")
        m3.metric("Taux de ventes gagnantes",
                  f"{stats['taux_reussite']:.1f} %" if stats["taux_reussite"] is not None else "—")
        m4.metric("Frais cumulés", f"{stats['frais_total']:,.2f} $")
        m5, m6 = st.columns(2)
        m5.metric("Ventes effectuées", stats["nb_ventes"])
        m6.metric("Résultat réalisé des ventes", f"{stats['pnl_realise']:+,.2f} $")
        st.caption("Taux de réussite : ventes avec résultat net positif / nombre de ventes. "
                   "Le drawdown est calculé seulement sur les valeurs du portefeuille enregistrées, "
                   "pas sur toutes les fluctuations réelles du marché.")
        st.subheader("📅 Rendements sur différentes durées")
        p1, p7, p30 = st.columns(3)
        def affichage_perf(x):
            return "— (historique insuffisant)" if x is None else f"{x:+.2f} %"
        p1.metric("Sur 1 jour", affichage_perf(stats["performance_1j"]))
        p7.metric("Sur 7 jours", affichage_perf(stats["performance_7j"]))
        p30.metric("Sur 30 jours", affichage_perf(stats["performance_30j"]))
        st.caption("Les durées sont calculées depuis le dernier point enregistré. "
                   "Les périodes sans données ne sont pas estimées.")
        montrer_rendements_periodiques(stats["historique"], "hist_group_stats")

    st.caption(
        "Simulation approximative : cours potentiellement différés, frais simulés de 0,1 % "
        "à l'achat et à la vente. Les TP/SL ne garantissent aucun prix d'exécution. " +
        ("En mode cloud, les simulations sont gerees par le moteur serveur, meme navigateur ferme. "
         if MODE_CLOUD else "Démo Community Cloud : navigateur ouvert pour actualiser et fichiers temporaires. ") +
        "Le bouton Pause suspend aussi les ventes de protection : "
        "ne pas utiliser le système comme un outil de protection financière réelle."
    )


mettre_a_jour()

ROBOT A — ESSAI GRATUIT SUR STREAMLIT COMMUNITY CLOUD

MODELE : démonstration 100 % fictive sans aucun courtier connecté.
La version cloud gratuite sert à tester l'ouverture du tableau sur PC/téléphone.
Elle ne garantit PAS une surveillance continue avec PC éteint : lorsque
l'application dort (12 heures sans trafic selon Streamlit), les mises à jour
et les simulations s'arrêtent. Elles reprennent lorsque la page est ouverte.

IMPORTANT : LES DONNEES LOCALES CLOUD PEUVENT ETRE EFFACEES.
Le portefeuille sur Streamlit Community Cloud est distinct de celui sur ton PC.
N'envoie jamais les fichiers portefeuille_fictif.json, parametres_robot.json,
etat_robot.json, secrets.toml, mots de passe ou identifiants bancaires sur GitHub.
La démo repart avec 5 000 $ fictifs, en PAUSE initiale. Pour réaliser des
transactions fictives pendant une séance, activer la reprise dans la barre latérale.
Lorsque l'application se met en veille, aucune opération n'est simulée.
Tu peux exporter une copie du portefeuille de démo depuis la barre latérale.

ETAPES :
1. Créer un compte sur https://github.com/ si nécessaire.
2. Créer un dépôt *PRIVE* "robot-a-demo".
3. Mettre les fichiers du contenu de ce dossier dans le dépôt :
   robot_direct.py, requirements.txt, .streamlit/config.toml, .gitignore.
   Ne mettre AUCUN fichier JSON de données personnelles/portefeuille.
4. Aller sur https://share.streamlit.io/ et se connecter avec GitHub.
   Autoriser l'accès au dépôt privé si demandé.
5. Créer une nouvelle application : sélectionner dépôt robot-a-demo,
   branche main et fichier principal robot_direct.py.
   Dans les paramètres avancés, choisir Python 3.12 par compatibilité.
6. Déployer, puis consulter l'URL HTTPS .streamlit.app depuis le téléphone.
7. Garder le mode pause au début; vérifier les 100 actions et les graphiques.

Si tu veux un jour des transactions fictives réellement continues et durables,
il faudra une tâche serveur indépendante et une base de données persistante.
Ton PC et ta clé USB restent les sauvegardes de référence.
