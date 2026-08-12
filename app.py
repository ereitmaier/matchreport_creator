import streamlit as st
import yaml
import requests
import pandas as pd

# -----------------------------------------------------------------------------
# Pagina Configuratie
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Match Report Creator | Team Level Up",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling voor Clean Match Header
st.markdown("""
    <style>
    .score-banner {
        background-color: #2d2d3f;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
    }
    .score-title {
        font-size: 32px;
        font-weight: bold;
        color: #ffffff;
        margin: 0;
    }
    .score-sub {
        font-size: 14px;
        color: #aaaaaa;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Data Laders
# -----------------------------------------------------------------------------
def load_yaml_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return yaml.safe_load(response.text)
    except Exception as e:
        st.error(f"Fout bij het laden via server URL: {e}")
        return None

def load_yaml_from_file(uploaded_file):
    try:
        return yaml.safe_load(uploaded_file)
    except Exception as e:
        st.error(f"Fout bij het lezen van het YAML-bestand: {e}")
        return None

# Helper functie om veilig spelers uit te lezen ongeacht YAML-structuur (dict of list)
def extract_roster(team_data):
    starters = []
    substitutes = []
    
    if isinstance(team_data, dict):
        starters = team_data.get("starters", [])
        substitutes = team_data.get("substitutes", [])
    elif isinstance(team_data, list):
        starters = team_data
        
    return starters, substitutes

# -----------------------------------------------------------------------------
# Sidebar & Routing (Admin vs Live Viewer)
# -----------------------------------------------------------------------------
st.sidebar.title("⚽ TLU Match Admin")

query_params = st.query_params
file_param = query_params.get("file", None)

data = None

if file_param:
    st.sidebar.success("🔗 Live Wedstrijd Geladen")
    base_url = "https://team-level-up.com/match-reporter/saved_matches/"
    target_url = base_url + file_param
    st.sidebar.caption(f"Bestand: `{file_param}`")
    data = load_yaml_from_url(target_url)
    
    if st.sidebar.button("❌ Wis URL & Ga naar Desktop Upload"):
        st.query_params.clear()
        st.rerun()

if data is None:
    st.sidebar.subheader("🖥️ Desktop Admin Mode")
    uploaded_file = st.sidebar.file_uploader(
        "Kies een wedstrijd YAML-bestand", 
        type=["yaml", "yml"],
        help="Upload een lokaal gegenereerd bestand uit de setup of app."
    )
    if uploaded_file:
        data = load_yaml_from_file(uploaded_file)

# -----------------------------------------------------------------------------
# Hoofd Rapportage Scherm
# -----------------------------------------------------------------------------
if data:
    match_info = data.get("match", {})
    teams_info = data.get("teams", {})
    events_info = data.get("events", [])

    home_team = match_info.get("home", "Thuisploeg")
    away_team = match_info.get("away", "Uitploeg")
    match_date = match_info.get("date", "Onbekend")
    category = match_info.get("category", "B")
    fmt_val = match_info.get("format", 11)
    half_duration = match_info.get("half_duration", 45)

    # Bereken de uitslag dynamisch op basis van de gelogde events
    home_score = 0
    away_score = 0
    
    for ev in events_info:
        name = ev.get("event", "")
        team = ev.get("team", "")
        own_goal = ev.get("own_goal", False)
        extra = ev.get("extra", "")

        is_goal = False
        if name in ["Doelpunt", "Goal"]:
            is_goal = True
        elif name == "Penalty":
            if not any(x in str(extra) for x in ["Naast/Over", "Gestopt", "Off target", "Blocked"]):
                is_goal = True

        if is_goal:
            if own_goal:
                if team == "home": away_score += 1
                elif team == "away": home_score += 1
            else:
                if team == "home": home_score += 1
                elif team == "away": away_score += 1

    # Header Banner
    st.markdown(f"""
        <div class="score-banner">
            <div class="score-title">{home_team} &nbsp; {home_score} - {away_score} &nbsp; {away_team}</div>
            <div class="score-sub">Datum: {match_date} &nbsp;|&nbsp; Categorie {category} &nbsp;|&nbsp; Wedstrijdvorm: {fmt_val}v{fmt_val} &nbsp;|&nbsp; Speeltijd: 2x {half_duration} min</div>
        </div>
    """, unsafe_allow_html=True)

    # Top KPI Metrics
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Eindstand", f"{home_score} - {away_score}")
    kpi2.metric("Wedstrijdvorm", f"{fmt_val} v {fmt_val}")
    kpi3.metric("Speeltijd per helft", f"{half_duration} min")
    kpi4.metric("Reglement", f"Categorie {category}")

    st.divider()

    # Tabs
    tab_log, tab_lineup, tab_raw = st.tabs(["📋 Live Wedstrijdverloop", "👥 Opstellingen", "📄 Ruwe YAML Data"])

    with tab_log:
        st.subheader("Wedstrijdverloop & Gebeurtenissen")
        if events_info:
            log_data = []
            for ev in events_info:
                if ev.get("marker"):
                    log_data.append({
                        "Tijd": ev.get("time", ""),
                        "Gebeurtenis": f"⏱️ {ev.get('event', '')}",
                        "Team": "-",
                        "Speler": "-",
                        "Details": ev.get("extra", "")
                    })
                else:
                    t_label = home_team if ev.get("team") == "home" else (away_team if ev.get("team") == "away" else "")
                    og_label = " (Eigen Doelpunt)" if ev.get("own_goal") else ""
                    log_data.append({
                        "Tijd": ev.get("time", ""),
                        "Gebeurtenis": f"{ev.get('icon', '')} {ev.get('event', '')}{og_label}",
                        "Team": t_label,
                        "Speler": ev.get("player", "-"),
                        "Details": ev.get("extra", "")
                    })
            
            df_log = pd.DataFrame(log_data)
            st.dataframe(df_log, use_container_width=True, hide_index=True)
        else:
            st.info("Geen gebeurtenissen geregistreerd in dit bestand.")

    with tab_lineup:
        col_h, col_a = st.columns(2)
        
        # Thuisploeg
        with col_h:
            st.subheader(f"🏠 {home_team}")
            home_data = teams_info.get("home", {}) if isinstance(teams_info, dict) else data.get("home", [])
            starters_h, subs_h = extract_roster(home_data)
            
            st.markdown("**Basisopstelling / Selectie:**")
            if starters_h:
                for p in starters_h:
                    st.write(f"• #{p.get('number', '')} {p.get('name', '')}")
            else:
                st.caption("Geen spelers opgegeven.")

            if subs_h:
                st.markdown("**Wisselspelers:**")
                for p in subs_h:
                    st.write(f"• #{p.get('number', '')} {p.get('name', '')}")

        # Uitploeg
        with col_a:
            st.subheader(f"🚩 {away_team}")
            away_data = teams_info.get("away", {}) if isinstance(teams_info, dict) else data.get("away", [])
            starters_a, subs_a = extract_roster(away_data)
            
            st.markdown("**Basisopstelling / Selectie:**")
            if starters_a:
                for p in starters_a:
                    st.write(f"• #{p.get('number', '')} {p.get('name', '')}")
            else:
                st.caption("Geen spelers opgegeven.")

            if subs_a:
                st.markdown("**Wisselspelers:**")
                for p in subs_a:
                    st.write(f"• #{p.get('number', '')} {p.get('name', '')}")

    with tab_raw:
        st.subheader("Ruwe YAML / Exporteren")
        yaml_string = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        st.code(yaml_string, language="yaml")
        st.download_button(
            label="💾 Download als YAML Bestand",
            data=yaml_string,
            file_name=f"export_match_{match_date}_{home_team}.yaml",
            mime="text/yaml"
        )

else:
    st.info("👋 Welkom bij de Match Report Creator.")
    st.markdown("""
        **Instructies:**
        * **Via Live App**: Zodra een wedstrijd wordt opgeslagen in de mobiele `match_app.html`, wordt het rapport hier automatisch geopend.
        * **Via Desktop Admin**: Gebruik de sidebar aan de linkerkant om een eerder opgeslagen `match.yaml` bestand te uploaden.
    """)
