"""
frontend/streamlit_app.py
──────────────────────────
Self-contained Streamlit app — no FastAPI backend required.
Imports FilterEngine and calls Groq directly.

Run:
    streamlit run frontend/streamlit_app.py --server.headless true
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
import streamlit as st

# ── Path setup so src/* is importable ─────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.loader import load_dataset
from src.filter.engine import CityNotFoundError, FilterEngine
from src.filter.schemas import UserPreferences
from src.llm.parser import LLMParseError, parse_response
from src.llm.prompt_builder import PromptBuilder

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Restaurant Recommender",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .app-header { text-align: center; padding: 1rem 0 0.2rem 0; }
    .app-header h1 { font-size: 2.1rem; margin-bottom: 0.1rem; }
    .app-header p  { color: #888; font-size: 1rem; margin-top: 0; }

    .card {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
        background: rgba(128,128,128,0.05);
    }
    .rank-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #e94560;
        color: white;
        border-radius: 50%;
        width: 1.9rem; height: 1.9rem;
        font-weight: 700; font-size: 0.88rem;
        margin-right: 0.5rem;
        vertical-align: middle;
    }
    .restaurant-name {
        font-size: 1.15rem;
        font-weight: 700;
        vertical-align: middle;
    }
    .chip {
        display: inline-block;
        border: 1px solid rgba(128,128,128,0.3);
        border-radius: 20px;
        padding: 0.1rem 0.6rem;
        margin: 0.25rem 0.2rem 0 0;
        font-size: 0.78rem;
        opacity: 0.85;
    }
    .meta-line { margin-top: 0.4rem; font-size: 0.88rem; }
    .explanation {
        margin-top: 0.65rem;
        font-size: 0.87rem;
        opacity: 0.8;
        border-left: 3px solid #e94560;
        padding-left: 0.7rem;
        font-style: italic;
    }
    hr { opacity: 0.2; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="app-header">
    <h1>🍽️ AI Restaurant Recommender</h1>
    <p>Powered by Zomato dataset + Groq LLM</p>
</div>
<hr/>
""", unsafe_allow_html=True)


# ── Load dataset & engine (cached) ────────────────────────────────────────────

DATA_PATH = ROOT / "data" / "zomato_clean.parquet"


@st.cache_resource(show_spinner="Loading restaurant data…")
def get_engine() -> FilterEngine:
    df = load_dataset(str(DATA_PATH))
    return FilterEngine(df)


@st.cache_data(ttl=3600)
def get_locations() -> list[str]:
    return get_engine().available_cities()


@st.cache_data(ttl=3600)
def get_cuisines() -> list[str]:
    return get_engine().available_cuisines()


# ── Groq call (direct HTTP) ───────────────────────────────────────────────────

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


def call_groq(system_prompt: str, user_prompt: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    }
    resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ── Groq API key ──────────────────────────────────────────────────────────────

# Priority: Streamlit secrets → env var → .env file
groq_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
if not groq_key:
    groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("GROQ_API_KEY="):
                groq_key = line.split("=", 1)[1].strip().strip('"')
                break

if not groq_key:
    st.warning(
        "**GROQ_API_KEY not set.** Add it in Streamlit Cloud → App Settings → Secrets:\n\n"
        "```toml\nGROQ_API_KEY = \"your-key-here\"\n```",
        icon="⚠️",
    )

# ── Load data ─────────────────────────────────────────────────────────────────

try:
    engine = get_engine()
    locations = get_locations()
    all_cuisines = get_cuisines()
except Exception as exc:
    st.error(f"Failed to load dataset: {exc}", icon="🔴")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────

if "results" not in st.session_state:
    st.session_state.results = None
if "last_query" not in st.session_state:
    st.session_state.last_query = None

# ── Layout ────────────────────────────────────────────────────────────────────

left, right = st.columns([1, 1.6], gap="large")

# ── LEFT — Preferences form ───────────────────────────────────────────────────

with left:
    st.subheader("Your Preferences")

    location = st.selectbox(
        "Locality",
        options=locations,
        index=locations.index("Indiranagar") if "Indiranagar" in locations else 0,
        help="Select a Bangalore locality (93 available)",
    )

    selected_cuisines = st.multiselect(
        "Cuisine(s)",
        options=all_cuisines,
        default=[],
        placeholder="Any cuisine — type to search",
    )

    budget_max = st.number_input(
        "Max Budget (₹ for two people)",
        min_value=100,
        max_value=5000,
        value=800,
        step=100,
        help="Maximum amount you're willing to spend for two people",
    )

    min_rating = st.slider(
        "Minimum Rating",
        min_value=0.0,
        max_value=5.0,
        value=3.5,
        step=0.1,
        format="%.1f ⭐",
    )

    extra_prefs = st.text_input(
        "Additional Preferences",
        placeholder="e.g. family-friendly, outdoor seating, romantic",
    )

    search_clicked = st.button(
        "🔍 Find Restaurants",
        use_container_width=True,
        type="primary",
    )

    current_query = (location, tuple(selected_cuisines), budget_max, min_rating, extra_prefs)
    if st.session_state.last_query and st.session_state.last_query != current_query:
        st.session_state.results = None
    st.session_state.last_query = current_query

# ── RIGHT — Results ───────────────────────────────────────────────────────────

with right:
    st.subheader("Recommendations")

    if search_clicked:
        prefs = UserPreferences(
            city=location,
            budget_max=int(budget_max),
            cuisines=selected_cuisines,
            min_rating=min_rating,
            extra_prefs=extra_prefs,
        )

        with st.spinner("Finding the best restaurants for you…"):
            try:
                filter_result = engine.run(prefs)
            except CityNotFoundError as exc:
                st.warning(str(exc), icon="⚠️")
                st.session_state.results = None
                filter_result = None

        if filter_result is not None:
            if not filter_result.candidates:
                st.warning("No restaurants found even after relaxing filters.", icon="⚠️")
                st.session_state.results = None
            else:
                recs = None
                llm_used = False

                if groq_key:
                    try:
                        builder = PromptBuilder()
                        system_prompt, user_prompt = builder.build(prefs, filter_result.candidates)
                        with st.spinner("Asking AI for personalised recommendations…"):
                            raw = call_groq(system_prompt, user_prompt, groq_key)
                        recs = parse_response(raw)
                        llm_used = True
                    except (LLMParseError, requests.RequestException, Exception):
                        recs = None

                # Fallback: top-5 from filter
                if recs is None:
                    fallback = filter_result.candidates[:5]
                    recs = [
                        {
                            "rank": i + 1,
                            "name": r.name,
                            "cuisine": ", ".join(r.cuisines) if r.cuisines else "—",
                            "rating": r.rating or 0.0,
                            "estimated_cost": f"₹{r.approx_cost} for two" if r.approx_cost else "N/A",
                            "explanation": "",
                        }
                        for i, r in enumerate(fallback)
                    ]

                st.session_state.results = {
                    "recs": [
                        r if isinstance(r, dict) else r.model_dump()
                        for r in recs
                    ],
                    "total": filter_result.total_before_limit,
                    "relaxed": filter_result.filters_relaxed,
                    "llm_used": llm_used,
                    "message": filter_result.message,
                }

    # ── Render results ────────────────────────────────────────────────────────

    if st.session_state.results:
        data = st.session_state.results
        recs = data["recs"]
        total = data["total"]
        relaxed = data["relaxed"]
        llm_used = data["llm_used"]
        message = data.get("message") or ""

        parts = [f"**{total}** restaurants matched"]
        if relaxed:
            parts.append("⚠️ filters relaxed")
        if not llm_used:
            parts.append("🔄 AI unavailable — showing filter results")
        st.caption(" · ".join(parts) + f" · showing top **{len(recs)}**")

        if message and message not in ("no_results",):
            st.info(message, icon="ℹ️")

        for r in recs:
            cuisine_val = r.get("cuisine", "")
            cuisine_chips = "".join(
                f'<span class="chip">{c.strip()}</span>'
                for c in cuisine_val.split(",")
            )
            explanation_html = (
                f'<div class="explanation">{r["explanation"]}</div>'
                if r.get("explanation")
                else ""
            )
            rating_val = r.get("rating") or 0
            st.markdown(f"""
            <div class="card">
                <span class="rank-badge">{r['rank']}</span>
                <span class="restaurant-name">{r['name']}</span>
                <div class="meta-line">{cuisine_chips}</div>
                <div class="meta-line">
                    ⭐ <strong>{rating_val}</strong>
                    &nbsp;&nbsp;
                    💰 <strong>{r['estimated_cost']}</strong>
                </div>
                {explanation_html}
            </div>
            """, unsafe_allow_html=True)

    elif not search_clicked:
        st.markdown(
            "<div style='text-align:center; opacity:0.45; margin-top:3rem; font-size:1rem;'>"
            "Set your preferences and click <strong>Find Restaurants</strong>"
            "</div>",
            unsafe_allow_html=True,
        )
