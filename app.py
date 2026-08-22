"""
RingGuard AI — Production Dashboard
Razorpay /buildathon · Track 02 · AI Risk Manager

Layout strategy:
  - Sidebar  : global filter controls, session config, system status
  - Main     : 3-tab canvas (Overview | Merchant Explorer | Audit Ledger)
  - Containers with border=True act as premium dashboard cards
  - @st.cache_data on all I/O; st.session_state for cross-tab state;
    st.fragment for the audit-sync block to avoid full-page re-renders
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Path bootstrap (works whether run from repo root or ringguard/) ────────
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from detector import run_detection, build_graph, detect_rings, compute_metrics, load_data
from agent import analyze_all_rings, analyze_ring
from audit import log_detection, get_log

DATA_DIR = _HERE / "data"
LOGS_DIR = _HERE / "logs"

FAVICON_PATH = _HERE / "favicon.png"

# ══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="RingGuard AI · Risk Monitor",
    page_icon=str(FAVICON_PATH) if FAVICON_PATH.exists() else "◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800;900&family=Tenor+Sans&family=Marcellus&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── DESIGN TOKENS (USER COLOR PALETTE & TYPOGRAPHY) ─────────────────
   cream        #EFEAE1   warm alabaster / primary text / crisp contrast
   umber        #2F2A22   deep espresso charcoal / dark canvas base
   umber-dk     #1a1713   ultra-deep base background
   olive        #5C6B4A   olive moss green / clean & low-risk status
   terracotta   #C08457   warm terracotta sienna / primary accents & hero
   terracotta-lt #dca074  lighter warm sienna
   olive-lt     #7d9165   lighter moss sage
   muted        #8f8677   warm muted taupe
──────────────────────────────────────────────────────────────────── */

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
}
.stApp {
    background:
        radial-gradient(ellipse 70% 50% at 0%   0%,  rgba(192,132,87,.14)  0%, rgba(0,0,0,0) 55%),
        radial-gradient(ellipse 55% 45% at 100% 100%,rgba(92,107,74,.12) 0%, rgba(0,0,0,0) 50%),
        radial-gradient(ellipse 40% 30% at 50%  50%, rgba(239,234,225,.025) 0%, rgba(0,0,0,0) 60%),
        #1a1713;
    color: #EFEAE1;
}

/* Hide default menu & footer, make header non-intrusive */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent !important;
    z-index: 99999 !important;
}
header [data-testid="stToolbar"],
header [data-testid="stDecoration"],
header [data-testid="stStatusWidget"] {
    display: none !important;
}

.block-container { padding: 1.6rem 2.2rem 4rem 2.2rem !important; max-width: 100% !important; }

/* ── SIDEBAR CONTAINER ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1c1914 0%, #15120f 100%) !important;
    border-right: 1px solid rgba(192,132,87,.18) !important;
    box-shadow: 6px 0 28px rgba(0,0,0,.6) !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1.2rem !important;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Tenor Sans', 'Marcellus', sans-serif !important;
    font-size: .74rem !important; font-weight: 700 !important;
    color: #C08457 !important; text-transform: uppercase !important;
    letter-spacing: .16em !important; margin: 1.4rem 0 .5rem 0 !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(192,132,87,.15) !important; margin: .7rem 0 !important; }

/* ── SIDEBAR CONTROLS (EXPAND & COLLAPSE) ──────────────────────── */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapseButton"] svg {
    color: #C08457 !important;
    fill: #C08457 !important;
    transition: all .2s ease !important;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    background: rgba(192,132,87,.15) !important;
    color: #dca074 !important;
    transform: scale(1.1) !important;
}

/* ── SIDEBAR WIDGETS (SLIDER, SELECTBOX, BUTTONS) ─────────────── */
/* Slider styling (Terracotta & Olive Moss track & thumb) */
div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child {
    background: rgba(239,234,225,.08) !important;
    height: 5px !important;
    border-radius: 3px !important;
}
div[data-testid="stSlider"] div[data-baseweb="slider"] div[role="slider"] {
    background: #C08457 !important;
    border: 2px solid #EFEAE1 !important;
    box-shadow: 0 0 12px rgba(192,132,87,.8) !important;
    width: 16px !important;
    height: 16px !important;
}
div[data-testid="stSlider"] div[data-baseweb="slider"] > div > div:first-child {
    background: linear-gradient(90deg, #5C6B4A, #C08457) !important;
    height: 5px !important;
    border-radius: 3px !important;
}
div[data-testid="stSlider"] [data-testid="stMarkdownContainer"] p {
    font-family: 'Syne', sans-serif !important;
    color: #C08457 !important;
    font-weight: 700 !important;
}
div[data-testid="stSlider"] label {
    font-family: 'Tenor Sans', sans-serif !important;
    color: #8f8677 !important;
    font-size: .75rem !important;
    text-transform: uppercase !important;
    letter-spacing: .08em !important;
}

/* Selectbox styling */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: rgba(239,234,225,.03) !important;
    border: 1px solid rgba(192,132,87,.25) !important;
    border-radius: 8px !important;
    color: #EFEAE1 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: .84rem !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover {
    border-color: rgba(192,132,87,.6) !important;
}
div[data-testid="stSelectbox"] svg {
    fill: #C08457 !important;
}
div[data-testid="stSelectbox"] label {
    font-family: 'Tenor Sans', sans-serif !important;
    color: #8f8677 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* Text Input */
div[data-testid="stTextInput"] div[data-baseweb="input"] > div {
    background: rgba(239,234,225,.03) !important;
    border: 1px solid rgba(192,132,87,.2) !important;
    border-radius: 8px !important;
    color: #EFEAE1 !important;
}
div[data-testid="stTextInput"] input {
    color: #EFEAE1 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ── CARDS ─────────────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(239,234,225,.022) !important;
    backdrop-filter: blur(24px) saturate(120%) !important;
    border: 1px solid rgba(192,132,87,.16) !important;
    border-radius: 16px !important;
    padding: .35rem .55rem !important;
    box-shadow: 0 4px 24px rgba(0,0,0,.45), inset 0 1px 0 rgba(239,234,225,.04) !important;
}

/* ── TABS ──────────────────────────────────────────────────────── */
[data-testid="stTabs"] > div:first-child { border-bottom: 1px solid rgba(192,132,87,.18) !important; gap: 4px !important; }
[data-testid="stTabs"] button {
    font-family: 'Tenor Sans', 'Marcellus', sans-serif !important;
    font-weight: 600 !important; font-size: .88rem !important; color: #8f8677 !important;
    border-radius: 8px 8px 0 0 !important; padding: .6rem 1.5rem !important; transition: all .2s !important;
    letter-spacing: .02em !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #EFEAE1 !important;
    background: rgba(192,132,87,.12) !important;
    border-bottom: 2px solid #C08457 !important;
    font-weight: 700 !important;
}
[data-testid="stTabs"] button:hover:not([aria-selected="true"]) {
    color: #dca074 !important;
    background: rgba(239,234,225,.03) !important;
}

/* ── METRIC CARDS ─────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: rgba(239,234,225,.02) !important;
    border: 1px solid rgba(192,132,87,.15) !important;
    border-top: 2px solid #C08457 !important;
    border-radius: 12px !important;
    padding: 1.1rem 1.2rem 1rem 1.2rem !important;
    transition: all .3s cubic-bezier(.22,1,.36,1) !important;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(192,132,87,.4) !important;
    border-top-color: #dca074 !important;
    box-shadow: 0 12px 36px rgba(0,0,0,.5), 0 0 20px rgba(192,132,87,.16) !important;
    transform: translateY(-3px) !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Tenor Sans', 'Marcellus', sans-serif !important;
    color: #8f8677 !important; font-size: .72rem !important;
    text-transform: uppercase; letter-spacing: .12em; font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 2.3rem !important; font-weight: 800 !important;
    color: #EFEAE1 !important; line-height: 1.1 !important;
    letter-spacing: -.02em !important;
}
[data-testid="stMetricDelta"] svg { display: none !important; }
[data-testid="stMetricDelta"] > div {
    font-size: .7rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    letter-spacing: .02em !important;
    font-weight: 500 !important;
}

/* ── DATAFRAME ───────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(192,132,87,.16) !important;
    border-radius: 10px !important; overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
    background: rgba(192,132,87,.12) !important;
    color: #EFEAE1 !important; font-size: .74rem !important;
    text-transform: uppercase; letter-spacing: .08em; font-weight: 700 !important;
    font-family: 'Tenor Sans', sans-serif !important;
}

/* ── BUTTONS ───────────────────────────────────────────────────── */
.stButton > button {
    font-family: 'Tenor Sans', sans-serif !important;
    background: rgba(192,132,87,.08) !important;
    color: #EFEAE1 !important;
    border: 1px solid rgba(192,132,87,.35) !important;
    border-radius: 8px !important;
    font-weight: 600 !important; font-size: .84rem !important;
    padding: .5rem 1.4rem !important;
    letter-spacing: .04em !important;
    text-transform: uppercase !important;
    transition: all .25s cubic-bezier(.34,1.56,.64,1) !important;
    backdrop-filter: blur(10px) !important;
}
.stButton > button:hover {
    background: rgba(192,132,87,.22) !important;
    border-color: #C08457 !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(192,132,87,.25) !important;
}
.stButton > button:active { transform: scale(.97) !important; }

[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, rgba(192,132,87,.18), rgba(92,107,74,.1)) !important;
    border: 1px solid rgba(192,132,87,.4) !important;
    color: #EFEAE1 !important;
    border-radius: 8px !important;
    padding: .6rem 1rem !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, rgba(192,132,87,.32), rgba(92,107,74,.2)) !important;
    border-color: #C08457 !important;
    box-shadow: 0 4px 20px rgba(192,132,87,.3) !important;
    color: #ffffff !important;
}

[data-testid="stProgress"] > div { background: rgba(239,234,225,.06) !important; border-radius: 10px; }
[data-testid="stProgress"] > div > div { background: linear-gradient(90deg,#5C6B4A,#C08457,#dca074) !important; border-radius: 10px; }
[data-testid="stExpander"] {
    background: rgba(239,234,225,.015) !important;
    border: 1px solid rgba(192,132,87,.14) !important;
    border-radius: 10px !important;
}

/* ── CUSTOM CLASSES ────────────────────────────────────────────── */
.rg-section-label {
    font-family: 'Tenor Sans', 'Marcellus', sans-serif;
    font-size: .7rem; font-weight: 700; color: #C08457;
    text-transform: uppercase; letter-spacing: .16em; margin-bottom: .3rem;
}
.rg-section-title {
    font-family: 'Tenor Sans', 'Marcellus', sans-serif;
    font-size: 1.25rem; font-weight: 600; letter-spacing: .02em;
    color: #EFEAE1; margin: 0 0 1rem 0;
    display: flex; align-items: center; gap: 10px;
}
.rg-section-title::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(192,132,87,.35), rgba(92,107,74,.2), transparent);
    margin-left: 10px;
}
.rg-hero {
    background: linear-gradient(135deg, rgba(192,132,87,.15) 0%, rgba(47,42,34,.98) 50%, rgba(92,107,74,.1) 100%);
    border: 1px solid rgba(192,132,87,.25);
    border-radius: 18px; padding: 2.2rem 2.4rem;
    margin-bottom: 1.8rem; position: relative; overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,.5);
}
.rg-hero::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(220,160,116,.7), rgba(92,107,74,.5), transparent);
}
.rg-hero::after {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(105deg, transparent 40%, rgba(239,234,225,.03) 50%, transparent 60%);
    background-size: 200% 100%; animation: rg-shimmer 6s linear infinite;
    pointer-events: none; border-radius: 18px;
}
.rg-hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.7rem; font-weight: 800;
    background: linear-gradient(135deg, #EFEAE1 25%, #dca074 65%, #C08457 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    margin: 0 0 .4rem 0; line-height: 1.15;
    letter-spacing: -.02em;
}
.rg-hero-sub { color: #8f8677; font-size: .94rem; margin: 0; font-family: 'Tenor Sans', sans-serif; font-weight: 400; letter-spacing: .02em; }
.rg-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(192,132,87,.14); border: 1px solid rgba(192,132,87,.35);
    border-radius: 100px; padding: 4px 14px;
    font-size: .68rem; font-weight: 700; color: #C08457;
    letter-spacing: .14em; text-transform: uppercase; margin-bottom: .9rem;
    font-family: 'Tenor Sans', sans-serif;
}
.rg-badge .dot {
    width: 6px; height: 6px; background: #5C6B4A; border-radius: 50%;
    box-shadow: 0 0 8px #5C6B4A; animation: rg-dot-shift 4s ease-in-out infinite;
}
@keyframes rg-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
.rg-stat-pill {
    display: inline-flex; gap: 22px;
    background: rgba(47,42,34,.6); border: 1px solid rgba(192,132,87,.18);
    border-radius: 10px; padding: .6rem 1.4rem; margin-top: 1rem; flex-wrap: wrap;
}
.rg-stat-pill span { font-size: .8rem; color: #8f8677; font-family: 'Tenor Sans', sans-serif; }
.rg-stat-pill b { color: #EFEAE1; font-family: 'JetBrains Mono', monospace; }

/* Ring cards */
.ring-card {
    background: linear-gradient(135deg, rgba(239,234,225,.03), rgba(239,234,225,.005));
    border: 1px solid rgba(192,132,87,.16);
    border-left: 3px solid #C08457;
    border-radius: 12px; padding: 1.1rem 1.3rem; margin-bottom:.9rem; transition: all .3s;
}
.ring-card:hover {
    transform: translateX(5px);
    border-color: rgba(192,132,87,.45);
    box-shadow: 0 10px 32px rgba(0,0,0,.5), -4px 0 20px rgba(192,132,87,.15);
}
.ring-card:nth-child(2) { border-left-color:#5C6B4A !important; }
.ring-card:nth-child(3) { border-left-color:#dca074 !important; }
.ring-card:nth-child(4) { border-left-color:#7d9165 !important; }
.ring-card-header {
    font-family: 'Syne', sans-serif; font-size: .86rem; font-weight: 700;
    color: #EFEAE1; margin-bottom: .5rem; letter-spacing: .02em;
}
.ring-chip {
    display: inline-block; background: rgba(239,234,225,.04);
    border: 1px solid rgba(192,132,87,.18); border-radius: 5px;
    padding: 2px 10px; font-size: .72rem;
    font-family: 'JetBrains Mono', monospace; color: #EFEAE1;
    margin-right: 5px; margin-bottom: 4px;
}
.ring-verdict {
    color: #8f8677; font-size: .84rem; line-height: 1.65;
    border-top: 1px solid rgba(192,132,87,.1);
    padding-top: .6rem; margin-top: .6rem;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.score-bar-bg { background: rgba(239,234,225,.06); border-radius: 3px; height: 4px; overflow: hidden; margin: .4rem 0; }
.score-bar-fill {
    height: 4px; border-radius: 3px;
    background: linear-gradient(90deg,#5C6B4A,#C08457,#dca074);
    animation: rg-bar-grow .8s cubic-bezier(.22,1,.36,1) both; transform-origin: left;
}
.audit-row {
    background: rgba(47,42,34,.5);
    border: 1px solid rgba(192,132,87,.12); border-radius: 10px;
    padding: .8rem 1.1rem; margin-bottom: .5rem;
    font-family: 'JetBrains Mono', monospace; font-size: .74rem; color: #8f8677;
    transition: border-color .2s, background .2s;
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.audit-row:hover { background: rgba(192,132,87,.08); border-color: rgba(192,132,87,.35); }
.audit-row .run-id { color: #C08457; font-weight: 600; min-width: 80px; }
.audit-row .ts { color: #5f574a; min-width: 140px; }
.audit-row .ok { color: #5C6B4A; }
.audit-row .warn { color: #dca074; }

/* ── SIDEBAR BADGES ────────────────────────────────────────────── */
.sidebar-status {
    background: rgba(92,107,74,.16) !important;
    border: 1px solid rgba(92,107,74,.38) !important;
    border-radius: 10px !important;
    padding: .65rem 1rem !important;
    font-size: .76rem !important;
    color: #7d9165 !important;
    margin-top: .5rem !important;
    font-family: 'Tenor Sans', sans-serif !important;
    box-shadow: 0 0 16px rgba(92,107,74,.12) !important;
}
.sidebar-warn {
    background: rgba(192,132,87,.14) !important;
    border: 1px solid rgba(192,132,87,.35) !important;
    border-radius: 10px !important;
    padding: .65rem 1rem !important;
    font-size: .76rem !important;
    color: #C08457 !important;
    margin-top: .5rem !important;
    font-family: 'Tenor Sans', sans-serif !important;
}
.merchant-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.45rem; font-weight: 800; color: #EFEAE1;
    letter-spacing: -.02em;
}
.merchant-sub { font-size: .82rem; color: #8f8677; margin-top: .15rem; font-family: 'Tenor Sans', sans-serif; }
.risk-high { color: #C08457; font-weight: 700; }
.risk-low { color: #5C6B4A; font-weight: 700; }

/* ── ANIMATIONS ─────────────────────────────────────────────────── */
@keyframes rg-fadein-up {
    from { opacity:0; transform:translateY(20px); }
    to   { opacity:1; transform:translateY(0); }
}
@keyframes rg-fadein { from{opacity:0} to{opacity:1} }
@keyframes rg-shimmer {
    0%   { background-position:-200% center; }
    100% { background-position: 200% center; }
}
@keyframes rg-bar-grow { from{transform:scaleX(0)} to{transform:scaleX(1)} }
@keyframes rg-dot-shift {
    0%,100% { background:#5C6B4A; box-shadow:0 0 8px #5C6B4A; }
    33%      { background:#C08457; box-shadow:0 0 10px #C08457; }
    66%      { background:#dca074; box-shadow:0 0 10px #dca074; }
}
@keyframes rg-slide-in {
    from { opacity:0; transform:translateX(-14px); }
    to   { opacity:1; transform:translateX(0); }
}
@keyframes rg-glow-pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(192,132,87,0); }
    50%      { box-shadow: 0 0 24px 4px rgba(192,132,87,.18); }
}

[data-testid="stVerticalBlockBorderWrapper"] { animation:rg-fadein-up .5s cubic-bezier(.22,1,.36,1) both; }
[data-testid="stVerticalBlockBorderWrapper"]:nth-child(1) { animation-delay:.04s; }
[data-testid="stVerticalBlockBorderWrapper"]:nth-child(2) { animation-delay:.1s; }
[data-testid="stVerticalBlockBorderWrapper"]:nth-child(3) { animation-delay:.16s; }
[data-testid="stVerticalBlockBorderWrapper"]:nth-child(4) { animation-delay:.22s; }
[data-testid="metric-container"]:hover { animation:rg-glow-pulse 2.2s ease-in-out infinite !important; }
.ring-card { animation:rg-fadein-up .4s cubic-bezier(.22,1,.36,1) both; }
.audit-row { animation:rg-slide-in .3s cubic-bezier(.22,1,.36,1) both; }
[data-testid="stPlotlyChart"] { animation:rg-fadein .55s ease both; animation-delay:.12s; }
[data-testid="stDataFrame"] { animation:rg-fadein-up .45s ease both; }
[data-testid="stTabs"] { animation:rg-fadein .35s ease both; }
</style>
""", unsafe_allow_html=True)

# ── JS sidebar toggle button — attached directly to parent document ──
st.components.v1.html("""
<script>
(function() {
  var pdoc = (window.parent && window.parent.document) ? window.parent.document : document;

  function initToggle() {
    var btn = pdoc.getElementById("ringguard-sidebar-toggle-btn");
    if (!btn) {
      btn = pdoc.createElement("button");
      btn.id = "ringguard-sidebar-toggle-btn";
      btn.innerHTML = `
        <span style="display:inline-flex;align-items:center;gap:7px;font-family:'Syne',sans-serif;">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#C08457" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
          <span style="font-weight:800;font-size:11px;color:#EFEAE1;letter-spacing:0.08em;text-transform:uppercase;">Sidebar</span>
        </span>
      `;
      btn.style.cssText = `
        position: fixed !important;
        top: 14px !important;
        left: 14px !important;
        z-index: 2147483647 !important;
        background: linear-gradient(135deg, rgba(192,132,87,0.3), rgba(47,42,34,0.96)) !important;
        border: 1px solid rgba(192,132,87,0.5) !important;
        border-radius: 8px !important;
        padding: 6px 13px !important;
        cursor: pointer !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.8), 0 0 12px rgba(192,132,87,0.25) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
        backdrop-filter: blur(10px) !important;
      `;

      btn.onmouseenter = function() {
        btn.style.background = "linear-gradient(135deg, rgba(192,132,87,0.45), rgba(47,42,34,0.96))";
        btn.style.borderColor = "#dca074";
        btn.style.transform = "translateY(-1px) scale(1.03)";
      };
      btn.onmouseleave = function() {
        btn.style.background = "linear-gradient(135deg, rgba(192,132,87,0.3), rgba(47,42,34,0.96))";
        btn.style.borderColor = "rgba(192,132,87,0.5)";
        btn.style.transform = "none";
      };

      btn.onclick = function(e) {
        e.stopPropagation();
        var triggers = pdoc.querySelectorAll(
          '[data-testid="stSidebarCollapseButton"] button,' +
          '[data-testid="stSidebarCollapsedControl"] button,' +
          '[data-testid="collapsedControl"] button,' +
          'button[aria-label*="sidebar" i],' +
          'button[aria-label*="Sidebar" i],' +
          'header button'
        );
        for (var i = 0; i < triggers.length; i++) {
          var t = triggers[i];
          if (t && t.id !== "ringguard-sidebar-toggle-btn") {
            t.click();
            return;
          }
        }
      };

      pdoc.body.appendChild(btn);
    }

    function updateVisibility() {
      var sidebar = pdoc.querySelector('[data-testid="stSidebar"]');
      if (sidebar) {
        var rect = sidebar.getBoundingClientRect();
        if (rect.width > 60 && rect.right > 60) {
          btn.style.display = "none";
        } else {
          btn.style.display = "flex";
        }
      } else {
        btn.style.display = "flex";
      }
    }

    updateVisibility();
    var obs = new MutationObserver(updateVisibility);
    obs.observe(pdoc.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["style", "class", "aria-expanded"] });
  }

  initToggle();
})();
</script>
""", height=0)



# ══════════════════════════════════════════════════════════════════════════
# CACHED DATA LOADERS
# ══════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def load_merchants() -> pd.DataFrame:
    with open(DATA_DIR / "merchants.json") as f:
        data = json.load(f)
    return pd.DataFrame(data)


@st.cache_data(show_spinner=False)
def load_transactions() -> pd.DataFrame:
    with open(DATA_DIR / "transactions.json") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date
    return df


@st.cache_data(show_spinner=False)
def load_returns() -> pd.DataFrame:
    with open(DATA_DIR / "returns.json") as f:
        data = json.load(f)
    return pd.DataFrame(data)


@st.cache_data(show_spinner=False, ttl=10)
def load_audit_log() -> list:
    return get_log()


@st.cache_data(show_spinner=False, ttl=30)
def run_full_detection() -> tuple:
    G, rings, metrics = run_detection()
    rings = analyze_all_rings(rings)
    return rings, metrics


# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════

_DEFAULTS = {
    "selected_merchant": None,
    "risk_threshold": 50,
    "category_filter": "All",
    "last_sync_ts": None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Single source of truth: @st.cache_data with ttl handles freshness.
# session_state only stores the threshold filter, not detection results.
rings, det_metrics = run_full_detection()

# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
<div style="padding: 0.6rem 0 0.8rem 0; display: flex; align-items: center; gap: 12px;">
  <div style="width: 38px; height: 38px; min-width: 38px; border-radius: 10px; background: linear-gradient(135deg, rgba(192,132,87,0.22), rgba(47,42,34,0.95)); border: 1px solid rgba(192,132,87,0.45); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(0,0,0,0.5), inset 0 1px 0 rgba(239,234,225,0.25);">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="9.5" stroke="#C08457" stroke-width="1.3" stroke-dasharray="3 2" opacity="0.65"/>
      <polygon points="12,3 20,7.5 20,16.5 12,21 4,16.5 4,7.5" stroke="#EFEAE1" stroke-width="1.3" fill="none" opacity="0.9"/>
      <circle cx="12" cy="12" r="3.5" fill="url(#rg-core-grad)" stroke="#C08457" stroke-width="1.2"/>
      <circle cx="12" cy="12" r="1.3" fill="#EFEAE1"/>
      <defs>
        <linearGradient id="rg-core-grad" x1="8.5" y1="8.5" x2="15.5" y2="15.5" gradientUnits="userSpaceOnUse">
          <stop stop-color="#C08457"/>
          <stop offset="1" stop-color="#5C6B4A"/>
        </linearGradient>
      </defs>
    </svg>
  </div>
  <div style="flex: 1; min-width: 0;">
    <div style="display: flex; align-items: center; gap: 7px; flex-wrap: nowrap;">
      <span style="font-family:'Syne',sans-serif; font-size:1.15rem; font-weight:800; letter-spacing:-0.02em; color:#EFEAE1; white-space:nowrap;">
        RingGuard
      </span>
      <span style="font-family:'Tenor Sans',sans-serif; font-size:0.58rem; font-weight:700; background:rgba(192,132,87,0.2); border:1px solid rgba(192,132,87,0.45); color:#dca074; padding:1px 6px; border-radius:4px; letter-spacing:0.06em; line-height:1.3;">
        AI
      </span>
    </div>
    <div style="font-family:'Tenor Sans',sans-serif; font-size:0.6rem; color:#8f8677; letter-spacing:0.12em; text-transform:uppercase; font-weight:600; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
      Fraud Intelligence · Track 02
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.divider()

    n_rings = len(rings)
    total_damage = sum(r["total_damage_inr"] for r in rings)
    if n_rings:
        st.markdown(f'<div class="sidebar-status"><b>● LIVE</b> &nbsp;{n_rings} ring(s) active &nbsp;·&nbsp; ₹{total_damage:,} surfaced</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sidebar-warn">◌ No rings detected</div>', unsafe_allow_html=True)

    st.markdown("### ⚙️ Risk Config")
    st.session_state.risk_threshold = st.slider(
        "Min confidence score", 0, 100, st.session_state.risk_threshold, 5,
        help="Only show rings at or above this confidence level"
    )

    merchants_df = load_merchants()
    cats = ["All"] + sorted(merchants_df["category"].unique().tolist())
    st.session_state.category_filter = st.selectbox(
        "Merchant category", cats, index=cats.index(st.session_state.category_filter)
    )

    st.markdown("### 🏪 Quick Select")
    cat = st.session_state.category_filter
    filtered_m = merchants_df if cat == "All" else merchants_df[merchants_df["category"] == cat]
    m_options = ["— none —"] + filtered_m["merchant_id"].tolist()
    sel_idx = m_options.index(st.session_state.selected_merchant) if st.session_state.selected_merchant in m_options else 0
    pick = st.selectbox("Jump to merchant", m_options, index=sel_idx)
    st.session_state.selected_merchant = None if pick == "— none —" else pick

    st.markdown("### 📊 Detection Run")
    if st.session_state.last_sync_ts:
        st.markdown(f"<div style='font-size:.72rem;color:#8f8677'>Last sync: {st.session_state.last_sync_ts}</div>", unsafe_allow_html=True)
    if st.button("🔄 Re-run Detection", use_container_width=True):
        run_full_detection.clear()
        rings, det_metrics = run_full_detection()
        st.session_state.rings = rings
        st.session_state.det_metrics = det_metrics
        st.session_state.last_sync_ts = datetime.now().strftime("%H:%M:%S")
        st.rerun()

    st.divider()
    st.markdown("<div style='font-size:.68rem;color:#5f574a;text-align:center'>Defense-only · No real customer data</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# DATA LOAD
# ══════════════════════════════════════════════════════════════════════════

txns_df = load_transactions()
returns_df = load_returns()
audit_entries = load_audit_log()

total_txns = len(txns_df)
total_fraud_txns = int(txns_df["is_fraud"].sum())
global_risk_rate = total_fraud_txns / total_txns if total_txns else 0
active_rings = [r for r in rings if r["confidence_score"] >= st.session_state.risk_threshold]

# ══════════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="rg-hero">
  <div class="rg-badge"><span class="dot"></span>LIVE · RAZORPAY BUILDATHON · TRACK 02</div>
  <div class="rg-hero-title">RingGuard AI · Risk Monitor</div>
  <div class="rg-hero-sub">Cross-merchant fraud ring detection · Graph clustering + LLM reasoning · Defense-only</div>
  <div class="rg-stat-pill">
    <span>Merchants: <b>{len(merchants_df)}</b></span>
    <span>Transactions: <b>{total_txns:,}</b></span>
    <span>Rings active: <b>{len(active_rings)}</b></span>
    <span>Damage surfaced: <b>₹{total_damage:,}</b></span>
    <span>Audit runs: <b>{len(audit_entries)}</b></span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Ring color palette (module-level so all tabs share it) ───────────────
RING_COLORS = {
    "RING_1": "#f43f5e",   # Rose Coral
    "RING_2": "#10b981",   # Emerald Green
    "RING_3": "#0ea5e9",   # Electric Cyan
    "RING_4": "#f59e0b",   # Solar Amber
    "RING_5": "#a855f7",   # Cyber Purple
}

# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════

tab_overview, tab_graph, tab_explorer, tab_audit = st.tabs([
    "📊  Overview Analytics",
    "🕸️  Ring Network Graph",
    "🏪  Merchant & Risk Explorer",
    "📋  Audit Ledger & Logs",
])


# ──────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW ANALYTICS
# ──────────────────────────────────────────────────────────────────────────

with tab_overview:

    # Row 1: KPIs
    with st.container(border=True):
        st.markdown('<div class="rg-section-label">Key Performance Indicators</div>', unsafe_allow_html=True)
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Transactions", f"{total_txns:,}", delta=f"{total_fraud_txns} flagged", delta_color="inverse")
        k2.metric("Rings Detected", str(len(active_rings)), delta=f"≥{st.session_state.risk_threshold}% confidence", delta_color="off")
        k3.metric("Global Risk Rate", f"{global_risk_rate*100:.2f}%", delta="fraud / total", delta_color="inverse")
        k4.metric("Damage Surfaced", f"₹{total_damage:,}", delta=f"{len(returns_df)} return events", delta_color="inverse")
        k5.metric("Audit Runs", str(len(audit_entries)), delta=f"Prec {det_metrics.get('precision',0)*100:.0f}% · Rec {det_metrics.get('recall',0)*100:.0f}%", delta_color="off")

    st.markdown("<div style='height:.8rem'/>", unsafe_allow_html=True)

    # Row 2: Volume + Category charts
    col_l, col_r = st.columns([3, 2], gap="medium")

    with col_l:
        with st.container(border=True):
            st.markdown('<div class="rg-section-title">📈 Transaction Volume · Last 30 Days</div>', unsafe_allow_html=True)
            daily = txns_df.groupby(["date", "is_fraud"]).agg(count=("txn_id","count")).reset_index()
            legit = daily[~daily["is_fraud"]].set_index("date")["count"]
            fraud = daily[daily["is_fraud"]].set_index("date")["count"]
            all_dates = sorted(txns_df["date"].unique())
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Scatter(x=all_dates, y=legit.reindex(all_dates, fill_value=0), name="Legitimate", mode="lines", line=dict(color="#5C6B4A",width=2.5), fill="tozeroy", fillcolor="rgba(92,107,74,.12)"))
            fig_vol.add_trace(go.Scatter(x=all_dates, y=fraud.reindex(all_dates, fill_value=0), name="Fraudulent", mode="lines+markers", line=dict(color="#C08457",width=2,dash="dot"), marker=dict(size=5,color="#C08457")))
            fig_vol.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),height=220,font=dict(family="Plus Jakarta Sans"),legend=dict(font=dict(color="#8f8677",size=11),bgcolor="rgba(0,0,0,0)",orientation="h",y=1.08),xaxis=dict(showgrid=False,color="#8f8677",tickfont=dict(size=10)),yaxis=dict(gridcolor="rgba(192,132,87,.08)",color="#8f8677",tickfont=dict(size=10)))
            st.plotly_chart(fig_vol, use_container_width=True)

    with col_r:
        with st.container(border=True):
            st.markdown('<div class="rg-section-title">🏷️ Risk by Category</div>', unsafe_allow_html=True)
            merged = txns_df.merge(merchants_df, on="merchant_id")
            cat_risk = merged.groupby("category").agg(total=("txn_id","count"),fraud=("is_fraud","sum")).assign(risk_pct=lambda d: d["fraud"]/d["total"]*100).sort_values("risk_pct",ascending=True).reset_index()
            fig_cat = go.Figure(go.Bar(x=cat_risk["risk_pct"],y=cat_risk["category"],orientation="h",marker=dict(color=cat_risk["risk_pct"],colorscale=[[0,"#2F2A22"],[.35,"#5C6B4A"],[.75,"#C08457"],[1,"#EFEAE1"]],showscale=False),text=[f"{v:.1f}%" for v in cat_risk["risk_pct"]],textposition="outside",textfont=dict(color="#EFEAE1",size=11,family="Tenor Sans")))
            fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=44,t=0,b=0),height=220,font=dict(family="Plus Jakarta Sans"),xaxis=dict(showgrid=False,showticklabels=False),yaxis=dict(color="#C08457",tickfont=dict(size=11,family="Tenor Sans")))
            st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("<div style='height:.8rem'/>", unsafe_allow_html=True)

    # Row 3: Amount histogram + ring damage pie
    col_h, col_p = st.columns([2, 1], gap="medium")

    with col_h:
        with st.container(border=True):
            st.markdown('<div class="rg-section-title">💰 Amount Distribution</div>', unsafe_allow_html=True)
            fig_hist = px.histogram(txns_df,x="amount",color="is_fraud",nbins=40,barmode="overlay",color_discrete_map={True:"rgba(192,132,87,.85)",False:"rgba(92,107,74,.65)"},labels={"is_fraud":"Fraud","amount":"Amount (₹)"},template="plotly_dark")
            fig_hist.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),height=200,font=dict(family="Plus Jakarta Sans"),legend=dict(font=dict(color="#8f8677",size=11),bgcolor="rgba(0,0,0,0)",orientation="h",y=1.08),xaxis=dict(gridcolor="rgba(192,132,87,.08)",color="#8f8677",tickfont=dict(size=10)),yaxis=dict(gridcolor="rgba(192,132,87,.08)",color="#8f8677",tickfont=dict(size=10)))
            st.plotly_chart(fig_hist, use_container_width=True)

    with col_p:
        with st.container(border=True):
            st.markdown('<div class="rg-section-title">🔴 Ring Damage Split</div>', unsafe_allow_html=True)
            if rings:
                pie_colors = [RING_COLORS.get(r["cluster_id"], "#f43f5e") for r in rings]
                fig_pie = go.Figure(go.Pie(
                    labels=[r["cluster_id"] for r in rings],
                    values=[r["total_damage_inr"] for r in rings],
                    hole=.55,
                    marker=dict(
                        colors=pie_colors,
                        line=dict(color="#1a1713", width=2.5)
                    ),
                    textinfo="label+percent",
                    textfont=dict(size=12, color="#ffffff", family="Tenor Sans"),
                    insidetextorientation="radial",
                    pull=[0.04]*len(rings),
                ))
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10,r=10,t=10,b=10),
                    height=200,
                    showlegend=False,
                    hoverlabel=dict(
                        bgcolor="#2F2A22",
                        font_size=12,
                        font_family="Plus Jakarta Sans",
                        font_color="#EFEAE1",
                        bordercolor="rgba(192,132,87,.4)"
                    )
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No rings above threshold.")

    st.markdown("<div style='height:.8rem'/>", unsafe_allow_html=True)

    # Row 4: Ring cards
    with st.container(border=True):
        st.markdown('<div class="rg-section-title">🚨 Active Fraud Rings</div>', unsafe_allow_html=True)
        if not active_rings:
            st.info(f"No rings above {st.session_state.risk_threshold}% confidence.")
        else:
            cols_r = st.columns(min(len(active_rings), 3), gap="medium")
            for i, ring in enumerate(active_rings):
                with cols_r[i % 3]:
                    score = ring["confidence_score"]
                    color = RING_COLORS.get(ring["cluster_id"], "#f43f5e")
                    verdict = ring.get("llm_verdict","Analysis pending.")
                    chips = f'<span class="ring-chip">👥 {ring["member_count"]} members</span><span class="ring-chip">🏪 {ring["merchant_count"]} merchants</span><span class="ring-chip">₹{ring["total_damage_inr"]:,}</span>'
                    st.markdown(f"""
<div class="ring-card" style="border-left: 3px solid {color} !important;">
  <div class="ring-card-header" style="color:{color}">{ring["cluster_id"]} · Score {score}/100</div>
  <div class="score-bar-bg"><div class="score-bar-fill" style="width:{score}%; background:linear-gradient(90deg, {color}, #EFEAE1) !important;"></div></div>
  <div style="margin:.5rem 0">{chips}</div>
  <div class="ring-verdict">🧠 {verdict[:220]}{'…' if len(verdict)>220 else ''}</div>
</div>
""", unsafe_allow_html=True)



# ──────────────────────────────────────────────────────────────────────────
# TAB 2 — RING NETWORK GRAPH
# ──────────────────────────────────────────────────────────────────────────

with tab_graph:
    import networkx as nx

    st.markdown('<div class="rg-section-title">🕸️ Fraud Ring Network Graph</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:.83rem;color:#8f8677;margin-bottom:1rem">'
        'Each fraud ring is color-coded with distinct neon nodes and cluster web lines. '
        'Clusters = rings. Hover any node for details.</div>',
        unsafe_allow_html=True
    )

    RING_COLORS = {
        "RING_1": "#f43f5e",  # Rose Coral
        "RING_2": "#10b981",  # Emerald Green
        "RING_3": "#0ea5e9",  # Electric Cyan
        "RING_4": "#f59e0b",  # Solar Amber
        "RING_5": "#a855f7",  # Cyber Purple
    }

    ctrl_col, info_col = st.columns([3, 1], gap="medium")
    with ctrl_col:
        show_legit = st.toggle("Show legitimate nodes", value=False,
            help="Adds legit transaction nodes for contrast (slower)")
        ring_filter = st.multiselect(
            "Filter rings",
            options=[r["cluster_id"] for r in rings],
            default=[r["cluster_id"] for r in rings],
        )
    with info_col:
        with st.container(border=True):
            st.markdown('<div class="rg-section-label">Legend</div>', unsafe_allow_html=True)
            st.markdown("""
<div style="font-size:.78rem;line-height:2.1;font-family:'Tenor Sans',sans-serif">
  <span style="color:#f43f5e">⬤</span> RING_1 (Rose Coral)<br>
  <span style="color:#10b981">⬤</span> RING_2 (Emerald Green)<br>
  <span style="color:#0ea5e9">⬤</span> RING_3 (Electric Cyan)<br>
  <span style="color:#f59e0b">⬤</span> RING_4 (Solar Amber)<br>
  <span style="color:#64748b">⬤</span> Legitimate<br>
  <span style="color:#EFEAE1">━</span> Strong intra-ring link<br>
  <span style="color:#475569">┄</span> Weak cross-ring link
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:.5rem'/>", unsafe_allow_html=True)

    # ── Build NetworkX graph ──────────────────────────────────────────────
    G_viz = nx.Graph()
    selected_rings = [r for r in rings if r["cluster_id"] in ring_filter]

    for ring in selected_rings:
        members = ring["members"]
        for m in members:
            G_viz.add_node(
                m["txn_id"],
                is_fraud=m.get("is_fraud", False),
                ring_id=ring["cluster_id"],
                merchant=m["merchant_id"],
                amount=m["amount"],
                device=m["device_fingerprint"][:8] + "…",
                bank_bin=m["bank_bin"],
                pin=m["pin"],
            )
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                w = 0
                if members[i]["device_fingerprint"] == members[j]["device_fingerprint"]: w += 3
                if abs(int(members[i]["pin"]) - int(members[j]["pin"])) <= 2: w += 2
                if members[i]["bank_bin"] == members[j]["bank_bin"]: w += 2
                if w >= 3:
                    G_viz.add_edge(members[i]["txn_id"], members[j]["txn_id"], weight=w, ring_id=ring["cluster_id"])

    if show_legit:
        legit_sample = returns_df[~returns_df["is_fraud"]].head(12)
        for _, row in legit_sample.iterrows():
            G_viz.add_node(row["txn_id"], is_fraud=False, ring_id="none",
                merchant=row["merchant_id"], amount=row["amount"],
                device="legit", bank_bin=row["bank_bin"], pin=row["pin"])

    if not G_viz.nodes:
        st.info("Select at least one ring above.")
    else:
        pos = nx.spring_layout(G_viz, seed=42, k=1.8)

        fig_g = go.Figure()

        # Draw intra-ring edges with each ring's specific color
        for ring in selected_rings:
            rid = ring["cluster_id"]
            rc = RING_COLORS.get(rid, "#f43f5e")
            r_members = set(m["txn_id"] for m in ring["members"])
            ex_r, ey_r = [], []
            for u, v, d in G_viz.edges(data=True):
                if u in r_members and v in r_members and u in pos and v in pos:
                    x0, y0 = pos[u]; x1, y1 = pos[v]
                    ex_r += [x0, x1, None]
                    ey_r += [y0, y1, None]
            if ex_r:
                fig_g.add_trace(go.Scatter(
                    x=ex_r, y=ey_r, mode="lines",
                    name=rid,
                    line=dict(color=rc, width=2.4),
                    opacity=0.75,
                    hoverinfo="none",
                    showlegend=False
                ))

        # Draw cross-ring or faint edges
        ex_other, ey_other = [], []
        for u, v, d in G_viz.edges(data=True):
            if u in pos and v in pos:
                u_ring = G_viz.nodes[u].get("ring_id")
                v_ring = G_viz.nodes[v].get("ring_id")
                if u_ring != v_ring or u_ring == "none":
                    x0, y0 = pos[u]; x1, y1 = pos[v]
                    ex_other += [x0, x1, None]
                    ey_other += [y0, y1, None]
        if ex_other:
            fig_g.add_trace(go.Scatter(
                x=ex_other, y=ey_other, mode="lines",
                line=dict(color="rgba(239,234,225,0.18)", width=1, dash="dot"),
                hoverinfo="none",
                showlegend=False
            ))

        # Draw Nodes with distinctive ring colors and crisp glowing borders
        nids = list(G_viz.nodes())
        nx_ = [pos[n][0] for n in nids]
        ny_ = [pos[n][1] for n in nids]
        ncolors = [
            RING_COLORS.get(G_viz.nodes[n].get("ring_id", "none"), "#64748b")
            if G_viz.nodes[n].get("is_fraud") else "#334155"
            for n in nids
        ]
        nsizes = [22 if G_viz.nodes[n].get("is_fraud") else 10 for n in nids]
        nhover = [
            f"<b>{n}</b><br>"
            f"Ring: <b style='color:{RING_COLORS.get(G_viz.nodes[n].get('ring_id'), '#fff')}'>{G_viz.nodes[n].get('ring_id','—')}</b><br>"
            f"Merchant: {G_viz.nodes[n].get('merchant','—')}<br>"
            f"Amount: ₹{G_viz.nodes[n].get('amount',0):,}<br>"
            f"Device: {G_viz.nodes[n].get('device','—')}<br>"
            f"BIN: {G_viz.nodes[n].get('bank_bin','—')}"
            for n in nids
        ]

        fig_g.add_trace(go.Scatter(
            x=nx_, y=ny_, mode="markers",
            marker=dict(
                size=nsizes,
                color=ncolors,
                line=dict(color="#ffffff", width=2),
                opacity=0.95
            ),
            text=nhover,
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        ))

        # Ring centroid labels with matching background pill and white text
        annotations = []
        for ring in selected_rings:
            mnodes = [m["txn_id"] for m in ring["members"] if m["txn_id"] in pos]
            if mnodes:
                cx = sum(pos[n][0] for n in mnodes) / len(mnodes)
                cy = sum(pos[n][1] for n in mnodes) / len(mnodes)
                color = RING_COLORS.get(ring["cluster_id"], "#f43f5e")
                annotations.append(dict(
                    x=cx, y=cy,
                    text=f"<b>{ring['cluster_id']}</b><br>₹{ring['total_damage_inr']:,}",
                    showarrow=False,
                    font=dict(size=12, color="#ffffff", family="Tenor Sans"),
                    bgcolor=color,
                    bordercolor="#ffffff",
                    borderwidth=1.5,
                    borderpad=6,
                    opacity=0.92
                ))

        fig_g.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), height=520,
            font=dict(family="Plus Jakarta Sans"),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            annotations=annotations,
            hoverlabel=dict(bgcolor="#1c1914", bordercolor="rgba(192,132,87,.6)",
                font=dict(color="#EFEAE1", size=12, family="Plus Jakarta Sans")),
        )

        with st.container(border=True):
            st.plotly_chart(fig_g, use_container_width=True)

        # ── Ring breakdown cards ──────────────────────────────────────────
        st.markdown("<div style='height:.5rem'/>", unsafe_allow_html=True)
        st.markdown('<div class="rg-section-title">🔍 Ring Breakdown</div>', unsafe_allow_html=True)

        ring_cols = st.columns(max(len(selected_rings), 1), gap="medium")
        for i, ring in enumerate(selected_rings):
            with ring_cols[i]:
                with st.container(border=True):
                    score = ring["confidence_score"]
                    color = RING_COLORS.get(ring["cluster_id"], "#f43f5e")
                    sig = ring["signals"]
                    st.markdown(
                        f'<div class="ring-card-header" style="color:{color}">'
                        f'{ring["cluster_id"]} · {score}/100</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f'<div class="score-bar-bg">'
                        f'<div class="score-bar-fill" style="width:{score}%;'
                        f'background:linear-gradient(90deg,{color},#EFEAE1)"></div></div>',
                        unsafe_allow_html=True
                    )
                    st.metric("Members", ring["member_count"])
                    st.metric("Merchants hit", ring["merchant_count"])
                    st.metric("Damage", f"₹{ring['total_damage_inr']:,}")
                    st.markdown(
                        f'<div style="margin-top:.4rem">'
                        f'<span class="ring-chip">📱 {sig["unique_devices"]} device</span>'
                        f'<span class="ring-chip">🏦 {sig["unique_bins"]} BIN</span></div>',
                        unsafe_allow_html=True
                    )
                    with st.expander("Merchants hit", expanded=False):
                        for mid in ring["merchants_hit"]:
                            m_name = merchants_df[merchants_df["merchant_id"] == mid]["name"].values
                            st.markdown(f"• `{mid}` {('— ' + m_name[0]) if len(m_name) else ''}")
                    verdict = ring.get("llm_verdict", "")
                    if verdict:
                        st.markdown(
                            f'<div class="ring-verdict">🧠 {verdict[:250]}'
                            f'{"…" if len(verdict) > 250 else ""}</div>',
                            unsafe_allow_html=True
                        )


# ──────────────────────────────────────────────────────────────────────────
# TAB 3 — MERCHANT & RISK EXPLORER
# ──────────────────────────────────────────────────────────────────────────

with tab_explorer:
    st.markdown('<div class="rg-section-title">🏪 Merchant Directory</div>', unsafe_allow_html=True)

    s_col, c_col, r_col = st.columns([3,2,1], gap="small")
    with s_col:
        search_term = st.text_input("Search merchants", placeholder="Name or ID…", label_visibility="collapsed")
    with c_col:
        cats2 = ["All"] + sorted(merchants_df["category"].unique().tolist())
        cat_filter2 = st.selectbox("Category", cats2, index=cats2.index(st.session_state.category_filter), label_visibility="collapsed")
    with r_col:
        if st.button("✕ Clear", use_container_width=True):
            st.session_state.selected_merchant = None
            st.rerun()

    # Build enriched table
    txn_summary = txns_df.groupby("merchant_id").agg(total_txns=("txn_id","count"),total_revenue=("amount","sum"),fraud_txns=("is_fraud","sum")).reset_index()
    txn_summary["risk_rate"] = (txn_summary["fraud_txns"]/txn_summary["total_txns"]*100).round(2)
    merchant_table = merchants_df.merge(txn_summary, on="merchant_id", how="left").fillna(0)
    ring_hit_ids = set(mid for r in rings for mid in r["merchants_hit"])
    merchant_table["in_ring"] = merchant_table["merchant_id"].isin(ring_hit_ids)

    if search_term:
        mask = merchant_table["merchant_id"].str.contains(search_term,case=False) | merchant_table["name"].str.contains(search_term,case=False)
        merchant_table = merchant_table[mask]
    if cat_filter2 != "All":
        merchant_table = merchant_table[merchant_table["category"]==cat_filter2]

    merchant_table = merchant_table.sort_values(["in_ring","risk_rate"],ascending=[False,False])

    pane_list, pane_detail = st.columns([2,3], gap="medium")

    with pane_list:
        with st.container(border=True):
            st.markdown(f'<div class="rg-section-label">{len(merchant_table)} merchants</div>', unsafe_allow_html=True)
            display_df = merchant_table[["merchant_id","name","category","total_txns","fraud_txns","risk_rate","in_ring"]].copy()
            display_df.columns = ["ID","Name","Category","Txns","Fraud","Risk%","In Ring"]
            display_df["In Ring"] = display_df["In Ring"].map({True:"🔴 YES",False:"✅ No"})
            st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)
            if st.session_state.selected_merchant:
                st.markdown(f"<div style='font-size:.75rem;color:#C08457;margin-top:.3rem;font-family:Tenor Sans,sans-serif'>Showing: {st.session_state.selected_merchant}</div>", unsafe_allow_html=True)

    with pane_detail:
        sel_id = st.session_state.selected_merchant
        if not sel_id:
            with st.container(border=True):
                st.markdown('<div style="padding:3rem 2rem;text-align:center;color:#8f8677"><div style="font-size:2rem;margin-bottom:.5rem">🏪</div><div style="font-size:.9rem;font-family:Tenor Sans,sans-serif">Select a merchant from the sidebar or use Quick Select</div></div>', unsafe_allow_html=True)
        else:
            m_row = merchants_df[merchants_df["merchant_id"]==sel_id]
            if m_row.empty:
                st.warning(f"Merchant {sel_id} not found.")
            else:
                m_info = m_row.iloc[0]
                m_txns = txns_df[txns_df["merchant_id"]==sel_id].sort_values("timestamp",ascending=False)
                m_fraud = int(m_txns["is_fraud"].sum())
                m_revenue = int(m_txns["amount"].sum())
                m_risk = m_fraud/len(m_txns)*100 if len(m_txns) else 0
                m_in_ring = sel_id in ring_hit_ids

                with st.container(border=True):
                    status_html = '<span class="risk-high">⚠ In active fraud ring</span>' if m_in_ring else '<span class="risk-low">✓ Clean</span>'
                    st.markdown(f'<div class="merchant-header">{m_info["name"]}</div><div class="merchant-sub">{sel_id} · {m_info["category"].title()} · {status_html}</div>', unsafe_allow_html=True)
                    st.markdown("<div style='height:.5rem'/>", unsafe_allow_html=True)

                    mk1,mk2,mk3,mk4 = st.columns(4)
                    mk1.metric("Transactions", f"{len(m_txns):,}")
                    mk2.metric("Revenue", f"₹{m_revenue:,}")
                    mk3.metric("Fraud Txns", str(m_fraud), delta=f"{m_risk:.1f}% risk rate", delta_color="inverse")
                    mk4.metric("Ring Status","EXPOSED" if m_in_ring else "CLEAN", delta="Hit by ring" if m_in_ring else "No ring", delta_color="inverse" if m_in_ring else "normal")

                    st.markdown("<div style='height:.4rem'/>", unsafe_allow_html=True)

                    if not m_txns.empty:
                        m_daily = m_txns.groupby(["date","is_fraud"])["amount"].sum().reset_index()
                        m_l = m_daily[~m_daily["is_fraud"]].set_index("date")["amount"]
                        m_fd = m_daily[m_daily["is_fraud"]].set_index("date")["amount"]
                        all_d = sorted(m_txns["date"].unique())
                        fig_m = go.Figure()
                        fig_m.add_trace(go.Bar(x=all_d,y=m_l.reindex(all_d,fill_value=0),name="Legitimate",marker_color="rgba(92,107,74,.7)"))
                        fig_m.add_trace(go.Bar(x=all_d,y=m_fd.reindex(all_d,fill_value=0),name="Fraud",marker_color="rgba(192,132,87,.85)"))
                        fig_m.update_layout(barmode="stack",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),height=160,font=dict(family="Plus Jakarta Sans"),legend=dict(font=dict(color="#8f8677",size=10),bgcolor="rgba(0,0,0,0)",orientation="h",y=1.1),xaxis=dict(showgrid=False,color="#8f8677",tickfont=dict(size=9)),yaxis=dict(gridcolor="rgba(192,132,87,.08)",color="#8f8677",tickfont=dict(size=9)))
                        st.plotly_chart(fig_m, use_container_width=True)

                    if m_in_ring:
                        with st.expander("🔴 Fraud ring involvement", expanded=True):
                            for ring in rings:
                                if sel_id in ring["merchants_hit"]:
                                    st.markdown(f"**{ring['cluster_id']}** · Confidence: `{ring['confidence_score']}/100` · Members: `{ring['member_count']}` · Damage: `₹{ring['total_damage_inr']:,}`\n\n> {ring.get('llm_verdict','')[:280]}")

                    with st.expander("📋 Transaction history (latest 50)", expanded=False):
                        st.dataframe(m_txns[["txn_id","customer_name","amount","timestamp","is_fraud","bank_bin"]].head(50), use_container_width=True, hide_index=True, height=260)


# ──────────────────────────────────────────────────────────────────────────
# TAB 4 — AUDIT LEDGER & LOGS
# ──────────────────────────────────────────────────────────────────────────

with tab_audit:

    @st.fragment
    def audit_sync_panel():
        sc1, sc2 = st.columns([2,1], gap="small")
        with sc1:
            with st.container(border=True):
                st.markdown('<div class="rg-section-label">Sync Controls</div>', unsafe_allow_html=True)
                a1, a2 = st.columns(2)
                with a1:
                    if st.button("⚡ Run Audit Sync", use_container_width=True):
                        with st.spinner("Running detection pipeline…"):
                            time.sleep(0.3)
                            G, rng, mtx = run_detection()
                            rng = analyze_all_rings(rng)
                            entry = log_detection(rng, mtx, source="manual_ui")
                            load_audit_log.clear()
                        st.success(f"✓ {entry['run_id']} complete · {len(rng)} ring(s) logged")
                with a2:
                    if st.button("🧹 Clear Cache", use_container_width=True):
                        run_full_detection.clear()
                        load_audit_log.clear()
                        st.info("Cache cleared.")
        with sc2:
            with st.container(border=True):
                st.markdown('<div class="rg-section-label">Detection Health</div>', unsafe_allow_html=True)
                st.metric("Precision", f"{det_metrics.get('precision',0)*100:.0f}%")
                st.metric("Recall", f"{det_metrics.get('recall',0)*100:.0f}%")
                st.metric("FP Cost", f"₹{det_metrics.get('false_positive_cost_inr',0):,}")

    audit_sync_panel()

    st.markdown("<div style='height:.8rem'/>", unsafe_allow_html=True)

    search_audit = st.text_input("Filter logs", placeholder="Search by run ID, source, or ring count…", label_visibility="collapsed")
    audit_entries_fresh = load_audit_log()

    if audit_entries_fresh:
        flat_rows = []
        for e in audit_entries_fresh:
            flat_rows.append({
                "Run ID": e["run_id"],
                "Timestamp": e["timestamp"][:19].replace("T"," "),
                "Source": e.get("source","auto"),
                "Rings": e["rings_detected"],
                "Precision": f"{e['metrics'].get('precision',0)*100:.0f}%",
                "Recall": f"{e['metrics'].get('recall',0)*100:.0f}%",
                "FP Cost ₹": e["metrics"].get("false_positive_cost_inr",0),
                "Fraud Returns": e["metrics"].get("detected_fraud_returns",0),
            })
        audit_df = pd.DataFrame(flat_rows)
        if search_audit:
            mask = audit_df.apply(lambda row: search_audit.lower() in row.astype(str).str.lower().str.cat(), axis=1)
            audit_df = audit_df[mask]

        with st.container(border=True):
            st.markdown(f'<div class="rg-section-label">{len(audit_df)} log entries</div>', unsafe_allow_html=True)
            st.dataframe(audit_df, use_container_width=True, hide_index=True, height=280)

        st.markdown("<div style='height:.5rem'/>", unsafe_allow_html=True)
        st.markdown('<div class="rg-section-title">🕐 Run Timeline</div>', unsafe_allow_html=True)

        for entry in reversed(audit_entries_fresh[-20:]):
            m = entry["metrics"]
            prec = m.get("precision",0)
            status_cls = "ok" if prec >= 0.9 else "warn"
            status_sym = "✓" if prec >= 0.9 else "⚠"
            ring_ids = ", ".join(r["cluster_id"] for r in entry.get("ring_summary",[])[:3])
            st.markdown(f"""
<div class="audit-row">
  <span class="run-id">{entry['run_id']}</span>
  <span class="ts">{entry['timestamp'][:19].replace('T',' ')}</span>
  <span class="{status_cls}">{status_sym} {prec*100:.0f}% prec</span>
  <span>Recall: <b>{m.get('recall',0)*100:.0f}%</b></span>
  <span>Rings: <b>{entry['rings_detected']}</b></span>
  <span style="color:#8f8677">{ring_ids}</span>
  <span style="margin-left:auto;color:#5f574a;font-size:.7rem">{entry.get('source','auto')}</span>
</div>
""", unsafe_allow_html=True)

        with st.expander("🔍 Inspect latest raw log (JSON)", expanded=False):
            st.json(audit_entries_fresh[-1])
    else:
        st.info("No audit entries yet. Click **Run Audit Sync** to generate the first log.")

    st.markdown("<div style='height:1rem'/>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("""
<div style="display:flex;align-items:flex-start;gap:12px;padding:.4rem .2rem">
  <div style="font-size:1.4rem">🔒</div>
  <div>
    <div style="font-size:.8rem;font-weight:600;color:#C08457;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.3rem;font-family:'Tenor Sans',sans-serif">Defense-Only Policy</div>
    <div style="font-size:.82rem;color:#8f8677;line-height:1.6">
      RingGuard detects and surfaces fraud rings. It <b style="color:#EFEAE1">never</b> blocks transactions,
      penalises customers, or exposes raw PII. All data shown is synthetic.
      Audit logs are append-only and include false-positive cost for honest reporting.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
