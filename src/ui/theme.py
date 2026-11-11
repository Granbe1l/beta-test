"""A restrained purple / white operational UI, rendered with native Streamlit widgets.

This is not an Accenture asset or an affiliation claim.  All dynamic text is
HTML-escaped and all buttons/links are native Streamlit controls.
"""
from __future__ import annotations

import html
import streamlit as st

INK = "#211E32"
PURPLE = "#6F3FDF"
PURPLE_DARK = "#44218F"
LAVENDER = "#EDE6FF"
MUTED = "#777487"
SURFACE = "#FFFFFF"

CSS = """
<style>
:root { --purple:#6f3fdf; --deep:#211339; --violet:#4f269f;
  --ink:#211e32; --muted:#777487; --line:#e9e6f1; --bg:#f7f6fb; }
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"] {
  background:#f7f6fb!important;color:var(--ink)!important;
}
[data-testid="stHeader"]{background:rgba(247,246,251,.93)!important;}
[data-testid="stSidebar"]{background:linear-gradient(170deg,#24143f 0%,#1a1133 100%)!important;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.55rem;}
[data-testid="stSidebar"] .stMarkdown p,[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] label,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {color:#f0ecfa!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  padding:9px 10px!important;border-radius:9px!important;
  transition:none!important;border:1px solid transparent;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background:#50328a!important;border:1px solid #7355ad!important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label p{font-size:.88rem!important;font-weight:550!important;}
[data-testid="stSidebar"] button{background:rgba(255,255,255,.07)!important;color:#f5f0ff!important;border-color:rgba(255,255,255,.2)!important;}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] *{color:#eeeaf5;}
[data-testid="stSidebar"] .stDivider{border-color:#594378;}
[data-testid="stMainBlockContainer"],.main .block-container {
  max-width:1320px!important;padding-top:1.45rem!important;padding-bottom:3rem!important;
}
h1,h2,h3{color:var(--ink)!important;letter-spacing:-.025em;}
h1{font-size:1.8rem!important;font-weight:760!important;}
h2{font-size:1.20rem!important;font-weight:730!important;}
h3{font-size:1.04rem!important;font-weight:700!important;}
.stMarkdown p{line-height:1.55;}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:11px;padding:15px;min-height:96px;}
[data-testid="stMetricValue"]{font-size:1.5rem!important;}
[data-testid="stMetricLabel"]{font-size:.8rem!important;}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:11px;overflow:hidden;}
[data-testid="stTabs"] button{font-weight:650;}
[data-testid="stTabs"] [aria-selected="true"]{color:var(--violet)!important;}
[data-testid="stExpander"]{border:1px solid var(--line)!important;border-radius:11px!important;background:white;}
.stButton button,.stLinkButton a,[data-testid="stFormSubmitButton"] button{
  border-radius:9px!important;font-weight:600;transition:none!important;
}
.stButton button[kind="primary"]{background:var(--purple)!important;border-color:var(--purple)!important;}
[data-baseweb="select"]>div,[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input{border-radius:9px!important;}
[data-testid="stPlotlyChart"]{background:#fff;border:1px solid var(--line);border-radius:12px;padding:5px;}
/* HTML cards contain no inputs or scripts: Streamlit owns all interactions. */
.brand{display:flex;align-items:center;gap:10px;margin:8px 0 17px;}
.brand-mark{width:37px;height:37px;display:grid;place-items:center;color:#e8ddff;
  background:#50328a;border:1px solid #7654b9;border-radius:10px;font-weight:900;font-size:1.25rem;}
.brand-name{font-size:.78rem;font-weight:850;letter-spacing:.08em;color:#fff;line-height:1.24;}
.brand-note{font-size:.68rem;color:#bba9dc;margin-top:3px;letter-spacing:.015em;}
.side-footer{font-size:.76rem;color:#c8bbdc;line-height:1.7;padding:5px 0;}
.breadcrumb{font-size:.73rem;font-weight:600;color:#888395;margin-bottom:7px;letter-spacing:.01em;}
.breadcrumb strong{color:#6030c4;font-weight:750;}
.page-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;
  margin-bottom:12px;flex-wrap:wrap;}
.page-title{margin:0;font-weight:790;font-size:1.72rem;letter-spacing:-.04em;line-height:1.25;color:#221e34;}
.page-caption{font-size:.85rem;color:#777487;line-height:1.5;margin-top:5px;max-width:710px;}
.status-chip{display:inline-flex;align-items:center;gap:7px;padding:6px 10px;
  font-size:.69rem;font-weight:760;letter-spacing:.02em;border-radius:8px;
  border:1px solid #e4d7ff;background:#f2eaff;color:#5b32b3;white-space:nowrap;}
.status-chip.good{background:#e9f8f0;color:#19764d;border-color:#c8ebda;}
.status-chip.warn{background:#fff3e1;color:#99611c;border-color:#f3dfbb;}
.section-heading{font-size:1rem;font-weight:760;letter-spacing:-.02em;color:var(--ink);margin:15px 0 10px;}
.section-note{font-size:.78rem;color:#848092;margin:-4px 0 11px;}
.stat-card{border:1px solid var(--line);background:white;border-radius:12px;
  padding:17px 16px 15px;min-height:115px;position:relative;}
.stat-card .stat-icon{position:absolute;top:14px;right:14px;width:28px;height:28px;
  display:grid;place-items:center;background:#f0eafe;border-radius:8px;color:#6a3dcb;
  font-weight:800;font-size:.96rem;}
.stat-card .stat-value{font-size:1.78rem;line-height:1.15;font-weight:800;letter-spacing:-.035em;
  color:var(--ink);padding-top:11px;overflow-wrap:anywhere;}
.stat-card .stat-label{font-size:.77rem;font-weight:590;color:#747081;margin-top:9px;}
.stat-card .stat-note{font-size:.69rem;color:#a09aaf;margin-top:4px;}
.surface{border:1px solid var(--line);background:#fff;border-radius:12px;padding:18px 20px;}
.surface-title{font-size:.94rem;font-weight:770;color:var(--ink);margin-bottom:5px;}
.surface-sub{font-size:.77rem;color:var(--muted);line-height:1.5;}
.repo-main{font-size:1.14rem;font-weight:770;color:var(--ink);}
.repo-meta{font-size:.77rem;color:#767184;line-height:1.7;}
.finding-card{background:#fff;border:1px solid var(--line);border-left:3px solid #8859ec;
  border-radius:10px;padding:15px 17px;margin-bottom:10px;}
.finding-tag{font-size:.63rem;color:#6c45c2;font-weight:850;letter-spacing:.085em;margin-bottom:5px;}
.finding-head{color:#2b2242;font-weight:750;font-size:.91rem;line-height:1.4;margin-bottom:8px;}
.finding-detail{font-size:.78rem;color:#706a80;line-height:1.6;margin:4px 0;}
.finding-detail strong{color:#42345c;}
.empty-card{background:#fff;border:1px dashed #d1c5ed;border-radius:12px;
  padding:22px 22px;color:#665b79;margin:11px 0;}
.empty-card .empty-head{font-size:.93rem;font-weight:800;color:#51406c;margin-bottom:5px;}
.empty-card p{font-size:.8rem;margin:0;max-width:720px;}
.footnote{font-size:.75rem;color:#878294;line-height:1.6;margin-top:10px;}
@media(max-width:700px){
 [data-testid="stMainBlockContainer"],.main .block-container{padding:1rem .75rem 5rem!important;}
 .brand{margin-bottom:8px;}
 .page-title{font-size:1.35rem;}
 .page-heading{gap:7px;}
 .page-caption{font-size:.79rem;}
 .stat-card{padding:13px;min-height:91px;}
 .stat-card .stat-value{font-size:1.42rem;padding-top:12px;}
 .stat-card .stat-label{font-size:.71rem;}
 .stat-card .stat-icon{top:10px;right:10px;width:23px;height:23px;}
 .surface{padding:14px;}
 .finding-card{padding:13px;}
 [data-testid="stHorizontalBlock"]{gap:.5rem!important;}
 [data-testid="stDataFrame"]{max-width:100%;}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;scroll-behavior:auto!important}}
</style>
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def brand() -> None:
    st.markdown('''<div class="brand"><div class="brand-mark">D</div>
    <div><div class="brand-name">DELIVERY<br>MONITOR</div>
    <div class="brand-note">OPEN-SOURCE ANALYTICS</div></div></div>''', unsafe_allow_html=True)


def page_header(title: str, description: str, status: str = "unavailable") -> None:
    level = "good" if status == "complete" else "warn" if status in ("partial", "stale", "failed") else ""
    labels = {"complete": "Verified coverage", "partial": "Partial coverage",
              "stale": "Data may be stale", "failed": "Sync failed", "unavailable": "Not connected"}
    st.markdown(f'''<div class="breadcrumb">Workspace&nbsp; › &nbsp;<strong>Project Delivery Monitor</strong></div>
    <div class="page-heading"><div><div class="page-title">{esc(title)}</div>
    <div class="page-caption">{esc(description)}</div></div>
    <div class="status-chip {level}"><span>●</span>{esc(labels.get(status, status.title()))}</div></div>''', unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    st.markdown(f'<div class="section-heading">{esc(title)}</div>' +
                (f'<div class="section-note">{esc(note)}</div>' if note else ""), unsafe_allow_html=True)


def stat(label: str, value: object, note: str = "", icon: str = "◈") -> None:
    st.markdown(f'''<div class="stat-card"><span class="stat-icon">{esc(icon)}</span>
    <div class="stat-value">{esc(value)}</div><div class="stat-label">{esc(label)}</div>
    {f'<div class="stat-note">{esc(note)}</div>' if note else ''}</div>''', unsafe_allow_html=True)


def surface(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="surface"><div class="surface-title">{esc(title)}</div>' +
                (f'<div class="surface-sub">{esc(subtitle)}</div>' if subtitle else '') + '</div>', unsafe_allow_html=True)


def finding(item: dict, tag: str = "REVIEW") -> None:
    st.markdown(f'''<div class="finding-card"><div class="finding-tag">{esc(tag)} · {esc(item['scope'])}</div>
    <div class="finding-head">{esc(item['headline'])}</div>
    <div class="finding-detail"><strong>Evidence:</strong> {esc(item['evidence'])}</div>
    <div class="finding-detail"><strong>Meaning:</strong> {esc(item['interpretation'])}</div>
    <div class="finding-detail"><strong>Next review:</strong> {esc(item['review'])}</div></div>''', unsafe_allow_html=True)
    # Native control preserves keyboard and assistive-technology access.
    st.link_button("↗  View GitHub evidence", item["url"], use_container_width=False)


def empty_state(message: str = "No verified data available yet", detail: str = "") -> None:
    detail = detail or "Connect a database and run an initial GitHub synchronization to see actual metrics. No example numbers are presented as production data."
    st.markdown(f'''<div class="empty-card"><div class="empty-head">{esc(message)}</div>
    <p>{esc(detail)}</p></div>''', unsafe_allow_html=True)
