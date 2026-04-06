"""
frontend/streamlit_app.py
──────────────────────────
Streamlit MVP — AI Restaurant Recommender UI.

Run:
    streamlit run frontend/streamlit_app.py --server.headless true

Requires the FastAPI backend running at http://localhost:8000.
"""

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

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


# ── API helpers ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def check_api_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200, r.json()
    except Exception:
        return False, {}


@st.cache_data(ttl=300)
def fetch_locations():
    try:
        r = requests.get(f"{API_BASE}/locations", timeout=5)
        r.raise_for_status()
        return r.json()["cities"]
    except Exception:
        return []


@st.cache_data(ttl=300)
def fetch_cuisines():
    try:
        r = requests.get(f"{API_BASE}/cuisines", timeout=5)
        r.raise_for_status()
        return r.json()["cuisines"]
    except Exception:
        return []


# ── API status banner ─────────────────────────────────────────────────────────

api_ok, health = check_api_health()
if not api_ok:
    st.error(
        "**Backend not reachable.** Start the API first:\n\n"
        "`uvicorn src.api.main:app --reload --port 8000`",
        icon="🔴",
    )
    st.stop()

st.success(
    f"API connected — LLM: **{health.get('llm_provider', 'groq').upper()}**",
    icon="🟢",
)

locations = fetch_locations()
all_cuisines = fetch_cuisines()

# ── Session state — clear results on new search ───────────────────────────────

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

    # Clear stale results when preferences change
    current_query = (location, tuple(selected_cuisines), budget_max, min_rating, extra_prefs)
    if st.session_state.last_query and st.session_state.last_query != current_query:
        st.session_state.results = None
    st.session_state.last_query = current_query

# ── RIGHT — Results ───────────────────────────────────────────────────────────

with right:
    st.subheader("Recommendations")

    if search_clicked:
        payload = {
            "city": location,
            "budget_max": int(budget_max),
            "cuisines": selected_cuisines,
            "min_rating": min_rating,
            "extra_prefs": extra_prefs,
        }

        with st.spinner("Finding the best restaurants for you..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/recommend",
                    json=payload,
                    timeout=30,
                )
            except requests.exceptions.Timeout:
                st.error("Request timed out. Try again.", icon="⏱️")
                st.stop()
            except requests.exceptions.ConnectionError:
                st.error("Could not reach the API. Is it still running?", icon="🔴")
                st.stop()

        if resp.status_code == 404:
            st.warning(resp.json().get("detail", "No results found."), icon="⚠️")
            st.session_state.results = None
        elif resp.status_code == 422:
            st.error(f"Invalid input: {resp.json()}", icon="❌")
            st.session_state.results = None
        elif not resp.ok:
            st.error(f"API error {resp.status_code}: {resp.text}", icon="❌")
            st.session_state.results = None
        else:
            st.session_state.results = resp.json()

    # ── Render stored results ─────────────────────────────────────────────────

    if st.session_state.results:
        data = st.session_state.results
        recs = data["recommendations"]
        total = data["total_candidates"]
        relaxed = data.get("filters_relaxed", False)
        llm_used = data.get("llm_used", True)
        message = data.get("message") or ""

        # Summary bar
        parts = [f"**{total}** restaurants matched"]
        if relaxed:
            parts.append("⚠️ filters relaxed")
        if not llm_used:
            parts.append("🔄 AI fallback (filter results)")
        st.caption(" · ".join(parts) + f" · showing top **{len(recs)}**")

        if message and message not in ("no_results",):
            st.info(message, icon="ℹ️")

        for r in recs:
            cuisine_chips = "".join(
                f'<span class="chip">{c.strip()}</span>'
                for c in r["cuisine"].split(",")
            )
            explanation_html = (
                f'<div class="explanation">{r["explanation"]}</div>'
                if r.get("explanation")
                else ""
            )
            st.markdown(f"""
            <div class="card">
                <span class="rank-badge">{r['rank']}</span>
                <span class="restaurant-name">{r['name']}</span>
                <div class="meta-line">{cuisine_chips}</div>
                <div class="meta-line">
                    ⭐ <strong>{r['rating']}</strong>
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
