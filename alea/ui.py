"""Habillage de l'interface : styles, animations, parcours, visite guidée et guide utilisateur.

Tout le visuel vit ici ; app.py n'appelle que des fonctions. Les animations n'utilisent que
transform et opacity, et se désactivent si le système demande de réduire les animations.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

ACCENT = "#1d4e74"
AMBER = "#b7791f"
INK = "#1b1f24"
MUTED = "#5b6470"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --al-accent: #1d4e74; --al-accent-soft: #e3ecf3; --al-amber: #b7791f; --al-amber-soft: #f6ead6;
  --al-ink: #1b1f24; --al-muted: #5b6470; --al-line: #e4e1da; --al-bg: #f7f6f3; --al-card: #fffefb;
  --al-ease: cubic-bezier(.22,1,.36,1);
}
html, body, [class*="css"], .stMarkdown, .stText, label, p, li { font-family: 'IBM Plex Sans', system-ui, sans-serif; }
h1, h2, h3, h4, .al-hero h1 { font-family: 'Outfit', system-ui, sans-serif !important; letter-spacing: -0.02em; }
[data-testid="stMetricValue"], .al-num, code, [data-testid="stDataFrame"] { font-variant-numeric: tabular-nums; }
[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; font-weight: 500; }

/* Fond : grain discret, pas d'aplat */
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 500px at 85% -10%, rgba(29,78,116,0.07), transparent 60%),
    radial-gradient(900px 400px at -10% 110%, rgba(183,121,31,0.05), transparent 60%),
    var(--al-bg);
}
[data-testid="stAppViewContainer"]::after {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .035;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
}
[data-testid="stMainBlockContainer"] { max-width: 1240px; padding-top: 1.4rem; }
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
  background: var(--al-card); border-radius: 16px; border-color: var(--al-line) !important;
  box-shadow: 0 16px 36px -30px rgba(29,78,116,.55); }
[data-testid="stExpander"] details { border: 0; border-radius: 12px; background: rgba(29,78,116,.045); }
[data-testid="stExpander"] summary { font-size: .9rem; color: var(--al-accent); }
[data-testid="stExpander"] summary:hover { color: var(--al-ink); }
[data-testid="stDataFrame"], [data-testid="stDataFrameResizable"] { border-radius: 12px; overflow: hidden; }
[data-testid="stAlert"] { border-radius: 12px; }
div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stTextArea textarea { border-radius: 10px !important; }
.stButton > button[kind="primary"] { background: linear-gradient(180deg, #24597f, #1d4e74); border: 0; }
.stButton > button[kind="primary"]:hover { background: linear-gradient(180deg, #2a6690, #1f537a); }

/* Entrée en cascade des blocs */
@keyframes alFadeUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"],
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
  animation: alFadeUp .55s var(--al-ease) both;
}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > *:nth-child(2) { animation-delay: .05s; }
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > *:nth-child(3) { animation-delay: .10s; }
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > *:nth-child(4) { animation-delay: .15s; }
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > *:nth-child(5) { animation-delay: .20s; }
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > *:nth-child(n+6) { animation-delay: .25s; }

/* Boutons : survol, appui, focus visible */
.stButton > button, .stDownloadButton > button {
  border-radius: 10px; font-weight: 500; transition: transform .18s var(--al-ease), box-shadow .18s, background .18s;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 18px -8px rgba(29,78,116,.45); }
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(1px) scale(.985); }
.stButton > button:focus-visible { outline: 2px solid var(--al-accent); outline-offset: 2px; }

/* Indicateurs */
[data-testid="stMetric"] {
  background: var(--al-card); border-radius: 14px; padding: 14px 16px; border: 1px solid var(--al-line);
  box-shadow: 0 1px 0 rgba(29,78,116,.04), 0 10px 24px -18px rgba(29,78,116,.35);
  transition: transform .2s var(--al-ease);
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); }
[data-testid="stMetricLabel"] p { color: var(--al-muted); font-size: .82rem; }

/* Barre latérale */
[data-testid="stSidebar"] { background: #f1efea; border-right: 1px solid var(--al-line); }
[data-testid="stSidebar"] [role="radiogroup"] { gap: 2px; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  position: relative; border-radius: 10px; padding: 9px 12px 9px 14px; margin: 0; width: 100%;
  transition: background .2s var(--al-ease), transform .2s var(--al-ease);
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) { display: none; }
[data-testid="stSidebar"] [role="radiogroup"] label::before { content: ""; position: absolute; left: 4px; top: 9px; bottom: 9px;
  width: 3px; border-radius: 3px; background: var(--al-accent); transform: scaleY(0); transition: transform .25s var(--al-ease); }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"]::before { transform: scaleY(1); }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] { background: var(--al-accent-soft); }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p { font-weight: 600; color: var(--al-ink); }
[data-testid="stSidebar"] [data-testid="stRadioOption"] p { font-size: .93rem; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { transform: translateX(2px); }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(29,78,116,.07); }

.al-brand { display: flex; gap: 10px; align-items: center; margin: 4px 0 2px; }
.al-brand b { font-family: 'Outfit'; font-size: 1.55rem; letter-spacing: -0.03em; color: var(--al-ink); }
.al-brand small { display: block; color: var(--al-muted); font-size: .78rem; margin-top: -2px; }

/* En-tête d'étape */
.al-hero { position: relative; padding: 4px 0 6px; }
.al-kicker { display: inline-flex; gap: 8px; align-items: center; font: 500 .78rem 'IBM Plex Mono', monospace;
  color: var(--al-accent); letter-spacing: .04em; }
.al-kicker i { width: 22px; height: 2px; background: var(--al-accent); display: inline-block;
  transform-origin: left; animation: alGrow .7s var(--al-ease) both; }
@keyframes alGrow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.al-hero h1 { font-size: 2.15rem; line-height: 1.12; margin: 6px 0 6px; font-weight: 600; color: var(--al-ink); }
.al-hero p.lead { color: var(--al-muted); max-width: 68ch; font-size: 1.02rem; margin: 0 0 12px; text-wrap: pretty; }
.al-roles { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 4px; }
.al-role { font-size: .84rem; padding: 6px 10px; border-radius: 8px; background: var(--al-card); border: 1px solid var(--al-line); }
.al-role b { font-weight: 600; margin-right: 4px; }
.al-role.ia b { color: var(--al-accent); }
.al-role.you b { color: var(--al-amber); }

/* Parcours */
.al-steps { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; margin: 0 0 26px; padding: 14px 16px 12px;
  background: rgba(255,254,251,.75); backdrop-filter: blur(8px); border: 1px solid var(--al-line); border-radius: 14px; }
.al-step { position: relative; padding-top: 14px; font-size: .76rem; color: var(--al-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.al-step::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 6px; border-radius: 6px; background: #e8e4dc; }
.al-step::after { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 6px; border-radius: 6px;
  background: var(--al-accent); transform: scaleX(0); transform-origin: left; }
.al-step.done::after { transform: scaleX(1); transition: transform .6s var(--al-ease); }
.al-step.current::after { transform: scaleX(1); background: linear-gradient(90deg, var(--al-amber), #d9a557, var(--al-amber));
  background-size: 200% 100%; animation: alShimmer 2.2s linear infinite; }
@keyframes alShimmer { from { background-position: 200% 0; } to { background-position: 0 0; } }
.al-step.done { color: var(--al-accent); }
@keyframes alPulse { 0%,100% { opacity: 1; } 50% { opacity: .45; } }
.al-step.current { color: var(--al-ink); font-weight: 600; }
.al-step span { font-family: 'IBM Plex Mono'; margin-right: 4px; }

/* Bandeau d'accueil */
@property --al-n { syntax: '<integer>'; inherits: false; initial-value: 0; }
.al-intro { position: relative; overflow: hidden; border-radius: 22px; padding: 30px 32px 26px; color: #f4f1ea;
  background: radial-gradient(700px 300px at 90% 0%, rgba(183,121,31,.28), transparent 60%),
              linear-gradient(135deg, #163f5e 0%, #1d4e74 55%, #23608c 100%);
  box-shadow: 0 30px 60px -40px rgba(22,63,94,.9); display: grid; grid-template-columns: 1.15fr 1fr; gap: 26px; align-items: center; }
.al-intro::after { content: ""; position: absolute; inset: 0; opacity: .08; pointer-events: none; background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
.al-intro h2 { font-family: 'Outfit'; font-weight: 600; font-size: 2rem; line-height: 1.1; letter-spacing: -0.025em; margin: 6px 0 10px; color: #fff; }
.al-intro p { color: rgba(244,241,234,.82); max-width: 52ch; margin: 0 0 18px; }
.al-intro .al-kicker { color: #e8c48a; } .al-intro .al-kicker i { background: #e8c48a; }
.al-proof { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.al-proof div { border-left: 1px solid rgba(255,255,255,.18); padding-left: 12px; }
.al-proof b { display: block; font: 600 1.7rem 'IBM Plex Mono'; color: #fff; }
.al-proof b.count { counter-reset: n var(--al-n); animation: alCount 1.6s var(--al-ease) .3s both; }
.al-proof b.count::before { content: counter(n); }
@keyframes alCount { from { --al-n: 0; } to { --al-n: var(--to); } }
.al-proof small { color: rgba(244,241,234,.7); font-size: .78rem; }
.al-intro .al-art { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.14); border-radius: 16px; padding: 10px; }
.al-intro .al-art svg { width: 100%; height: auto; }
@media (max-width: 900px) { .al-intro { grid-template-columns: 1fr; } }

/* Carte d'accueil */
.al-welcome { display: grid; grid-template-columns: 1.25fr 1fr; gap: 18px; align-items: center;
  background: var(--al-card); border: 1px solid var(--al-line); border-radius: 18px; padding: 22px 24px;
  box-shadow: 0 18px 40px -30px rgba(29,78,116,.5); }
.al-welcome h3 { margin: 0 0 6px; font-size: 1.35rem; }
.al-welcome p { color: var(--al-muted); margin: 0 0 8px; }
.al-welcome ol { margin: 0; padding-left: 18px; color: var(--al-ink); font-size: .92rem; }
@media (max-width: 900px) { .al-welcome { grid-template-columns: 1fr; } .al-steps { grid-template-columns: repeat(4,1fr); } }

/* Visite guidée */
.al-tour-art { background: linear-gradient(180deg, #fbfaf7, #f2f0ea); border: 1px solid var(--al-line); border-radius: 14px;
  display: flex; justify-content: center; padding: 10px; margin-bottom: 12px; }
.al-tour-art svg { width: 100%; max-width: 680px; height: auto; }
.al-dots { display: flex; gap: 6px; justify-content: center; margin: 4px 0 10px; }
.al-dots i { width: 8px; height: 8px; border-radius: 99px; background: var(--al-line); transition: width .3s var(--al-ease); }
.al-dots i.on { width: 22px; background: var(--al-accent); }

/* Dessins animés (SVG) */
.al-draw { stroke-dasharray: 600; stroke-dashoffset: 600; animation: alDraw 2.2s var(--al-ease) forwards; }
.al-draw.d2 { animation-delay: .5s; } .al-draw.d3 { animation-delay: 1s; } .al-draw.d4 { animation-delay: 1.6s; }
@keyframes alDraw { to { stroke-dashoffset: 0; } }
.al-pop { transform-box: fill-box; transform-origin: center; animation: alPop .5s var(--al-ease) both; }
.al-pop.p1 { animation-delay: .3s; } .al-pop.p2 { animation-delay: .6s; } .al-pop.p3 { animation-delay: .9s; }
.al-pop.p4 { animation-delay: 1.2s; } .al-pop.p5 { animation-delay: 1.5s; } .al-pop.p6 { animation-delay: 1.8s; }
@keyframes alPop { from { opacity: 0; transform: scale(.4); } to { opacity: 1; transform: none; } }
.al-slide { animation: alSlide 1.1s var(--al-ease) both; } .al-slide.s2 { animation-delay: .25s; } .al-slide.s3 { animation-delay: .5s; }
@keyframes alSlide { from { opacity: 0; transform: translateX(-40px); } to { opacity: 1; transform: none; } }
.al-scan { animation: alScan 2.4s ease-in-out infinite; }
@keyframes alScan { 0% { transform: translateY(0); } 50% { transform: translateY(96px); } 100% { transform: translateY(0); } }
.al-flash { animation: alFlash 2.4s ease-in-out infinite; }
@keyframes alFlash { 0%,40% { fill: #fffefb; } 55%,75% { fill: #f6ead6; } 100% { fill: #e3ecf3; } }
.al-fly { animation: alFly 2.6s var(--al-ease) infinite; }
.al-fly.f2 { animation-delay: .5s; } .al-fly.f3 { animation-delay: 1s; }
@keyframes alFly { 0% { opacity: 0; transform: translate(0,0); } 20% { opacity: 1; } 80% { opacity: 1; } 100% { opacity: 0; transform: translate(var(--dx), var(--dy)); } }
.al-breathe { transform-box: fill-box; transform-origin: center; animation: alBreathe 2.6s ease-in-out infinite; }
@keyframes alBreathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.08); } }

/* Guide utilisateur */
.al-guide-step { display: grid; grid-template-columns: 56px 1fr; gap: 14px; padding: 16px 0; border-top: 1px solid var(--al-line); }
.al-guide-step .n { font: 600 1.6rem 'Outfit'; color: var(--al-accent); }
.al-guide-step h4 { margin: 0 0 4px; font-size: 1.08rem; }
.al-guide-step p { margin: 0 0 6px; color: var(--al-muted); max-width: 72ch; }
.al-term { padding: 10px 0; border-top: 1px solid var(--al-line); }
.al-term b { font-family: 'Outfit'; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .al-draw { stroke-dashoffset: 0; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    tpl = go.layout.Template()
    tpl.layout = go.Layout(
        font=dict(family="IBM Plex Sans, system-ui, sans-serif", color=INK, size=13),
        colorway=[ACCENT, AMBER, "#8a929c", "#7fa7c6", "#4f8a5b"],
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#e9e6df", zerolinecolor="#e4e1da", linecolor="#d8d4cb"),
        yaxis=dict(gridcolor="#e9e6df", zerolinecolor="#e4e1da", linecolor="#d8d4cb"),
        legend=dict(bgcolor="rgba(255,254,251,.85)", bordercolor="#e4e1da", borderwidth=1),
        hoverlabel=dict(font_family="IBM Plex Mono", bgcolor="#fffefb"),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    pio.templates["alea"] = tpl
    pio.templates.default = "plotly_white+alea"


def brand() -> None:
    st.markdown(
        """<div class="al-brand"><svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
        <rect x="1" y="1" width="32" height="32" rx="9" fill="#1d4e74"/>
        <path class="al-draw" d="M7 24 C 12 23, 15 21, 18 17 S 24 9, 27 8" stroke="#f6ead6" stroke-width="2.4" fill="none" stroke-linecap="round"/>
        <circle class="al-pop p3" cx="27" cy="8" r="2.4" fill="#b7791f"/></svg>
        <div><b>Aléa</b><small>L'IA prépare, l'actuaire décide.</small></div></div>""",
        unsafe_allow_html=True)


def nav_done(done: list[bool]) -> None:
    """Coche les étapes terminées dans la navigation, sans toucher aux libellés du widget."""
    rules = "".join(
        f'[data-testid="stSidebar"] [role="radiogroup"] > div:nth-child({i + 1}) [data-testid="stRadioOption"] p::after'
        '{content:"✓";margin-left:8px;color:#1d4e74;font-weight:600;}'
        for i, d in enumerate(done) if d)
    if rules:
        st.markdown(f"<style>{rules}</style>", unsafe_allow_html=True)


def stepper(labels: list[str], current: int, done: list[bool]) -> None:
    items = []
    for i, lab in enumerate(labels):
        cls = "current" if i == current else ("done" if done[i] else "")
        name = lab.split(". ", 1)[-1]
        items.append(f'<div class="al-step {cls}"><span>{i + 1:02d}</span>{name}</div>')
    st.markdown(f'<nav class="al-steps" aria-label="Parcours">{"".join(items)}</nav>', unsafe_allow_html=True)


def hero(n: int, title: str, lead: str, ia: str, you: str) -> None:
    st.markdown(
        f"""<header class="al-hero"><div class="al-kicker"><i></i>ÉTAPE {n:02d} / 07</div>
        <h1>{title}</h1><p class="lead">{lead}</p>
        <div class="al-roles"><div class="al-role ia"><b>L'IA</b>{ia}</div>
        <div class="al-role you"><b>Vous</b>{you}</div></div></header>""",
        unsafe_allow_html=True)


# ------------------------------------------------------------------ illustrations animées
ART = {
    "welcome": """<svg viewBox="0 0 440 200" role="img" aria-label="Courbe de mortalité qui se dessine">
      <line x1="40" y1="170" x2="410" y2="170" stroke="#d8d4cb"/><line x1="40" y1="20" x2="40" y2="170" stroke="#d8d4cb"/>
      <path class="al-draw" d="M40 160 C 120 158, 200 150, 260 120 S 360 50, 410 30" stroke="#b7791f" stroke-width="2" stroke-dasharray="6 6" fill="none" opacity=".7"/>
      <path class="al-draw d2" d="M40 166 C 130 164, 210 158, 270 135 S 365 72, 410 52" stroke="#1d4e74" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <circle class="al-pop p2" cx="120" cy="163" r="4" fill="#1d4e74"/><circle class="al-pop p3" cx="200" cy="157" r="4" fill="#1d4e74"/>
      <circle class="al-pop p4" cx="270" cy="134" r="4" fill="#1d4e74"/><circle class="al-pop p5" cx="340" cy="94" r="4" fill="#1d4e74"/>
      <text x="60" y="34" font-family="IBM Plex Mono" font-size="11" fill="#b7791f">— table de référence</text>
      <text x="60" y="52" font-family="IBM Plex Mono" font-size="11" fill="#1d4e74">— table locale</text></svg>""",
    "columns": """<svg viewBox="0 0 440 200" role="img" aria-label="Colonnes reconnues et alignées">
      <g font-family="IBM Plex Mono" font-size="11">
      <rect class="al-slide" x="20" y="30" width="120" height="26" rx="6" fill="#fffefb" stroke="#d8d4cb"/><text class="al-slide" x="30" y="47" fill="#5b6470">DOB</text>
      <rect class="al-slide s2" x="20" y="86" width="120" height="26" rx="6" fill="#fffefb" stroke="#d8d4cb"/><text class="al-slide s2" x="30" y="103" fill="#5b6470">Genre</text>
      <rect class="al-slide s3" x="20" y="142" width="120" height="26" rx="6" fill="#fffefb" stroke="#d8d4cb"/><text class="al-slide s3" x="30" y="159" fill="#5b6470">sum_insured</text>
      <path class="al-draw d2" d="M140 43 C 200 43, 230 43, 290 43" stroke="#1d4e74" stroke-width="2" fill="none"/>
      <path class="al-draw d3" d="M140 99 C 200 99, 230 99, 290 99" stroke="#1d4e74" stroke-width="2" fill="none"/>
      <path class="al-draw d4" d="M140 155 C 200 155, 230 155, 290 155" stroke="#1d4e74" stroke-width="2" fill="none"/>
      <rect class="al-pop p3" x="290" y="30" width="130" height="26" rx="6" fill="#e3ecf3"/><text class="al-pop p3" x="300" y="47" fill="#1d4e74">date de naissance</text>
      <rect class="al-pop p4" x="290" y="86" width="130" height="26" rx="6" fill="#e3ecf3"/><text class="al-pop p4" x="300" y="103" fill="#1d4e74">sexe</text>
      <rect class="al-pop p5" x="290" y="142" width="130" height="26" rx="6" fill="#e3ecf3"/><text class="al-pop p5" x="300" y="159" fill="#1d4e74">capital assuré</text></g></svg>""",
    "quality": """<svg viewBox="0 0 440 200" role="img" aria-label="Lignes contrôlées une à une">
      <g><rect x="70" y="30" width="300" height="20" rx="5" fill="#fffefb" stroke="#e4e1da"/>
      <rect class="al-flash" x="70" y="58" width="300" height="20" rx="5" stroke="#e4e1da"/>
      <rect x="70" y="86" width="300" height="20" rx="5" fill="#fffefb" stroke="#e4e1da"/>
      <rect class="al-flash" style="animation-delay:.8s" x="70" y="114" width="300" height="20" rx="5" stroke="#e4e1da"/>
      <rect x="70" y="142" width="300" height="20" rx="5" fill="#fffefb" stroke="#e4e1da"/></g>
      <rect class="al-scan" x="62" y="26" width="316" height="28" rx="7" fill="rgba(29,78,116,.10)" stroke="#1d4e74"/>
      <g font-family="IBM Plex Mono" font-size="10" fill="#b7791f"><text x="380" y="72">doublon</text><text x="380" y="128">âge &gt; 100</text></g></svg>""",
    "pool": """<svg viewBox="0 0 440 200" role="img" aria-label="Assureurs partageant des agrégats">
      <circle cx="220" cy="100" r="34" fill="#e3ecf3" class="al-breathe"/><text x="220" y="104" text-anchor="middle" font-family="Outfit" font-size="13" fill="#1d4e74">marché</text>
      <g font-family="IBM Plex Mono" font-size="11" fill="#5b6470" text-anchor="middle">
      <circle cx="60" cy="50" r="22" fill="#fffefb" stroke="#d8d4cb"/><text x="60" y="54">A</text>
      <circle cx="60" cy="160" r="22" fill="#fffefb" stroke="#d8d4cb"/><text x="60" y="164">B</text>
      <circle cx="380" cy="100" r="22" fill="#fffefb" stroke="#d8d4cb"/><text x="380" y="104">C</text></g>
      <rect class="al-fly" style="--dx:120px;--dy:40px" x="82" y="46" width="10" height="10" rx="2" fill="#1d4e74"/>
      <rect class="al-fly f2" style="--dx:120px;--dy:-48px" x="82" y="150" width="10" height="10" rx="2" fill="#1d4e74"/>
      <rect class="al-fly f3" style="--dx:-112px;--dy:0px" x="348" y="95" width="10" height="10" rx="2" fill="#1d4e74"/>
      <text x="220" y="185" text-anchor="middle" font-family="IBM Plex Mono" font-size="10" fill="#5b6470">seuls des comptages agrégés circulent</text></svg>""",
    "price": """<svg viewBox="0 0 440 200" role="img" aria-label="Combinaison de deux courbes et prime">
      <path class="al-draw" d="M40 150 C 140 140, 240 110, 400 60" stroke="#8a929c" stroke-width="2" fill="none"/>
      <path class="al-draw d2" d="M40 165 C 140 150, 240 90, 400 30" stroke="#7fa7c6" stroke-width="2" fill="none" stroke-dasharray="4 5"/>
      <path class="al-draw d3" d="M40 157 C 140 145, 240 100, 400 45" stroke="#1d4e74" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <g font-family="IBM Plex Mono" font-size="11"><text x="300" y="80" fill="#8a929c">marché</text><text x="250" y="40" fill="#7fa7c6">propre</text>
      <rect class="al-pop p5" x="60" y="20" width="150" height="40" rx="8" fill="#fffefb" stroke="#e4e1da"/>
      <text class="al-pop p5" x="72" y="37" fill="#5b6470">prime annuelle</text><text class="al-pop p6" x="72" y="53" fill="#1d4e74" font-weight="500">18 584 FCFA</text></g></svg>""",
    "sign": """<svg viewBox="0 0 440 200" role="img" aria-label="Note technique signée">
      <rect x="120" y="14" width="200" height="172" rx="10" fill="#fffefb" stroke="#e4e1da"/>
      <path class="al-draw" d="M140 44 H300" stroke="#d8d4cb" stroke-width="6" stroke-linecap="round"/>
      <path class="al-draw d2" d="M140 64 H280" stroke="#d8d4cb" stroke-width="6" stroke-linecap="round"/>
      <path class="al-draw d2" d="M140 84 H295" stroke="#d8d4cb" stroke-width="6" stroke-linecap="round"/>
      <path class="al-draw d3" d="M140 104 H250" stroke="#d8d4cb" stroke-width="6" stroke-linecap="round"/>
      <path class="al-draw d4" d="M150 150 C 165 128, 175 168, 190 145 S 215 140, 230 150" stroke="#1d4e74" stroke-width="2.4" fill="none"/>
      <g class="al-pop p6"><circle cx="280" cy="148" r="22" fill="none" stroke="#b7791f" stroke-width="2"/>
      <path d="M270 148 l7 7 l13 -14" stroke="#b7791f" stroke-width="2.6" fill="none" stroke-linecap="round"/></g></svg>""",
}

TOUR = [
    ("welcome", "Bienvenue dans Aléa",
     "En zone CIMA, l'assurance-vie est tarifée sur des tables issues de la population française des années 1960. "
     "Aléa aide l'actuaire à construire une table locale à partir des données des assureurs.",
     "prépare, calcule, explique", "choisissez, validez, signez"),
    ("columns", "Les données, telles qu'elles arrivent",
     "Chaque assureur exporte ses fichiers à sa façon : noms de colonnes, formats de date, codes. "
     "Aléa reconnaît chaque colonne et indique sa confiance.",
     "reconnaît les colonnes (embeddings multilingues)", "confirmez les correspondances incertaines"),
    ("quality", "Le contrôle qualité",
     "Doublons, âges impossibles, dates incohérentes, capitaux mal saisis : chaque anomalie arrive avec une action proposée. "
     "Rien n'est corrigé sans vous.",
     "détecte (règles + Isolation Forest)", "acceptez ou rejetez chaque action"),
    ("pool", "Mutualiser sans exposer",
     "Chaque assureur ne partage que des comptages agrégés par âge et sexe. Les petites cellules et celles d'un seul "
     "contributeur sont retirées : aucune donnée personnelle ne circule.",
     "construit la table de marché", "choisissez le modèle de crédibilité"),
    ("price", "De la table au prix",
     "La crédibilité combine votre expérience et celle du marché, avec un intervalle de confiance. "
     "Vous voyez aussitôt l'effet sur la prime d'un contrat type.",
     "combine et chiffre l'incertitude", "fixez les hypothèses tarifaires"),
    ("sign", "La note, puis la signature",
     "La note technique est construite à partir des seuls résultats calculés ; un garde-fou bloque tout nombre non tracé. "
     "Vous signez, et tout est archivé avec sa traçabilité.",
     "rédige et vérifie chaque nombre", "relisez et signez"),
]


def _tour_nav(delta: int) -> None:
    st.session_state.tour_i = max(0, min(len(TOUR) - 1, st.session_state.get("tour_i", 0) + delta))


@st.dialog("Visite guidée", width="large")
def tour() -> None:
    i = st.session_state.get("tour_i", 0)
    key, title, text, ia, you = TOUR[i]
    st.markdown(f'<div class="al-tour-art" key="{key}-{i}">{ART[key]}</div>', unsafe_allow_html=True)
    dots = "".join(f'<i class="{"on" if j == i else ""}"></i>' for j in range(len(TOUR)))
    st.markdown(f'<div class="al-dots">{dots}</div>', unsafe_allow_html=True)
    st.markdown(f"### {title}")
    st.write(text)
    st.markdown(f'<div class="al-roles"><div class="al-role ia"><b>L\'IA</b>{ia}</div>'
                f'<div class="al-role you"><b>Vous</b>{you}</div></div>', unsafe_allow_html=True)
    st.write("")
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.button("Précédent", on_click=_tour_nav, args=(-1,), disabled=i == 0, use_container_width=True, key="tour_prev")
    if i < len(TOUR) - 1:
        c3.button("Suivant", on_click=_tour_nav, args=(1,), type="primary", use_container_width=True, key="tour_next")
    elif c3.button("Commencer", type="primary", use_container_width=True, key="tour_end"):
        st.session_state.tour_i = 0
        st.rerun()


INTRO_ART = """<svg viewBox="0 0 440 220" role="img" aria-label="Table locale construite à partir des données">
  <g stroke="rgba(255,255,255,.12)"><line x1="30" y1="190" x2="420" y2="190"/><line x1="30" y1="140" x2="420" y2="140"/>
  <line x1="30" y1="90" x2="420" y2="90"/><line x1="30" y1="40" x2="420" y2="40"/></g>
  <path class="al-draw" d="M30 180 C 130 178, 210 168, 270 138 S 370 60, 420 34" stroke="#e8c48a" stroke-width="2" stroke-dasharray="6 6" fill="none"/>
  <path class="al-draw d2" d="M30 186 C 140 184, 220 176, 280 152 S 375 88, 420 64" stroke="#ffffff" stroke-width="3.5" fill="none" stroke-linecap="round"/>
  <g fill="#ffffff"><circle class="al-pop p2" cx="110" cy="183" r="3.5"/><circle class="al-pop p3" cx="190" cy="178" r="3.5"/>
  <circle class="al-pop p4" cx="260" cy="160" r="3.5"/><circle class="al-pop p5" cx="330" cy="120" r="3.5"/><circle class="al-pop p6" cx="390" cy="82" r="3.5"/></g>
  <g font-family="IBM Plex Mono" font-size="11"><text x="34" y="26" fill="#e8c48a">— table de référence (population)</text>
  <text x="34" y="44" fill="#ffffff">— table locale (Aléa)</text></g></svg>"""


def intro_banner() -> None:
    st.markdown(
        f"""<section class="al-intro"><div><div class="al-kicker"><i></i>ACTUARIAT AUGMENTÉ</div>
        <h2>Des tables de mortalité locales, construites avec l'actuaire</h2>
        <p>En zone CIMA, l'assurance-vie est encore tarifée sur des tables issues de la population française des
        années 1960. Aléa prépare les données, mutualise le marché sans exposer personne, et laisse chaque décision
        à l'actuaire.</p>
        <div class="al-proof"><div><b class="count" style="--to:8"></b><small>champs sur 8 reconnus automatiquement</small></div>
        <div><b class="count" style="--to:100"></b><small>% de précision sur les erreurs injectées</small></div>
        <div><b>0</b><small>donnée personnelle partagée</small></div></div></div>
        <div class="al-art">{INTRO_ART}</div></section>""", unsafe_allow_html=True)


def welcome_card() -> None:
    st.markdown(
        f"""<section class="al-welcome"><div><h3>Une table de mortalité locale, en sept étapes</h3>
        <p>Chargez un portefeuille fictif, laissez l'IA préparer le travail, puis décidez à chaque étape.</p>
        <ol><li>Données et colonnes</li><li>Qualité</li><li>Expérience et mutualisation</li>
        <li>Tarification</li><li>Note signée</li></ol></div>
        <div class="al-tour-art" style="margin:0">{ART['welcome']}</div></section>""",
        unsafe_allow_html=True)


# ------------------------------------------------------------------ aide contextuelle
HELP = {
    0: "Choisissez un assureur fictif (Gamma est le plus petit : c'est là que la mutualisation compte le plus) ou "
       "importez un CSV. Le fichier est lu tel quel : séparateur et encodage sont détectés. Son empreinte SHA-256 est "
       "conservée pour la traçabilité.",
    1: "Chaque ligne associe un champ standard à une colonne du fichier. La confiance combine le sens de l'en-tête "
       "(modèle d'embeddings) et le profil des valeurs (dates, montants, codes). Sous 0,55, la ligne est marquée « à "
       "confirmer » : changez la colonne source dans la liste si besoin. Une même colonne ne peut servir deux fois.",
    2: "Le tableau du haut résume les anomalies par type ; celui du bas les détaille ligne par ligne. Décochez "
       "« accepter » pour refuser une action. Attention : exclure les décès sans date sous-estimerait la mortalité ; "
       "Aléa propose donc d'imputer la date. Les profils atypiques sont signalés mais conservés.",
    3: "Les points gris sont les taux bruts par âge, la courbe bleue le modèle (GLM de Poisson) avec son intervalle "
       "à 95 %, la courbe orange la table OMS du Bénin. L'échelle est logarithmique : un écart vertical constant est "
       "un écart en pourcentage constant.",
    4: "Le tableau du haut montre ce que chaque assureur partage et ce qui est supprimé avant partage. Choisissez le "
       "modèle : par bandes d'âge (recommandé à partir de 5 assureurs), global, ou « marché sans soi » pour contrôler "
       "un assureur dominant. Le bootstrap ajoute l'incertitude sur la table de marché et sur K.",
    5: "Réglez le contrat type. Le taux technique doit respecter le maximum autorisé par le code CIMA. L'écart est "
       "calculé par rapport à la table OMS de population ; ajoutez data/reference/cima.csv pour comparer à la table "
       "réglementaire.",
    6: "Le rédacteur n'utilise que les faits du tableau dépliable. Si vous modifiez le texte, le garde-fou revérifie "
       "chaque nombre. La signature exige votre nom et votre validation explicite ; la note est alors archivée avec "
       "son manifeste de traçabilité.",
}


def help_box(i: int) -> None:
    with st.expander("Comment lire cet écran"):
        st.write(HELP[i])


# ------------------------------------------------------------------ guide utilisateur
GUIDE_STEPS = [
    ("Données", "Charger un portefeuille",
     "Un portefeuille est l'export brut d'un assureur : une ligne par contrat, avec naissance, sexe, dates d'effet et "
     "de sortie, motif de sortie, capital. Les quatre portefeuilles fournis sont fictifs.",
     "Commencez par Gamma (petit assureur) pour voir l'apport de la mutualisation."),
    ("Colonnes", "Valider la correspondance",
     "Aléa propose une colonne source pour chaque champ standard, avec un score de confiance.",
     "Vérifiez toujours les lignes « à confirmer », puis cliquez sur « Valider la correspondance »."),
    ("Qualité", "Décider des corrections",
     "Chaque anomalie arrive avec une action : exclure, imputer, diviser par 1 000, traiter comme en cours, conserver.",
     "Décochez ce que vous refusez, puis « Appliquer les décisions ». Rien n'est corrigé sans vous."),
    ("Expérience", "Lire la mortalité observée",
     "Expositions, décès et rapport observés sur attendus par rapport à la table OMS, avec un modèle lissé et son "
     "intervalle de confiance.",
     "Basculez entre hommes et femmes ; activez « Afficher la vérité » pour juger l'estimation (données fictives)."),
    ("Mutualisation", "Combiner avec le marché",
     "Les assureurs partagent des agrégats ; Aléa estime l'hétérogénéité entre eux et pondère votre expérience "
     "selon son volume (crédibilité).",
     "Comparez les modèles ; lancez le bootstrap pour un intervalle de bout en bout."),
    ("Tarification", "Mesurer l'effet sur la prime",
     "Prime annuelle pure d'un temporaire décès selon chaque table.",
     "Alignez le taux technique sur le maximum CIMA ; chargez la table CIMA pour la comparaison réglementaire."),
    ("Note technique", "Rédiger, vérifier, signer",
     "La note est construite à partir des faits calculés ; le garde-fou bloque tout nombre non tracé.",
     "Relisez, saisissez votre nom, validez : la note et son manifeste sont archivés et téléchargeables."),
]

GLOSSARY = [
    ("Exposition", "Temps passé sous risque, en années-personnes : la base de tout taux de mortalité."),
    ("Observés / attendus (A/E)", "Décès observés divisés par les décès qu'aurait prédits une table de référence. "
                                  "80 % signifie une mortalité inférieure de 20 % à la référence."),
    ("GLM de Poisson", "Modèle statistique qui lisse les taux bruts par âge et sexe et fournit un intervalle de confiance."),
    ("Crédibilité (Z)", "Poids donné à votre propre expérience face au marché. Plus vous avez de décès attendus, plus Z est élevé."),
    ("K, τ²", "Mesures de l'hétérogénéité réelle entre assureurs, estimées sur les données mutualisées (Bühlmann-Straub)."),
    ("Bandes d'âge", "Crédibilité appliquée séparément aux 20-34, 35-49, 50-64 et 65-80 ans, avec repli sur le niveau "
                     "global quand une bande a trop peu de décès attendus."),
    ("Marché sans soi", "Table de marché recalculée sans l'assureur évalué, pour éviter qu'un assureur dominant se "
                        "crédibilise lui-même."),
    ("Bootstrap", "Rééchantillonnages répétés qui donnent un intervalle à 95 % incluant l'incertitude sur le marché et sur K."),
    ("Contributeur unique", "Cellule (âge, sexe) alimentée par un seul assureur : son « total de marché » serait sa donnée "
                            "individuelle. Elle est retirée avant mutualisation."),
    ("Garde-fou", "Contrôle qui extrait chaque nombre de la note et vérifie qu'il provient d'un calcul tracé."),
]


def guide_page() -> None:
    st.markdown("""<header class="al-hero"><div class="al-kicker"><i></i>GUIDE UTILISATEUR</div>
        <h1>Prendre Aléa en main</h1><p class="lead">Aléa prépare le travail actuariel ; vous gardez chaque décision.
        Le parcours suit sept étapes, dans l'ordre de la barre latérale. Comptez une dizaine de minutes pour un
        premier passage.</p></header>""", unsafe_allow_html=True)
    if st.button("Lancer la visite guidée animée", type="primary", key="guide_tour"):
        st.session_state.tour_i = 0
        tour()
    st.markdown("#### Le parcours, étape par étape")
    html = "".join(f'<div class="al-guide-step"><div class="n">{i + 1:02d}</div><div><h4>{t} — {h}</h4>'
                   f'<p>{d}</p><p><b>À faire :</b> {a}</p></div></div>'
                   for i, (t, h, d, a) in enumerate(GUIDE_STEPS))
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("#### Glossaire")
    st.markdown("".join(f'<div class="al-term"><b>{k}</b> — {v}</div>' for k, v in GLOSSARY), unsafe_allow_html=True)
    st.markdown("#### Bon à savoir")
    st.markdown(
        "- **Données fictives.** Les portefeuilles sont simulés à partir de la table OMS du Bénin ; leur vraie "
        "mortalité est connue, d'où l'option « Afficher la vérité ».\n"
        "- **Aucune donnée personnelle ne circule** dans la mutualisation : seulement des comptages agrégés.\n"
        "- **Limite connue.** Quand la forme de mortalité d'un assureur diffère fortement de celle du marché, la table "
        "de marché est biaisée ; Aléa le rend visible (A/E par bande, marché sans soi).\n"
        "- **Tables CIMA.** Aucune valeur n'est inventée : déposez `data/reference/cima.csv` pour les comparer.\n"
        "- **Traçabilité.** Chaque note signée est archivée dans `runs/` avec l'empreinte du fichier, vos décisions "
        "et les paramètres.")
