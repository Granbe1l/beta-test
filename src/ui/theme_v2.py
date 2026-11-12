"""Delivery Monitor V3 presentation: compact dark navigation and readable charts."""
from __future__ import annotations

import streamlit as st
from src.ui.theme import apply_theme, brand

CSS_V2 = """
<style>
:root{--ui-ink:#29233D;--ui-muted:#706A7E;--ui-line:#E7E3EF;--ui-purple:#7046C4;--ui-bg:#F7F7FB;}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--ui-bg)!important;}
[data-testid="stMainBlockContainer"],.main .block-container{max-width:1370px!important;padding:1.25rem 2.1rem 3rem!important;}
[data-testid="stHeader"]{background:rgba(247,247,251,.93)!important;}
[data-testid="stSidebar"]{background:#241936!important;border-right:1px solid #45345F!important;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.22rem!important;}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding:21px 17px 18px!important;}
[data-testid="stSidebar"] .brand{padding:1px 0 12px!important;margin:0 0 7px!important;border-bottom:1px solid rgba(255,255,255,.12);}
[data-testid="stSidebar"] .brand-mark{border-radius:9px;width:34px;height:34px;font-size:1.03rem;background:#554080;}
[data-testid="stSidebar"] .brand-name{font-size:.76rem;line-height:1.23;letter-spacing:.055em;}
[data-testid="stSidebar"] .brand-note{font-size:.61rem;opacity:.84;}
.sidebar-label{font-size:.65rem;font-weight:750;letter-spacing:.14em;color:#AFA1C5;margin:10px 0 6px!important;}
[data-testid="stSidebar"] .stButton button,
[data-testid="stSidebar"] [data-testid="stButton"] button{
  display:flex!important;justify-content:flex-start!important;align-items:center!important;
  text-align:left!important;min-height:38px!important;width:100%!important;
  border-radius:8px!important;padding:8px 12px!important;margin:0!important;
  letter-spacing:0!important;font-size:.83rem!important;font-weight:590!important;
  box-shadow:none!important;transition:background-color .1s ease!important;
}
[data-testid="stSidebar"] .stButton button[kind="secondary"],
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"]{
  background:transparent!important;border:1px solid transparent!important;color:#D9D1E7!important;
}
[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover{
  color:#fff!important;background:#352749!important;
}
[data-testid="stSidebar"] .stButton button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]{
  background:#584089!important;border:1px solid #6A50A0!important;
  color:white!important;font-weight:730!important;box-shadow:inset 3px 0 0 #C2A8FA!important;
}
[data-testid="stSidebar"] .stButton button [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] .stButton button [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stButton"] button [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stButton"] button [data-testid="stMarkdownContainer"] p{
  text-align:left!important;justify-content:flex-start!important;margin:0!important;
  flex:1!important;width:100%!important;
}
[data-testid="stSidebar"] .stButton button:focus-visible{outline:2px solid #C2A8FA!important;outline-offset:2px!important;}
.side-health-card{background:#302441;border:1px solid #493958;border-radius:10px;padding:12px 13px;margin-top:5px;}
.side-health-head{font-size:.66rem;letter-spacing:.09em;font-weight:740;color:#BCAACF;margin:0 0 5px;}
.side-health-status{font-size:.82rem;font-weight:720;color:#F3EBFF;line-height:1.5;}
.side-health-small{font-size:.70rem;color:#C8B9D8;line-height:1.58;margin-top:4px;}
.side-health-note{font-size:.68rem;color:#BCACCF;line-height:1.5;}
[data-testid="stSidebar"] [data-testid="stDivider"]{border-color:#453458!important;margin:12px 0!important;}
[data-testid="stSidebar"] .side-footer{color:#AFA0C2;font-size:.68rem;line-height:1.55;margin:7px 0;}
[data-testid="stSidebar"] .stButton:last-of-type button[kind="secondary"]{border-color:rgba(255,255,255,.10)!important;}
.d-hero{background:linear-gradient(112deg,#281C43,#54308E 75%,#6A43B3);border-radius:13px;padding:19px 23px;margin:0 0 13px;display:flex;align-items:center;justify-content:space-between;gap:15px;}
.d-hero h1{color:white!important;font-size:1.52rem!important;line-height:1.17!important;letter-spacing:-.035em!important;margin:7px 0!important;font-weight:800!important;}
.d-hero p{font-size:.79rem!important;max-width:670px;line-height:1.46;color:#E2D8F2!important;margin:0;}
.d-eyebrow{color:#D4C3EE;font-size:.59rem;font-weight:790;letter-spacing:.14em;}
.d-mark{color:#EDE0FF;background:#ffffff14;border:1px solid #ffffff31;font-size:1.14rem;font-weight:820;padding:16px 18px;border-radius:10px;min-width:75px;text-align:center;}
.d-heading{display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;gap:8px;margin:1px 0 16px;}
.d-heading h1{font-size:1.51rem!important;letter-spacing:-.025em!important;margin:0!important;color:var(--ui-ink);}
.d-heading p{font-size:.79rem;color:var(--ui-muted);line-height:1.48;max-width:620px;margin:4px 0 0;}
.d-overline{color:#6F48B8;font-size:.63rem;letter-spacing:.13em;font-weight:800;margin-bottom:5px;}
.d-status{display:inline-flex;align-items:center;align-self:flex-start;font-size:.67rem;font-weight:700;color:#855D28;background:#FFF2DF;border-radius:8px;padding:6px 9px;line-height:1.2;}
.d-status.ok{background:#E7F5EE;color:#14764E;}
.d-section{font-size:1.02rem;font-weight:800;letter-spacing:-.019em;color:var(--ui-ink);margin:19px 0 3px;}
.d-sub{font-size:.75rem;line-height:1.45;color:var(--ui-muted);margin-bottom:10px;}
.d-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:8px 0 13px;}
.d-kpi{min-width:0;background:#fff;border:1px solid var(--ui-line);border-radius:12px;min-height:111px;padding:14px 15px;}
.d-kpi-label{display:flex;justify-content:space-between;align-items:center;gap:6px;color:#756D85;font-weight:640;font-size:.72rem;line-height:1.25;}
.d-kpi-icon{display:grid;place-items:center;min-width:23px;width:23px;height:23px;border-radius:6px;background:#EFEAFF;color:#6A45C4;font-weight:750;}
.d-kpi-value{font-size:1.65rem;font-weight:850;letter-spacing:-.04em;line-height:1.08;color:var(--ui-ink);margin:9px 0 5px;}
.d-kpi-note{font-size:.69rem;color:#8C8499;line-height:1.4;}
.d-chart-title{font-weight:760;font-size:.91rem;color:var(--ui-ink);margin:2px 2px 2px;}
.d-chart-sub{font-size:.72rem;color:#827B90;line-height:1.4;margin:0 2px 6px;}
.d-coverage,.d-context{font-size:.74rem;line-height:1.6;padding:9px 12px;margin:7px 0;border-radius:9px;}
.d-coverage{background:#fff;border:1px solid var(--ui-line);color:#5D536A;}
.d-coverage strong{color:#433456;}
.d-coverage em{color:#74688D;font-style:normal;}
.d-context{background:#F0EBF9;border-left:3px solid #9573CF;color:#534469;}
.d-repo-header{background:#fff;border:1px solid var(--ui-line);padding:15px 17px;border-radius:12px;margin:5px 0 10px;}
.d-repo-header strong{display:block;font-size:1.03rem;overflow-wrap:anywhere;color:var(--ui-ink);}
.d-repo-header small{font-size:.74rem;color:var(--ui-muted);}
[data-testid="stPlotlyChart"]{background:transparent!important;border:0!important;padding:0!important;border-radius:10px!important;}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:12px!important;}
[data-testid="stTabs"] button{font-size:.82rem!important;}
.stLinkButton a{border-radius:8px!important;border:1px solid #DDD2EE!important;background:#F4F0FA!important;color:#563590!important;font-size:.80rem!important;font-weight:650!important;}
.stButton button,.stLinkButton a{border-radius:9px!important;}
@media(max-width:1024px){.d-kpis{grid-template-columns:repeat(2,minmax(0,1fr));}.d-mark{display:none;}}
@media(max-width:700px){
  [data-testid="stMainBlockContainer"],.main .block-container{padding:1.05rem .72rem 3rem!important;}
  .d-hero{padding:14px 15px;margin:0 0 9px;}
  .d-hero h1{font-size:1.26rem!important;line-height:1.19!important;}
  .d-hero p{font-size:.72rem!important;}
  .d-eyebrow{font-size:.55rem;}
  .d-kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:8px 0;}
  .d-kpi{padding:12px 10px;min-height:94px;}
  .d-kpi-value{font-size:1.37rem;}
  .d-kpi-label{font-size:.66rem;}
  .d-kpi-note{font-size:.64rem;line-height:1.30;}
  .d-section{margin-top:16px;}
  .d-heading h1{font-size:1.28rem!important;}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}
</style>
"""

def apply_theme_v2():
    apply_theme()
    st.markdown(CSS_V2, unsafe_allow_html=True)
