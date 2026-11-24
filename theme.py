"""
The look of the web app: a black-and-white boutique style with one accent colour.
Streamlit's own colours are set in .streamlit/config.toml; this adds the fonts,
spacing and the small pieces of HTML (top banner, user card) that Streamlit has no widget for.
"""
from __future__ import annotations

import html

ACCENT = "#C8102E"          # used sparingly: hover, "below PAR" and the banner dot


class Theme:
    """Only presentation: no inventory logic here (SRP). Every method returns text for
    ui.markdown(..., unsafe_allow_html=True); anything typed by users is escaped first."""

    CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
html, body, .stApp, [data-testid="stSidebar"], button, input, textarea, select {
    font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
}
#MainMenu, footer {visibility: hidden;}
[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 1.2rem; max-width: 1240px;}

/* headings: small, uppercase, widely spaced */
h1, h2, h3 {text-transform: uppercase; letter-spacing: .14em; font-weight: 600;}
h3 {font-size: .95rem !important; border-bottom: 1px solid #111; padding-bottom: .45rem;
    margin: 1.4rem 0 .9rem 0;}

/* top banner */
.sx-banner {display: flex; justify-content: space-between; align-items: center;
    background: #000; color: #fff; padding: 16px 24px; margin-bottom: 22px;}
.sx-brand {font-weight: 700; letter-spacing: .38em; font-size: 1.05rem;}
.sx-brand .sx-dot {color: ACCENT;}
.sx-meta {font-size: .74rem; letter-spacing: .18em; text-transform: uppercase; opacity: .9;}

/* metric cards */
[data-testid="stMetric"] {border: 1px solid #e6e6e6; border-top: 3px solid #000;
    padding: 14px 18px; background: #fff;}
[data-testid="stMetricLabel"] p {text-transform: uppercase; letter-spacing: .14em;
    font-size: .7rem; color: #6b6b6b;}
[data-testid="stMetricValue"] {font-weight: 600; font-size: 1.7rem;}

/* buttons: square, uppercase; primary ones black, accent on hover */
.stButton > button, .stDownloadButton > button {border-radius: 0; border: 1px solid #111;
    text-transform: uppercase; letter-spacing: .14em; font-size: .72rem; font-weight: 600;
    padding: .6rem 1.3rem;}
.stButton > button[kind="primary"] {background: #000; color: #fff;}
.stButton > button[kind="primary"]:hover {background: ACCENT; border-color: ACCENT; color: #fff;}

/* square inputs, alerts and tables */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"] {border-radius: 0 !important;}
[data-testid="stAlert"] {border-radius: 0;}
[data-testid="stDataFrame"] {border: 1px solid #e6e6e6;}
[data-testid="stExpander"] details {border-radius: 0;}

/* sidebar: white, a user card, and the menu as a list */
[data-testid="stSidebar"] {background: #fff; border-right: 1px solid #e6e6e6;}
.sx-user {border: 1px solid #111; padding: 12px 14px; margin: 4px 0 14px 0;}
.sx-user .sx-name {font-weight: 600; letter-spacing: .06em;}
.sx-user .sx-role {font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; color: #6b6b6b;}
[data-testid="stSidebar"] [role="radiogroup"] label {padding: 7px 2px; border-bottom: 1px solid #f0f0f0;
    width: 100%; letter-spacing: .04em;}

/* the login card */
.sx-login-note {font-size: .78rem; color: #6b6b6b; letter-spacing: .04em;}
</style>
""".replace("ACCENT", ACCENT)

    @staticmethod
    def banner(right: str = "") -> str:
        """The black bar across the top: the app name, and e.g. the store and user on the right."""
        return (f'<div class="sx-banner"><div class="sx-brand">SEPHORA INVENTORY'
                f'<span class="sx-dot"> ●</span></div>'
                f'<div class="sx-meta">{html.escape(right)}</div></div>')

    @staticmethod
    def user_card(username: str, role: str) -> str:
        return (f'<div class="sx-user"><div class="sx-name">{html.escape(username)}</div>'
                f'<div class="sx-role">{html.escape(role)}</div></div>')

    @staticmethod
    def status(below_par: bool, to_order: int) -> str:
        """The Status column: a filled dot when a product needs restocking."""
        return f"● Below PAR · order {to_order}" if below_par else "○ OK"
