"""Purple/white visual-first styling layered over the existing Streamlit theme."""
from __future__ import annotations

import streamlit as st
from src.ui.theme import apply_theme, brand

CSS_V2 = """
<style>
:root {--d-purple:#6941C6;--d-deep:#291748;--d-bg:#F8F7FC;--d-ink:#211A35;--d-muted:#776E88;--d-line:#E8E3F1;}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--d-bg)!important;}
[data-testid="stMainBlockContainer"],.main .block-container{max-width:1410px!important;padding-top:1.5rem!important;padding-bottom:3rem!important;}
[data-testid="stSidebar"]{background:linear-gradient(160deg,#29194B,#1E153A 65%,#1A1433)!important;}
[data-testid="stPlotlyChart"]{background:#fff!important;border:0!important;padding:0!important;border-radius:12px!important;}
[data-testid="stMetric"]{background:white!important;border:1px solid var(--d-line)!important;border-radius:14px!important;}
.stButton button,.stLinkButton a{border-radius:10px!important;}
.stLinkButton a{border:1px solid #DDCFF5!important;background:#F4EEFF!important;color:#543099!important;font-weight:650!important;font-size:.83rem!important;}
.stLinkButton a:hover{background:#EBE1FF!important;}
[data-testid="stTabs"] button{font-size:.86rem!important;}
.d-hero{padding:25px 28px;border-radius:18px;margin:2px 0 18px;background:radial-gradient(circle at 85% 0%,rgba(176,134,250,.35),transparent 32%),linear-gradient(110deg,#241642 0%,#482784 58%,#7042C0 100%);display:flex;align-items:center;justify-content:space-between;gap:20px;}
.d-hero h1{font-size:2.0rem!important;font-weight:800!important;color:#fff!important;letter-spacing:-.04em!important;margin:8px 0!important;line-height:1.12;}
.d-hero p{font-size:.89rem!important;color:#DFD7EE!important;max-width:680px;line-height:1.55;margin:0;}
.d-eyebrow{font-size:.66rem;letter-spacing:.15em;font-weight:800;color:#DCCFFF;}
.d-mark{background:rgba(255,255,255,.08);color:#FFF;border:1px solid rgba(255,255,255,.18);border-radius:17px;padding:24px;font-size:1.45rem;font-weight:900;min-width:115px;text-align:center;}
.d-heading{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;margin:2px 0 20px;}
.d-heading h1{margin:0!important;font-size:1.65rem!important;letter-spacing:-.035em;}
.d-heading p{font-size:.83rem;color:#81788F;margin:5px 0 0;max-width:680px;line-height:1.5;}
.d-overline{font-size:.65rem;font-weight:850;letter-spacing:.16em;color:#7044B9;margin-bottom:6px;}
.d-status{font-size:.7rem;border-radius:50px;padding:7px 11px;font-weight:750;background:#FFF0D9;color:#946719;white-space:nowrap;}
.d-status.ok{background:#E5F6EC;color:#177C5E;}
.d-section{font-size:1.04rem;font-weight:800;color:var(--d-ink);margin:26px 0 5px;}
.d-sub{font-size:.77rem;color:#878092;margin-bottom:12px;line-height:1.5;}
.d-kpi{background:#fff;border:1px solid var(--d-line);border-radius:14px;padding:16px 16px 14px;min-height:123px;box-shadow:0 2px 13px rgba(43,30,73,.024);}
.d-kpi-label{font-size:.75rem;color:#777085;font-weight:650;display:flex;align-items:center;justify-content:space-between;gap:4px;}
.d-kpi-icon{color:#7243CC;background:#F0E9FF;border-radius:8px;width:26px;height:26px;display:grid;place-items:center;font-weight:800;}
.d-kpi-value{font-size:1.82rem;color:#28203B;line-height:1.13;letter-spacing:-.035em;font-weight:850;margin:9px 0 7px;overflow-wrap:anywhere;}
.d-kpi-note{font-size:.69rem;line-height:1.4;color:#958EA3;}
.d-chart-title{font-size:.93rem;font-weight:760;color:#2A233B;margin:6px 2px 0;}
.d-chart-sub{font-size:.71rem;color:#878092;margin:1px 2px 6px;line-height:1.4;}
.d-finding{background:#fff;border:1px solid var(--d-line);border-left:3px solid #8A61D9;border-radius:12px;margin:10px 0 5px;padding:14px 16px;display:flex;gap:13px;align-items:flex-start;}
.d-finding-index{width:32px;min-width:32px;height:32px;border-radius:9px;background:#F0E9FF;color:#643AB9;display:grid;place-items:center;font-size:.8rem;font-weight:850;}
.d-finding-body{min-width:0;overflow-wrap:anywhere;}
.d-finding-scope{color:#93889F;font-size:.74rem;}
.d-finding-title{font-size:.93rem;font-weight:780;color:#322846;margin:3px 0 5px;}
.d-finding-fact{font-size:.8rem;color:#655C75;margin-bottom:5px;}
.d-finding-next{font-size:.79rem;color:#4A3D5E;}
.d-repo-header{background:#fff;border:1px solid var(--d-line);border-radius:14px;padding:18px 20px;margin:6px 0 12px;}
.d-repo-header strong{color:#2B223E;font-size:1.08rem;display:block;overflow-wrap:anywhere;}
.d-repo-header small{font-size:.75rem;color:#897F96;}
@media(max-width:900px){.d-mark{display:none;}.d-hero h1{font-size:1.7rem!important;}}
@media(max-width:700px){
[data-testid="stMainBlockContainer"],.main .block-container{padding:1rem .75rem 4rem!important;}
.d-hero{padding:21px 18px;border-radius:14px;margin:0 0 14px;}
.d-hero h1{font-size:1.48rem!important;}.d-hero p{font-size:.79rem!important;}
.d-heading h1{font-size:1.34rem!important;}.d-kpi{padding:12px;min-height:105px;}
.d-kpi-value{font-size:1.45rem;}.d-kpi-label{font-size:.68rem;}.d-section{margin-top:19px;}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}
</style>
"""

def apply_theme_v2():
    apply_theme()
    st.markdown(CSS_V2, unsafe_allow_html=True)
