"""Futures Desk — animated Streamlit workspace for Binance USDⓈ-M Futures Demo."""

from __future__ import annotations

import html
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from trading_bot.client import BinanceFuturesTestnetClient
from trading_bot.exceptions import BinanceAPIError, NetworkError, TradingBotError, ValidationError
from trading_bot.logging_config import configure_logging
from trading_bot.orders import OrderService

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "logs" / "bot.log"
load_dotenv(ROOT / ".env")
configure_logging(LOG_PATH, "INFO")
LOGGER = logging.getLogger("trading_bot.ui")

st.set_page_config(
    page_title="Futures Desk · Binance Demo",
    page_icon="⌁",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAV = ["Overview", "Trade terminal", "Activity", "Settings"]
NAV_LABELS = {
    "Overview": "01   Overview",
    "Trade terminal": "02   Trade terminal",
    "Activity": "03   Activity ledger",
    "Settings": "04   Settings",
}

st.session_state.setdefault("page", "Overview")
st.session_state.setdefault("session_orders", [])
st.session_state.setdefault("account_config", None)
st.session_state.setdefault("connection_verified", False)
st.session_state.setdefault("last_order", None)

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {
    --paper: #070B14;
    --paper-2: #0D1524;
    --paper-3: #090F1B;
    --ink: #E8F4FF;
    --ink-2: #B2C6D9;
    --mute: #71869E;
    --hair: rgba(111, 174, 205, .19);
    --accent: #00D9F5;
    --accent-d: #00AFCB;
    --hi: #B8FF3B;
    --ok: #B8FF3B;
    --bad: #FF4D83;
    --display: 'Space Grotesk', 'IBM Plex Sans', system-ui, sans-serif;
    --body: 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
    --mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    color-scheme: dark;
}

html, body, [data-testid="stAppViewContainer"] { background: var(--paper); }
.stApp { background: var(--paper); color: var(--ink); font-family: var(--body); -webkit-font-smoothing: antialiased; }
.stApp::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .045;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .7 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] { display: none; }
footer { visibility: hidden; }
.block-container { padding: 2.25rem 2.5rem 2.8rem; max-width: 1260px; }
::selection { background: var(--hi); color: var(--ink); }

[data-testid="stSidebar"] { background: var(--paper-3); border-right: 1px solid var(--hair); }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.3rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: var(--ink); }
[data-testid="stSidebar"] .stRadio > label { display: none; }
[data-testid="stSidebar"] .stRadio [role="radiogroup"] { gap: .32rem; }
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    border: 1px solid transparent; border-radius: 5px; padding: .48rem .55rem; transition: .2s ease;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover { background: rgba(255,255,255,.42); border-color: var(--hair); }
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:has(input:checked) { background: var(--paper-2); border-color: var(--hair); }

h1, h2, h3, h4, p, label, span, div { font-family: var(--body); }
.display, .display * { font-family: var(--display); }
.mono, code, pre, .mono * { font-family: var(--mono) !important; }

.brand { display:flex; align-items:center; gap:11px; padding: .15rem .1rem 1.05rem; border-bottom:1px solid var(--hair); margin-bottom:1.25rem; }
.brand-mark { width:37px; height:37px; background:var(--ink); color:var(--paper-2); display:grid; place-items:center; border-radius:6px; font-size:24px; line-height:1; transform:rotate(-4deg); }
.brand-name { font:700 20px/1 var(--display); letter-spacing:-.7px; }
.brand-sub { color:var(--mute); font:10px var(--mono); letter-spacing:.12em; margin-top:5px; text-transform:uppercase; }
.side-h { color:var(--mute); font:10px var(--mono); letter-spacing:.14em; text-transform:uppercase; margin:1.1rem 0 .5rem; }
.side-status { border:1px solid var(--hair); background:rgba(250,247,239,.58); border-radius:5px; padding:11px 12px; margin-top: .35rem; }
.status-row { display:flex; align-items:center; gap:8px; color:var(--ink-2); font-size:12px; margin:5px 0; }
.status-row b { margin-left:auto; color:var(--ink); font:600 10px var(--mono); letter-spacing:.05em; }
.dot { width:7px; height:7px; border-radius:50%; background:#A7A092; display:inline-block; flex:none; }
.dot.live { background:var(--ok); box-shadow:0 0 0 0 rgba(47,107,79,.35); animation:pulse 2s infinite; }
.dot.bad { background:var(--bad); }
.side-foot { border-top:1px solid var(--hair); margin-top:2rem; padding-top:1rem; color:var(--mute); font:10px/1.7 var(--mono); }

.masthead { display:flex; align-items:center; gap:18px; border-bottom:1px solid var(--hair); padding:0 0 13px; margin-bottom:30px; color:var(--mute); font:10px var(--mono); letter-spacing:.12em; text-transform:uppercase; }
.masthead .strong { color:var(--ink); font-weight:600; }
.masthead .grow { flex:1; }
.eyebrow { display:flex; gap:9px; align-items:center; color:var(--mute); font:10px var(--mono); letter-spacing:.14em; text-transform:uppercase; margin-bottom:17px; }
.pulse-dot { width:7px; height:7px; display:inline-block; border-radius:50%; background:var(--ok); box-shadow:0 0 0 0 rgba(47,107,79,.4); animation:pulse 1.8s infinite; }
.display { font:700 clamp(2.6rem,5vw,4.4rem)/.99 var(--display); letter-spacing:-.065em; color:var(--ink); margin:0 0 18px; }
.display .line { display:block; overflow:hidden; padding-bottom:4px; }
.display .line > span { display:inline-block; animation:reveal .85s cubic-bezier(.2,.8,.2,1) both; }
.display .line:nth-child(2) > span { animation-delay:.14s; }
.hl { color:var(--accent); position:relative; }
.lead { color:var(--ink-2); font-size:15px; line-height:1.7; max-width:570px; margin-bottom:23px; }

.hero-art { min-height:300px; border:1px solid var(--ink); background:#1B1A16; border-radius:7px; color:#F2EDE1; position:relative; overflow:hidden; padding:22px; box-shadow:8px 8px 0 rgba(22,20,15,.08); animation:rise .8s .18s both; }
.hero-art:before { content:""; position:absolute; width:280px; height:280px; border:1px solid rgba(245,213,71,.22); border-radius:50%; right:-55px; top:-125px; box-shadow:0 0 0 24px rgba(245,213,71,.025),0 0 0 52px rgba(245,213,71,.02); animation:orbit 18s linear infinite; }
.art-top { display:flex; justify-content:space-between; align-items:center; color:#B8B09D; font:10px var(--mono); letter-spacing:.13em; text-transform:uppercase; position:relative; z-index:1; }
.art-pill { border:1px solid rgba(245,213,71,.4); color:var(--hi); padding:5px 8px; border-radius:3px; font-size:9px; }
.art-big { font:700 35px/1 var(--display); letter-spacing:-1.8px; margin-top:26px; position:relative; z-index:1; }
.art-big span { color:var(--hi); }
.art-sub { color:#B8B09D; font:11px var(--mono); margin-top:8px; position:relative; z-index:1; }
.chart-wrap { position:relative; height:126px; margin-top:10px; }
.chart-wrap svg { width:100%; height:100%; overflow:visible; }
.chart-line { stroke:var(--hi); stroke-width:2; fill:none; stroke-linecap:round; stroke-linejoin:round; stroke-dasharray:600; stroke-dashoffset:600; animation:draw 2s .3s ease forwards; }
.chart-glow { fill:rgba(245,213,71,.07); }
.candle { transform-origin:bottom; animation:candle-in .65s both; }
.art-bottom { display:flex; justify-content:space-between; border-top:1px solid rgba(0,217,245,.22); padding-top:12px; margin-top:7px; color:#B8B09D; font:9px var(--mono); letter-spacing:.1em; }
.art-bottom b { color:#F2EDE1; font-weight:500; }

.ticker { border-top:1px solid var(--hair); border-bottom:1px solid var(--hair); margin:30px 0 27px; overflow:hidden; padding:11px 0; white-space:nowrap; color:var(--mute); font:10px var(--mono); letter-spacing:.13em; }
.ticker-track { display:inline-flex; gap:32px; min-width:max-content; animation:marquee 32s linear infinite; }
.ticker-item:before { content:"✳"; color:var(--accent); padding-right:12px; }

.metric { background:var(--paper-2); border:1px solid var(--hair); border-radius:5px; padding:16px 17px 14px; min-height:105px; animation:rise .65s both; }
.metric-k { color:var(--mute); font:10px var(--mono); letter-spacing:.1em; text-transform:uppercase; }
.metric-v { color:var(--ink); font:700 26px/1.25 var(--display); letter-spacing:-1px; margin-top:10px; overflow-wrap:anywhere; }
.metric-s { color:var(--mute); font:10px var(--mono); margin-top:4px; }
.section-head { display:flex; align-items:baseline; gap:12px; border-bottom:1px solid var(--hair); padding-bottom:11px; margin:32px 0 0; }
.section-no { color:var(--accent); font:11px var(--mono); }
.section-title { color:var(--ink); font:600 21px var(--display); letter-spacing:-.5px; }
.cap-list { border-top:1px solid var(--hair); margin-top:12px; }
.cap-row { display:grid; grid-template-columns:44px 1.1fr 1.8fr auto; align-items:center; gap:12px; padding:15px 5px; border-bottom:1px solid var(--hair); animation:rise .55s both; }
.cap-no { color:var(--accent); font:11px var(--mono); }
.cap-title { color:var(--ink); font:600 15px var(--display); }
.cap-desc { color:var(--mute); font-size:12px; line-height:1.5; }
.cap-tag { color:var(--ink-2); font:9px var(--mono); letter-spacing:.08em; border:1px solid var(--hair); border-radius:3px; padding:5px 7px; white-space:nowrap; }

.panel { background:var(--paper-2); border:1px solid var(--hair); border-radius:6px; padding:19px; margin-bottom:14px; }
.panel-dark { background:var(--ink); color:var(--paper); border:1px solid var(--ink); border-radius:6px; padding:19px; }
.panel-k { color:var(--mute); font:10px var(--mono); letter-spacing:.12em; text-transform:uppercase; margin-bottom:9px; }
.panel-dark .panel-k { color:#B8B09D; }
.panel-title { color:var(--ink); font:600 21px var(--display); letter-spacing:-.5px; margin-bottom:5px; }
.panel-copy { color:var(--mute); font-size:12px; line-height:1.55; }
.panel-dark .panel-title { color:var(--paper); }
.panel-dark .panel-copy { color:#B8B09D; }
.result-title { color:var(--ok); font:600 15px var(--display); margin:0 0 4px; }
.result-copy { color:var(--mute); font-size:12px; }
.result-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:9px; margin-top:14px; }
.result-cell { border:1px solid var(--hair); background:var(--paper); padding:11px; border-radius:4px; min-width:0; }
.result-cell small { display:block; color:var(--mute); font:9px var(--mono); letter-spacing:.08em; text-transform:uppercase; margin-bottom:7px; }
.result-cell b { color:var(--ink); font:600 14px var(--mono); overflow-wrap:anywhere; }
.ledger-row { display:grid; grid-template-columns:1fr auto auto; gap:15px; align-items:center; border-bottom:1px solid var(--hair); padding:13px 4px; }
.ledger-name { color:var(--ink); font:600 13px var(--display); }
.ledger-meta { color:var(--mute); font:10px var(--mono); margin-top:4px; }
.tag { border:1px solid var(--hair); padding:5px 7px; border-radius:3px; color:var(--ink-2); font:9px var(--mono); }
.tag.buy { color:var(--ok); border-color:rgba(47,107,79,.32); }
.tag.sell { color:var(--accent-d); border-color:rgba(232,71,43,.32); }
.empty { border:1px dashed rgba(22,20,15,.3); border-radius:5px; padding:27px; text-align:center; color:var(--mute); font-size:12px; }
.footer { display:flex; justify-content:space-between; gap:15px; border-top:1px solid var(--hair); margin-top:42px; padding-top:13px; color:var(--mute); font:9px var(--mono); letter-spacing:.07em; text-transform:uppercase; }

/* Streamlit controls, restyled to match the DocuStruct workspace */
[data-testid="stForm"] { background:var(--paper-2); border:1px solid var(--hair); border-radius:6px; padding:18px; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background:var(--paper-2); border-color:rgba(22,20,15,.24); border-radius:4px; color:var(--ink); font-family:var(--mono); font-size:13px;
}
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus { border-color:var(--accent); box-shadow:0 0 0 1px var(--accent); }
[data-testid="stWidgetLabel"] p { color:var(--ink-2); font-size:11px; font-weight:600; letter-spacing:.02em; }
[data-testid="stCheckbox"] label, [data-testid="stRadio"] label { color:var(--ink-2); font-size:12px; }
[data-testid="stRadio"] [role="radiogroup"] { gap:9px; }
[data-testid="stAlert"] { border-radius:5px; }
.stButton > button, [data-testid="stFormSubmitButton"] button, [data-testid="stLinkButton"] a {
    border-radius:4px; border:1px solid var(--ink); background:var(--ink); color:var(--paper-2);
    font:600 12px var(--mono); letter-spacing:.02em; min-height:42px; transition:transform .18s ease, background .18s ease, box-shadow .18s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover, [data-testid="stLinkButton"] a:hover {
    background:var(--accent); border-color:var(--accent); color:white; transform:translateY(-2px); box-shadow:3px 3px 0 rgba(22,20,15,.17);
}
.stButton > button:focus, [data-testid="stFormSubmitButton"] button:focus { box-shadow:0 0 0 2px var(--paper-2),0 0 0 4px var(--accent); }
[data-testid="stCode"] { border:1px solid var(--hair); border-radius:5px; }
hr { border-color:var(--hair); }

.rise { animation:rise .7s both; }
@keyframes rise { from { opacity:0; transform:translateY(13px); } to { opacity:1; transform:translateY(0); } }
@keyframes reveal { from { opacity:0; transform:translateY(110%); } to { opacity:1; transform:translateY(0); } }
@keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(47,107,79,.38); } 70% { box-shadow:0 0 0 7px rgba(47,107,79,0); } 100% { box-shadow:0 0 0 0 rgba(47,107,79,0); } }
@keyframes marquee { to { transform:translateX(-50%); } }
@keyframes draw { to { stroke-dashoffset:0; } }
@keyframes orbit { to { transform:rotate(360deg); } }
@keyframes candle-in { from { transform:scaleY(.05); opacity:.2; } to { transform:scaleY(1); opacity:1; } }
@media (max-width: 800px) {
    .block-container { padding:1.35rem 1rem 2rem; }
    .cap-row { grid-template-columns:32px 1fr; }
    .cap-desc { grid-column:2; }
    .cap-tag { display:none; }
    .result-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .footer { flex-direction:column; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration:.01ms !important; animation-iteration-count:1 !important; scroll-behavior:auto !important; }
}
"""

# Cyber-finance skin: layered over the layout rules above so the trading logic stays untouched.
CSS += r"""

/* FINANCE / CYBERPUNK VISUAL SYSTEM */
html, body, [data-testid="stAppViewContainer"], .stApp {
    background: var(--paper) !important;
    color: var(--ink) !important;
}
.stApp {
    background-image:
        radial-gradient(ellipse at 78% 2%, rgba(0,217,245,.11), transparent 34%),
        radial-gradient(ellipse at 8% 42%, rgba(184,255,59,.055), transparent 32%),
        linear-gradient(rgba(0,217,245,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,217,245,.035) 1px, transparent 1px) !important;
    background-size: auto, auto, 42px 42px, 42px 42px !important;
    background-attachment: fixed !important;
}
.stApp::before {
    opacity: .13 !important;
    background-image: linear-gradient(transparent 50%, rgba(0,0,0,.18) 50%) !important;
    background-size: 100% 4px !important;
}
[data-testid="stHeader"] { background: rgba(7,11,20,.72) !important; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A1220 0%, #080D17 100%) !important;
    border-right: 1px solid rgba(0,217,245,.22) !important;
    box-shadow: 12px 0 40px rgba(0,0,0,.18);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: var(--ink-2); }
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    border: 1px solid transparent !important;
    border-radius: 5px !important;
    background: transparent !important;
    transition: all .22s ease !important;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
    background: rgba(0,217,245,.07) !important;
    border-color: rgba(0,217,245,.24) !important;
    box-shadow: inset 2px 0 var(--accent);
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg, rgba(0,217,245,.14), rgba(0,217,245,.025)) !important;
    border-color: rgba(0,217,245,.28) !important;
    box-shadow: inset 2px 0 var(--accent), 0 0 18px rgba(0,217,245,.05);
}
.brand { border-bottom-color: rgba(0,217,245,.24) !important; }
.brand-mark {
    color: #061018 !important;
    background: linear-gradient(135deg, var(--accent), var(--hi)) !important;
    border-radius: 9px !important;
    box-shadow: 0 0 22px rgba(0,217,245,.28), 0 0 38px rgba(184,255,59,.08) !important;
    transform: none !important;
}
.brand-name { color: var(--ink) !important; letter-spacing: -.9px !important; }
.brand-sub, .side-h, .side-foot { color: #6F8AA3 !important; }
.side-status, .panel, [data-testid="stForm"] {
    background: linear-gradient(145deg, rgba(15,26,43,.96), rgba(10,17,29,.96)) !important;
    border: 1px solid rgba(111,174,205,.2) !important;
    border-radius: 8px !important;
    box-shadow: inset 0 1px rgba(255,255,255,.025), 0 12px 35px rgba(0,0,0,.13) !important;
}
.status-row { color: #9DB2C7 !important; }
.status-row b { color: var(--accent) !important; }
.dot.live, .pulse-dot {
    background: var(--hi) !important;
    box-shadow: 0 0 11px rgba(184,255,59,.65) !important;
    animation: cyberpulse 1.8s infinite !important;
}
.dot.bad { background: var(--bad) !important; box-shadow: 0 0 10px rgba(255,77,131,.55) !important; }
.masthead {
    color: #718BA4 !important;
    border-bottom-color: rgba(0,217,245,.2) !important;
}
.masthead .strong { color: var(--accent) !important; text-shadow: 0 0 13px rgba(0,217,245,.28); }
.eyebrow { color: #8FA7BE !important; }
.display { color: #F1F8FF !important; text-shadow: 0 5px 30px rgba(0,0,0,.25); }
.hl { color: var(--accent) !important; text-shadow: 0 0 24px rgba(0,217,245,.2); }
.lead { color: #9FB3C7 !important; }
.hero-art {
    color: #EAF7FF !important;
    background:
        radial-gradient(circle at 82% 12%, rgba(0,217,245,.18), transparent 28%),
        linear-gradient(145deg, #111F33 0%, #09111E 55%, #0C1827 100%) !important;
    border: 1px solid rgba(0,217,245,.42) !important;
    border-radius: 9px !important;
    box-shadow: 0 0 0 1px rgba(0,217,245,.05), 0 20px 55px rgba(0,0,0,.35), 0 0 36px rgba(0,217,245,.08) !important;
}
.hero-art:before {
    border-color: rgba(0,217,245,.28) !important;
    box-shadow: 0 0 0 24px rgba(0,217,245,.035), 0 0 0 52px rgba(184,255,59,.025) !important;
}
.art-top, .art-sub, .art-bottom { color: #829BB3 !important; }
.art-pill { color: var(--hi) !important; border-color: rgba(184,255,59,.45) !important; background: rgba(184,255,59,.07); }
.art-big { color: #F1F8FF !important; }
.art-big span { color: var(--hi) !important; text-shadow: 0 0 18px rgba(184,255,59,.2); }
.art-bottom { border-top-color: rgba(0,217,245,.22) !important; }
.art-bottom b { color: #DFF7FF !important; }
.chart-glow { fill: rgba(0,217,245,.11) !important; }
.chart-line { stroke: var(--accent) !important; filter: drop-shadow(0 0 5px rgba(0,217,245,.55)); }
.ticker { border-color: rgba(0,217,245,.2) !important; color: #7F99B2 !important; }
.ticker-item:before { color: var(--hi) !important; text-shadow: 0 0 9px rgba(184,255,59,.5); }
.metric {
    background: linear-gradient(145deg, rgba(15,27,45,.95), rgba(9,16,28,.96)) !important;
    border: 1px solid rgba(111,174,205,.2) !important;
    border-radius: 8px !important;
    box-shadow: inset 0 1px rgba(255,255,255,.035), 0 12px 28px rgba(0,0,0,.16) !important;
    position: relative; overflow: hidden;
}
.metric:after { content:""; position:absolute; inset:0 auto 0 0; width:2px; background:linear-gradient(var(--accent), transparent 85%); opacity:.8; }
.metric-k, .metric-s { color: #8299B0 !important; }
.metric-v { color: #ECF8FF !important; }
.section-head { border-bottom-color: rgba(0,217,245,.2) !important; }
.section-no, .cap-no { color: var(--hi) !important; }
.section-title { color: #E7F4FF !important; }
.cap-list { border-top-color: rgba(0,217,245,.2) !important; }
.cap-row { border-bottom-color: rgba(111,174,205,.16) !important; }
.cap-title, .ledger-name { color: #E2F0FC !important; }
.cap-desc, .ledger-meta { color: #839BB2 !important; }
.cap-tag, .tag {
    color: #AFC4D7 !important;
    border: 1px solid rgba(0,217,245,.25) !important;
    background: rgba(0,217,245,.045) !important;
    border-radius: 4px !important;
}
.panel-dark {
    background: linear-gradient(145deg, #101E31, #09121F) !important;
    border: 1px solid rgba(0,217,245,.34) !important;
    border-radius: 8px !important;
    box-shadow: 0 15px 40px rgba(0,0,0,.24), inset 0 1px rgba(255,255,255,.035) !important;
}
.panel-k, .panel-copy { color: #8FA6BC !important; }
.panel-title { color: #ECF7FF !important; }
.panel-dark .panel-k, .panel-dark .panel-copy { color: #93AFC5 !important; }
.result-title { color: var(--hi) !important; text-shadow: 0 0 12px rgba(184,255,59,.16); }
.result-copy { color: #8EA7BE !important; }
.result-cell { background: #091321 !important; border-color: rgba(0,217,245,.18) !important; }
.result-cell small { color: #7892AA !important; }
.result-cell b { color: #E8F7FF !important; }
.ledger-row { border-bottom-color: rgba(111,174,205,.17) !important; }
.tag.buy { color: var(--hi) !important; border-color: rgba(184,255,59,.38) !important; background: rgba(184,255,59,.06) !important; }
.tag.sell { color: #FF77A0 !important; border-color: rgba(255,77,131,.36) !important; background: rgba(255,77,131,.06) !important; }
.empty { color: #829BB2 !important; border-color: rgba(0,217,245,.26) !important; background: rgba(0,217,245,.025) !important; }
.footer { color: #718AA2 !important; border-top-color: rgba(0,217,245,.2) !important; }

/* Inputs: dark exchange-terminal controls with clear focus rings. */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stTextArea"] textarea {
    background: #081321 !important;
    border: 1px solid rgba(111,174,205,.27) !important;
    border-radius: 5px !important;
    color: #E8F7FF !important;
    caret-color: var(--accent) !important;
    font-family: var(--mono) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent), 0 0 18px rgba(0,217,245,.12) !important;
}
[data-testid="stWidgetLabel"] p { color: #B0C4D7 !important; }
[data-testid="stCheckbox"] label, [data-testid="stRadio"] label { color: #B5C9DC !important; }
[data-testid="stRadio"] [role="radiogroup"] label {
    border: 1px solid rgba(111,174,205,.18);
    border-radius: 5px;
    padding: 5px 9px;
    background: rgba(0,217,245,.025);
}
[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    border-color: rgba(0,217,245,.55);
    background: rgba(0,217,245,.09);
    box-shadow: 0 0 14px rgba(0,217,245,.07);
}
[data-testid="stForm"] { padding: 20px !important; }
.stButton > button, [data-testid="stFormSubmitButton"] button, [data-testid="stLinkButton"] a {
    background: linear-gradient(100deg, #00CBE8, #00AFCB) !important;
    color: #031019 !important;
    border: 1px solid #00D9F5 !important;
    border-radius: 5px !important;
    font-weight: 700 !important;
    letter-spacing: .025em !important;
    box-shadow: 0 0 18px rgba(0,217,245,.12), inset 0 1px rgba(255,255,255,.24) !important;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover, [data-testid="stLinkButton"] a:hover {
    background: linear-gradient(100deg, #B8FF3B, #8BEA2B) !important;
    border-color: var(--hi) !important;
    color: #07110A !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 0 25px rgba(184,255,59,.2) !important;
}
.stButton > button:focus, [data-testid="stFormSubmitButton"] button:focus {
    box-shadow: 0 0 0 2px #07101B, 0 0 0 4px var(--accent), 0 0 20px rgba(0,217,245,.25) !important;
}
[data-testid="stAlert"] { background: #0D1A2B !important; border: 1px solid rgba(0,217,245,.26) !important; color: #DCEEFF !important; }
[data-testid="stExpander"] { background: rgba(12,22,37,.92) !important; border: 1px solid rgba(111,174,205,.2) !important; border-radius: 6px !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p { color: #BDD2E4 !important; }
[data-testid="stCode"] { background: #081321 !important; border: 1px solid rgba(0,217,245,.2) !important; }
[data-testid="stJson"] { background: #081321 !important; }
[data-testid="stCaptionContainer"] p, .stCaption { color: #819AB1 !important; }
hr { border-color: rgba(0,217,245,.18) !important; }

@keyframes cyberpulse {
    0% { box-shadow: 0 0 0 0 rgba(184,255,59,.45), 0 0 8px rgba(184,255,59,.5); }
    70% { box-shadow: 0 0 0 8px rgba(184,255,59,0), 0 0 12px rgba(184,255,59,.35); }
    100% { box-shadow: 0 0 0 0 rgba(184,255,59,0), 0 0 8px rgba(184,255,59,.5); }
}
@media (max-width: 800px) {
    .hero-art { padding: 17px !important; }
    .display { font-size: clamp(2.35rem, 11vw, 3.5rem) !important; }
}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def esc(value: Any) -> str:
    return html.escape(str(value))


def render(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def get_client() -> BinanceFuturesTestnetClient:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise TradingBotError(
            "Demo API credentials are missing. Add BINANCE_API_KEY and "
            "BINANCE_API_SECRET to your local .env file, then restart Streamlit."
        )
    return BinanceFuturesTestnetClient(api_key, api_secret)


def metric_card(label: str, value: Any, note: str, delay: float = 0) -> None:
    render(
        f'<div class="metric" style="animation-delay:{delay:.2f}s">'
        f'<div class="metric-k">{esc(label)}</div>'
        f'<div class="metric-v">{esc(value)}</div>'
        f'<div class="metric-s">{esc(note)}</div></div>'
    )


def section(number: str, title: str) -> None:
    render(
        f'<div class="section-head"><span class="section-no">{esc(number)}</span>'
        f'<span class="section-title">{esc(title)}</span></div>'
    )


def masthead(page: str) -> None:
    now = datetime.now().strftime("%a %d %b %Y").upper()
    render(
        '<div class="masthead rise"><span class="strong">Futures Desk</span>'
        f'<span> / {esc(page)}</span><span class="grow"></span>'
        f'<span>{esc(now)}</span><span> · UTC+05:30</span></div>'
    )


def hero_visual() -> str:
    # Decorative artwork only: no synthetic market prices or fabricated live data.
    points = "0,92 35,82 69,91 103,58 137,68 171,38 205,49 239,23 273,31 310,7"
    return (
        '<div class="hero-art">'
        '<div class="art-top"><span>Execution environment</span><span class="art-pill">DEMO · NOT LIVE</span></div>'
        '<div class="art-big">Practice with <span>precision.</span></div>'
        '<div class="art-sub">ORDER FLOW / SIGNED REQUESTS / AUDIT LOGS</div>'
        '<div class="chart-wrap"><svg viewBox="0 0 320 112" preserveAspectRatio="none" aria-hidden="true">'
        '<path class="chart-glow" d="M0 92 L35 82 L69 91 L103 58 L137 68 L171 38 L205 49 L239 23 L273 31 L310 7 L320 112 L0 112 Z"/>'
        '<path class="chart-line" d="M' + points.replace(" ", " L") + '"/>'
        '<g stroke="#B8B09D" stroke-width="1" opacity=".55">'
        '<path d="M35 60V97 M69 72V103 M103 46V76 M137 54V82 M171 25V54 M205 36V61 M239 9V37 M273 17V42"/>'
        '</g><g fill="#E8472B">'
        '<rect class="candle" x="31" y="72" width="8" height="12" style="animation-delay:.15s"/>'
        '<rect class="candle" x="65" y="83" width="8" height="10" style="animation-delay:.22s"/>'
        '<rect class="candle" x="99" y="52" width="8" height="15" style="animation-delay:.29s"/>'
        '<rect class="candle" x="133" y="62" width="8" height="12" style="animation-delay:.36s"/>'
        '</g><g fill="#F5D547">'
        '<rect class="candle" x="167" y="32" width="8" height="13" style="animation-delay:.43s"/>'
        '<rect class="candle" x="201" y="42" width="8" height="12" style="animation-delay:.50s"/>'
        '<rect class="candle" x="235" y="15" width="8" height="14" style="animation-delay:.57s"/>'
        '<rect class="candle" x="269" y="21" width="8" height="13" style="animation-delay:.64s"/>'
        '</g></svg></div>'
        '<div class="art-bottom"><span><b>01</b> · MARKET</span><span><b>02</b> · LIMIT</span><span><b>03</b> · LOGGED</span></div>'
        '</div>'
    )


def ticker() -> None:
    words = ["BINANCE USDⓈ-M FUTURES", "DEMO ENVIRONMENT", "MARKET ORDERS", "LIMIT ORDERS", "SIGNED REST API", "STRUCTURED ACTIVITY LOGS"]
    repeated = words + words
    items = "".join(f'<span class="ticker-item">{esc(word)}</span>' for word in repeated)
    render(f'<div class="ticker"><div class="ticker-track">{items}</div></div>')


def show_order_result(order: dict[str, str], response: dict[str, Any]) -> None:
    status = str(response.get("status", "UNKNOWN")).upper()
    heading = "Order request accepted" if status in {"NEW", "PARTIALLY_FILLED", "FILLED"} else "Order response received"
    fields = [
        ("Symbol", order.get("symbol", "—")),
        ("Side", order.get("side", "—")),
        ("Type", order.get("type", "—")),
        ("Quantity", order.get("quantity", "—")),
        ("Order ID", response.get("orderId", "N/A")),
        ("Status", status),
        ("Executed", response.get("executedQty", "N/A")),
        ("Average price", response.get("avgPrice") or "N/A"),
    ]
    if "price" in order:
        fields.insert(4, ("Limit price", order["price"]))
    cells = "".join(
        f'<div class="result-cell"><small>{esc(key)}</small><b>{esc(value)}</b></div>'
        for key, value in fields
    )
    render(
        '<div class="panel" style="margin-top:16px">'
        f'<div class="result-title">✓ {esc(heading)}</div>'
        '<div class="result-copy">Binance Demo response · review the details before placing another order.</div>'
        f'<div class="result-grid">{cells}</div></div>'
    )
    if status in {"NEW", "PARTIALLY_FILLED"}:
        st.info("The order is accepted but not fully filled. Check its status in your Binance Demo order history.")


def read_log_entries() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    entries: list[dict[str, Any]] = []
    try:
        lines = LOG_PATH.read_text(encoding="utf-8").splitlines()[-100:]
        for line in lines:
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    entries.append(item)
            except json.JSONDecodeError:
                continue
    except OSError as exc:
        LOGGER.warning("Could not read activity log", extra={"event": "log_read_error", "error": str(exc)})
    return entries


def render_recent_orders() -> None:
    orders = list(reversed(st.session_state.session_orders))[:4]
    if not orders:
        render('<div class="empty">No orders placed in this session yet. Your next Demo order will appear here.</div>')
        return
    rows = []
    for item in orders:
        order = item["order"]
        response = item["response"]
        side = order["side"].lower()
        rows.append(
            '<div class="ledger-row">'
            f'<div><div class="ledger-name">{esc(order["symbol"])} · {esc(order["type"])}</div>'
            f'<div class="ledger-meta">{esc(item.get("time", "Session order"))} · Qty {esc(order["quantity"])}</div></div>'
            f'<span class="tag {side}">{esc(order["side"])}</span>'
            f'<span class="tag">{esc(response.get("status", "UNKNOWN"))}</span></div>'
        )
    render('<div class="cap-list">' + "".join(rows) + '</div>')


def go_to_trade() -> None:
    st.session_state.page = "Trade terminal"


def render_sidebar() -> str:
    api_ready = bool(os.getenv("BINANCE_API_KEY", "").strip() and os.getenv("BINANCE_API_SECRET", "").strip())
    with st.sidebar:
        render(
            '<div class="brand"><div class="brand-mark">⌁</div><div>'
            '<div class="brand-name">Futures Desk</div><div class="brand-sub">Binance · Demo terminal</div>'
            '</div></div>'
        )
        render('<div class="side-h">Workspace</div>')
        page = st.radio("Navigate", NAV, key="page", format_func=lambda value: NAV_LABELS[value], label_visibility="collapsed")
        render('<div class="side-h">System status</div>')
        configured_label = "CONFIGURED" if api_ready else "MISSING KEYS"
        verified = bool(st.session_state.connection_verified)
        verified_label = "VERIFIED" if verified else "NOT CHECKED"
        render(
            '<div class="side-status">'
            f'<div class="status-row"><i class="dot {"live" if api_ready else "bad"}"></i>Demo credentials<b>{configured_label}</b></div>'
            f'<div class="status-row"><i class="dot {"live" if verified else ""}"></i>API connection<b>{verified_label}</b></div>'
            '<div class="status-row"><i class="dot live"></i>REST environment<b>DEMO ONLY</b></div>'
            '</div>'
        )
        if st.button("Verify Demo connection", use_container_width=True, key="verify_connection"):
            try:
                config = get_client().get_account_config()
                st.session_state.account_config = config
                st.session_state.connection_verified = True
                LOGGER.info("Demo API connection verified", extra={"event": "account_connection_success"})
                st.success("Authenticated Demo connection verified.")
            except (BinanceAPIError, NetworkError, TradingBotError, ValueError) as exc:
                st.session_state.connection_verified = False
                LOGGER.error("Demo API connection failed", extra={"event": "account_connection_failure", "error": str(exc)})
                st.error(str(exc))
        st.link_button("Open Binance Demo ↗", "https://demo.binance.com/en/futures/BTCUSDT", use_container_width=True)
        render('<div class="side-h">Safety note</div>')
        st.caption("This workspace is pinned to the Binance Futures Demo REST host. Never add production API credentials to this project.")
        render('<div class="side-foot">FUTURES DESK / V1.1<br>PYTHON · STREAMLIT · REST API</div>')
    return page


page = render_sidebar()
masthead(page)

# -----------------------------------------------------------------------------
# OVERVIEW
# -----------------------------------------------------------------------------
if page == "Overview":
    api_ready = bool(os.getenv("BINANCE_API_KEY", "").strip() and os.getenv("BINANCE_API_SECRET", "").strip())
    left, right = st.columns([1.02, 1], gap="large")
    with left:
        render(
            '<div class="eyebrow rise"><i class="pulse-dot"></i>USDⓈ-M Futures · isolated Demo workspace</div>'
            '<div class="display"><span class="line"><span>Trade with</span></span>'
            '<span class="line"><span class="hl">a clearer head.</span></span></div>'
            '<div class="lead rise" style="animation-delay:.25s">A focused trading workspace for testing MARKET and LIMIT orders, '
            'checking API responses, and reviewing every request in a structured activity log. No production endpoint is configured.</div>'
        )
        st.button("Open trade terminal   →", type="primary", key="go_trade", on_click=go_to_trade)
        render('<div style="color:var(--mute);font:10px var(--mono);margin-top:12px">BUILT FOR TESTING · NOT FINANCIAL ADVICE</div>')
    with right:
        render(hero_visual())

    ticker()

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        metric_card("API credentials", "Ready" if api_ready else "Missing", "Local .env · never displayed", .06)
    with c2:
        metric_card("Orders this session", len(st.session_state.session_orders), "Successful API submissions", .13)
    with c3:
        metric_card("Order types", "02", "MARKET + LIMIT", .20)
    with c4:
        metric_card("Environment", "DEMO", "No live trading endpoint", .27)

    section("01", "What this terminal does")
    capabilities = [
        ("01", "Market execution", "Submit BUY or SELL market orders through the signed Demo endpoint.", "MARKET"),
        ("02", "Limit execution", "Send GTC limit orders with a specified quantity and price.", "LIMIT · GTC"),
        ("03", "Request verification", "Check authenticated account configuration without exposing credentials.", "SIGNED REST"),
        ("04", "Activity ledger", "Review structured request, response, and error events from the local log.", "JSON LINES"),
    ]
    render('<div class="cap-list">' + "".join(
        f'<div class="cap-row" style="animation-delay:{i * .07:.2f}s"><span class="cap-no">{n}</span>'
        f'<span class="cap-title">{esc(title)}</span><span class="cap-desc">{esc(desc)}</span>'
        f'<span class="cap-tag">{esc(tag)}</span></div>'
        for i, (n, title, desc, tag) in enumerate(capabilities)
    ) + '</div>')

    section("02", "Recent orders")
    render_recent_orders()

# -----------------------------------------------------------------------------
# TRADE TERMINAL
# -----------------------------------------------------------------------------
elif page == "Trade terminal":
    render(
        '<div class="eyebrow rise"><i class="pulse-dot"></i>Execution desk · Binance Demo only</div>'
        '<div class="display"><span class="line"><span>Make your</span></span>'
        '<span class="line"><span class="hl">next move.</span></span></div>'
        '<div class="lead">Configure an order, review the inputs, and explicitly confirm before the request is sent to the Demo environment.</div>'
    )
    left, right = st.columns([1.2, .8], gap="large")
    with left:
        render('<div class="panel-k">01 / New order</div><div class="panel-title">Order ticket</div><div class="panel-copy">All fields are validated before the signed request is sent.</div>')
        with st.form("order_form", clear_on_submit=False):
            symbol = st.text_input("Trading symbol", value="BTCUSDT", help="Example: BTCUSDT")
            side = st.radio("Order side", options=["BUY", "SELL"], horizontal=True)
            order_type = st.radio("Execution type", options=["MARKET", "LIMIT"], horizontal=True)
            quantity = st.text_input("Quantity", value="0.001", help="Quantity in the base asset, e.g. BTC")
            price: str | None = None
            if order_type == "LIMIT":
                entered_price = st.text_input("Limit price (USDT)", value="", placeholder="Enter limit price", help="Required for LIMIT orders")
                price = entered_price.strip() or None
            render('<div style="height:5px"></div>')
            confirmed = st.checkbox("I confirm this request is being sent to Binance Futures Demo.")
            submitted = st.form_submit_button("Submit Demo order   →", type="primary", use_container_width=True)

        if submitted:
            st.session_state.last_order = None
            if not confirmed:
                st.warning("Confirm the Demo environment before submitting this order.")
            else:
                try:
                    service = OrderService(get_client())
                    order, response = service.submit_order(
                        symbol=symbol,
                        side=side,
                        order_type=order_type,
                        quantity=quantity,
                        price=price,
                    )
                    item = {
                        "order": order,
                        "response": response,
                        "time": datetime.now().strftime("%H:%M:%S"),
                    }
                    st.session_state.last_order = item
                    st.session_state.session_orders.append(item)
                    LOGGER.info("UI order submission completed", extra={"event": "ui_order_success", "response": response})
                except ValidationError as exc:
                    LOGGER.warning("UI order validation failed", extra={"event": "ui_validation_error", "error": str(exc)})
                    st.error(f"Input validation failed: {exc}")
                except (BinanceAPIError, NetworkError) as exc:
                    LOGGER.error("UI order submission failed", extra={"event": "ui_order_failure", "error": str(exc)})
                    if getattr(exc, "outcome_unknown", False):
                        st.error(f"Order outcome UNKNOWN: {exc}")
                        st.warning("Do not submit again yet. Check Binance Demo order history first.")
                    else:
                        st.error(f"Order failed: {exc}")
                except (TradingBotError, ValueError) as exc:
                    st.error(str(exc))
                except Exception as exc:  # Keep unexpected implementation details in the local log.
                    LOGGER.exception("Unexpected UI error", extra={"event": "ui_unexpected_error", "error": str(exc)})
                    st.error("Unexpected application error. Check logs/bot.log for details.")

        if st.session_state.last_order:
            show_order_result(st.session_state.last_order["order"], st.session_state.last_order["response"])

    with right:
        render(
            '<div class="panel-dark">'
            '<div class="panel-k">Execution protocol</div><div class="panel-title">Before you send.</div>'
            '<div class="panel-copy">A Demo order changes the state of your Demo account. Check the symbol, quantity and order type every time.</div>'
            '<div style="height:14px;border-top:1px solid rgba(0,217,245,.22);margin-top:14px"></div>'
            '<div style="font:10px var(--mono);color:#B8FF3B;letter-spacing:.1em">MARKET</div>'
            '<div class="panel-copy" style="margin:5px 0 16px">Executes at the available market price. The final fill price can differ from your expectation.</div>'
            '<div style="font:10px var(--mono);color:#B8FF3B;letter-spacing:.1em">LIMIT · GTC</div>'
            '<div class="panel-copy" style="margin-top:5px">Rests until filled or cancelled. An accepted LIMIT order may remain NEW.</div>'
            '</div>'
        )
        render('<div class="panel"><div class="panel-k">02 / Connection</div><div class="panel-title">Demo API</div><div class="panel-copy">REST host</div><div class="mono" style="font-size:11px;margin-top:8px;overflow-wrap:anywhere">demo-fapi.binance.com</div></div>')
        render('<div class="panel"><div class="panel-k">03 / Safety</div><div class="panel-copy">Never paste your API secret into the interface or commit your .env file. A timeout can leave an order outcome unknown: check order history before retrying.</div></div>')

# -----------------------------------------------------------------------------
# ACTIVITY
# -----------------------------------------------------------------------------
elif page == "Activity":
    render(
        '<div class="eyebrow rise"><i class="pulse-dot"></i>Local audit trail · JSON lines</div>'
        '<div class="display"><span class="line"><span>Every request.</span></span>'
        '<span class="line"><span class="hl">Accounted for.</span></span></div>'
        '<div class="lead">Review orders created in this session and the real request/response events captured in logs/bot.log.</div>'
    )
    section("01", "Session orders")
    render_recent_orders()
    section("02", "Application log")
    entries = read_log_entries()
    if entries:
        st.caption(f"Showing the latest {min(12, len(entries))} structured events from the local log. API signatures are excluded.")
        for entry in reversed(entries[-12:]):
            level = esc(entry.get("level", "INFO"))
            event = esc(entry.get("event", entry.get("message", "Application event")))
            timestamp = esc(entry.get("timestamp", "—"))
            details = {key: value for key, value in entry.items() if key not in {"timestamp", "level", "logger", "message", "event"}}
            with st.expander(f"{timestamp}   ·   {level}   ·   {event}"):
                st.json(details if details else {"message": entry.get("message", "")}, expanded=False)
    else:
        render('<div class="empty">No application log found yet. Verify the Demo connection or submit a Demo order to create a real log.</div>')
        synthetic_logs = ROOT / "logs" / "demo_market_order.log"
        if synthetic_logs.exists():
            st.caption("The repository also includes sample demonstration logs. They are synthetic examples, not real account executions.")

# -----------------------------------------------------------------------------
# SETTINGS
# -----------------------------------------------------------------------------
elif page == "Settings":
    api_ready = bool(os.getenv("BINANCE_API_KEY", "").strip() and os.getenv("BINANCE_API_SECRET", "").strip())
    render(
        '<div class="eyebrow rise"><i class="pulse-dot"></i>Configuration · local workspace</div>'
        '<div class="display"><span class="line"><span>Under the</span></span>'
        '<span class="line"><span class="hl">hood.</span></span></div>'
        '<div class="lead">A quick look at the environment and the components powering this trading workspace.</div>'
    )
    section("01", "Application")
    settings = [
        ("Application", "Futures Desk"),
        ("Framework", "Python · Streamlit"),
        ("Exchange", "Binance USDⓈ-M Futures"),
        ("Environment", "Demo"),
        ("REST host", "https://demo-fapi.binance.com"),
        ("API credentials", "Configured" if api_ready else "Not configured"),
        ("Order types", "MARKET · LIMIT"),
        ("Log file", "logs/bot.log"),
    ]
    rows = "".join(
        f'<div class="ledger-row"><span class="ledger-name">{esc(key)}</span><span></span><span class="mono" style="font-size:11px">{esc(value)}</span></div>'
        for key, value in settings
    )
    render(f'<div class="cap-list">{rows}</div>')
    section("02", "Safety & scope")
    render(
        '<div class="panel" style="margin-top:14px"><div class="panel-title">Demo environment only</div>'
        '<div class="panel-copy">The REST client is pinned to demo-fapi.binance.com. API credentials are read from the local .env file and are never rendered on screen. '
        'Do not replace the Demo host with a production endpoint for this assignment.</div></div>'
    )
    config = st.session_state.account_config
    if config:
        render('<div class="panel-k">Last verified account configuration</div>')
        st.json({key: config.get(key) for key in ("canTrade", "dualSidePosition", "multiAssetsMargin", "feeTier", "updateTime")}, expanded=False)

render(
    '<div class="footer"><span>Futures Desk · demo trading workspace</span>'
    f'<span>Python / Streamlit · {datetime.now().year}</span></div>'
)
