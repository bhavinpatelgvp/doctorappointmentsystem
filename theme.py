"""
Gujarat Vidyapith-inspired UI theme.

Provides the CSS injection and helpers for a consistent, minimal,
professional and accessible interface using cream/off-white and earthy brown.
"""
import streamlit as st

CSS = """
<style>
:root {
  --gv-cream: #F7F1E3;
  --gv-brown: #5C3A21;
  --gv-dusty: #8A6D4F;
  --gv-tan: #D9C7A7;
  --gv-text: #3B2A1A;
  --gv-white: #FFFFFF;
}

/* Background */
.stApp {
  background-color: var(--gv-cream);
  color: var(--gv-text);
  font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}

/* Header */
.gv-header {
  background: linear-gradient(135deg, var(--gv-brown) 0%, var(--gv-dusty) 100%);
  color: #FFF8EC;
  padding: 1.1rem 1.5rem;
  border-radius: 10px;
  margin-bottom: 0.4rem;
  box-shadow: 0 3px 10px rgba(0,0,0,0.15);
}
.gv-header-title { display: flex; flex-direction: column; }
.gv-org { font-size: 1.7rem; font-weight: 700; letter-spacing: 0.5px; }
.gv-subtitle { font-size: 1rem; opacity: 0.92; margin-top: 2px; }
.gv-tagline {
  text-align: center; color: var(--gv-dusty); font-size: 0.95rem;
  font-style: italic; margin-bottom: 1rem;
}

/* Footer */
.gv-footer {
  text-align: center; color: var(--gv-dusty); font-size: 0.8rem;
  margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--gv-tan);
}

/* Cards */
.gv-card {
  background: var(--gv-white); border: 1px solid var(--gv-tan);
  border-left: 5px solid var(--gv-brown); border-radius: 8px;
  padding: 1rem 1.2rem; margin-bottom: 0.8rem;
  box-shadow: 0 1px 4px rgba(92,58,33,0.08);
}
.gv-card-icon { font-size: 1.5rem; }
.gv-card-value { font-size: 1.9rem; font-weight: 700; color: var(--gv-brown); }
.gv-card-label { font-size: 0.85rem; color: var(--gv-dusty); }

/* Section titles */
.gv-section-title {
  font-size: 1.25rem; font-weight: 700; color: var(--gv-brown);
  border-bottom: 2px solid var(--gv-tan); padding-bottom: 0.3rem;
  margin: 1.2rem 0 0.8rem;
}

/* Empty state */
.gv-empty {
  text-align: center; color: var(--gv-dusty); padding: 2rem;
  border: 1px dashed var(--gv-tan); border-radius: 8px; background: var(--gv-white);
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: var(--gv-white);
  border-right: 1px solid var(--gv-tan);
}

/* Buttons */
.stButton > button {
  background: var(--gv-brown); color: #FFF8EC;
  border: none; border-radius: 6px; font-weight: 600;
}
.stButton > button:hover {
  background: var(--gv-dusty); color: #FFF8EC;
}

/* Dataframe & tables */
[data-testid="stDataFrame"] { background: var(--gv-white); border-radius: 8px; }

/* Headings */
h1, h2, h3 { color: var(--gv-brown); }

/* Inputs */
.stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] {
  background: var(--gv-white);
}
</style>
"""


def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def set_page_config():
    st.set_page_config(
        page_title="Gujarat Vidyapith · Doctor Appointment & Medical Management System",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
    )
