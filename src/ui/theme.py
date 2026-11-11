"""Small CSS layer for accessible Streamlit typography and component spacing."""
import html
import streamlit as st

CSS = """
<style>
:root {--ink:#14283f;--muted:#61768a;--ice:#d6ecfb;--blue:#2b76a5;--border:#dfe8ef;--surface:#ffffff;--bg:#f5f9fc;}
html, body, [data-testid="stAppViewContainer"] {background:var(--bg)!important; color:var(--ink);}
[data-testid="stSidebar"] {background:#102840!important;}
[data-testid="stSidebar"] * {color:#eaf4fb!important;}
[data-testid="stSidebar"] [role="radiogroup"] label {border-radius:8px;padding:7px!important;}
.main .block-container {max-width:1280px;padding-top:2rem;padding-bottom:4rem;}
h1,h2,h3 {color:var(--ink)!important;letter-spacing:-.03em;}
h1 {font-size:2rem!important;line-height:1.2!important;}
h2 {font-size:1.35rem!important;}
h3 {font-size:1.08rem!important;}
p {line-height:1.55;}
small,.muted {color:var(--muted);}
.hero {background:linear-gradient(100deg,#102b46,#1b5275);border-radius:14px;padding:25px 30px;color:#fff;margin-bottom:17px;}
.hero h1 {color:#fff!important;margin:0 0 5px 0;font-size:1.85rem!important;}
.hero p {color:#d9e9f5;margin:0;font-size:0.95rem;}
.eyebrow {color:#a6d8fa;font-size:.72em;letter-spacing:.14em;font-weight:700;margin-bottom:8px;}
.stat {background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:19px 18px;min-height:120px;}
.stat .value {font-size:1.8rem;font-weight:760;color:var(--ink);line-height:1.15;overflow-wrap:anywhere;}
.stat .label {color:var(--muted);font-size:.79rem;margin-top:8px;}
.insight {background:white;border:1px solid var(--border);border-left:3px solid #65b5e8;border-radius:9px;padding:15px 19px;height:100%;}
.insight .scope {font-size:.74rem;font-weight:700;color:var(--blue);margin-bottom:8px;}
.insight .headline {font-weight:730;font-size:1.08rem;color:var(--ink);margin-bottom:9px;}
.insight p {margin:5px 0;font-size:.84rem;color:#486174;}
.insight strong {color:#173b5b;}
.sectionintro {font-size:.9rem;color:var(--muted);margin-bottom:12px;}
.method {background:#eaf5fc;border-left:3px solid #8cc5e9;padding:11px 15px;border-radius:6px;color:#31526b;font-size:.84rem;}
.stButton button,.stLinkButton a {border-radius:9px!important;}
[data-testid="stMetric"] {background:#fff;border:1px solid var(--border);border-radius:10px;padding:12px;}
[data-testid="stDataFrame"] {border:1px solid var(--border);border-radius:9px;overflow:hidden;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;}
@media(max-width:700px){.main .block-container{padding:1rem .75rem}.hero{padding:22px 18px}.hero h1{font-size:1.5rem!important}.stat{min-height:100px;padding:14px}.stat .value{font-size:1.45rem}}
</style>
"""


def apply_theme(): st.markdown(CSS, unsafe_allow_html=True)


def hero(title, description, kicker="OPEN-SOURCE DELIVERY ANALYTICS"):
    st.markdown(f'<div class="hero"><div class="eyebrow">{html.escape(kicker)}</div><h1>{html.escape(title)}</h1><p>{html.escape(description)}</p></div>', unsafe_allow_html=True)


def stat(label, value):
    st.markdown(f'<div class="stat"><div class="value">{html.escape(str(value))}</div><div class="label">{html.escape(label)}</div></div>', unsafe_allow_html=True)


def insight(item):
    safe = lambda x: html.escape(str(x))
    st.markdown(f'''<div class="insight"><div class="scope">{safe(item['scope'])}</div>
    <div class="headline">{safe(item['headline'])}</div>
    <p><strong>Evidence</strong> — {safe(item['evidence'])}</p>
    <p><strong>Interpretation</strong> — {safe(item['interpretation'])}</p>
    <p><strong>Next review</strong> — {safe(item['review'])}</p></div>''',unsafe_allow_html=True)
    st.link_button("View source evidence", item["url"])


def empty_state(message="No verified data available yet"):
    st.info(message + ". Run discovery and the initial synchronization to populate this view. No fabricated numbers are shown.")
