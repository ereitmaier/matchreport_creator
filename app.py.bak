import streamlit as st
import yaml
import re
import json
import requests
from weasyprint import HTML

# ---------------------------------------------------------
# CONFIGURATIE URL'S (team-level-up.com)
# ---------------------------------------------------------
API_LIST_URL = "https://team-level-up.com/match-reporter/get_matches.php"
BASE_FILE_URL = "https://team-level-up.com/match-reporter/matches/"

# ---------------------------------------------------------
# 1. HELPER FUNCTIES (NORMALISATIE & PARSING)
# ---------------------------------------------------------

def parse_yaml_content(content_str):
    """Veilige parser voor YAML-inhoud."""
    try:
        return yaml.safe_load(content_str)
    except Exception as e:
        st.error(f"Fout bij het verwerken van het YAML-bestand: {e}")
        return None

def normalize_event(event_str):
    """Normaliseert Engelse en Nederlandse gebeurtenissen."""
    e = str(event_str).lower().strip()
    if e in ['goal', 'doelpunt']:
        return 'goal'
    elif e in ['subst', 'wissel', 'substitution']:
        return 'subst'
    elif 'card' in e or 'kaart' in e:
        return 'card'
    elif e in ['start of match', 'aanvang wedstrijd']:
        return 'start_match'
    elif e in ['end of p1', 'einde periode 1', 'einde 1e helft']:
        return 'end_p1'
    elif e in ['start of second part', 'start 2e periode', 'start 2e helft']:
        return 'start_p2'
    elif e in ['end of match', 'einde wedstrijd']:
        return 'end_match'
    return e

def get_squad_lists(team_data):
    """Haalt veilig starters en substitutes op, ongeacht dict of flat list format."""
    if isinstance(team_data, dict):
        starters = team_data.get('starters', [])
        subs = team_data.get('substitutes', [])
        return starters, subs
    elif isinstance(team_data, list):
        return team_data, []
    return [], []

# ---------------------------------------------------------
# 2. SPEELMINUTEN BEREKENEN
# ---------------------------------------------------------

def calculate_player_minutes(data):
    """
    Berekent per speler het aantal gespeelde minuten op basis van
    de beginopstelling en wissel-events (In: ... | Out: ...).
    """
    teams = data.get('teams', {})
    events = data.get('events', [])
    
    # Bepaal totale duur van de wedstrijd uit het laatste tijdevent
    total_match_minutes = 90
    for e in reversed(events):
        time_str = str(e.get('time', ''))
        match = re.search(r'(\d+):(\d+)', time_str)
        if match:
            mins = int(match.group(1))
            if 'P2' in time_str and mins < 45:
                mins += 45
            total_match_minutes = max(total_match_minutes, mins)
            break

    minutes_summary = {}

    for team_key in ['home', 'away']:
        team_data = teams.get(team_key)
        team_name = data.get('match', {}).get(team_key, 'Thuis' if team_key == 'home' else 'Uit')
        
        starters_list, subs_list = get_squad_lists(team_data)
        
        starters_names = [p.get('name') for p in starters_list if isinstance(p, dict) and p.get('name')]
        subs_names = [p.get('name') for p in subs_list if isinstance(p, dict) and p.get('name')]
        
        all_players = list(set(starters_names + subs_names))
        
        player_on_time = {}
        player_total_mins = {p: 0 for p in all_players}

        # Basisspelers starten op minuut 0
        for p in starters_names:
            player_on_time[p] = 0

        # Verwerk wissel-events chronologisch
        for e in events:
            event_norm = normalize_event(e.get('event', ''))
            if event_norm == 'subst' and e.get('team') == team_key:
                extra = str(e.get('extra', ''))
                time_str = str(e.get('time', ''))
                
                match = re.search(r'(\d+):(\d+)', time_str)
                event_min = int(match.group(1)) if match else 0
                if 'P2' in time_str and event_min < 45:
                    event_min += 45

                in_match = re.search(r'In:\s*([^|]+)', extra)
                out_match = re.search(r'Out:\s*([^|]+)', extra)

                p_in = in_match.group(1).strip() if in_match else None
                p_out = out_match.group(1).strip() if out_match else None

                # Uitgewisselde speler stopt met minuten maken
                if p_out and p_out in player_on_time:
                    played = event_min - player_on_time[p_out]
                    player_total_mins[p_out] = player_total_mins.get(p_out, 0) + max(0, played)
                    del player_on_time[p_out]

                # Invallende speler begint met minuten maken
                if p_in:
                    player_on_time[p_in] = event_min

        # Voeg resterende tijd van de wedstrijd toe voor spelers die nog op het veld staan
        for p, on_min in player_on_time.items():
            played = total_match_minutes - on_min
            player_total_mins[p] = player_total_mins.get(p, 0) + max(0, played)

        minutes_summary[team_name] = (player_total_mins, total_match_minutes)

    return minutes_summary

# ---------------------------------------------------------
# 3. STREAMLIT PAGINA CONFIGURATIE & STYLING
# ---------------------------------------------------------

st.set_page_config(
    page_title="Match Report & Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #0f172a;
        padding: 0.5rem !important;
    }
    
    /* Responsive Scoreboard Container */
    .scoreboard-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .team-title-home {
        color: #ef4444;
        font-weight: bold;
        font-size: clamp(1.2rem, 4vw, 2.2rem);
    }
    .team-title-away {
        color: #22c55e;
        font-weight: bold;
        font-size: clamp(1.2rem, 4vw, 2.2rem);
    }
    .score-badge {
        background-color: #020617;
        color: #f59e0b;
        font-weight: bold;
        font-size: clamp(1.5rem, 5vw, 2.8rem);
        padding: 4px 16px;
        border-radius: 8px;
        display: inline-block;
        margin: 5px 0;
    }

    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #1e293b !important;
        padding: 10px 12px !important;
        border-radius: 10px !important;
        border: 1px solid #334155 !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetricLabel"] p {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetricValue"] div {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.3rem !important;
    }

    @media (max-width: 640px) {
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 10px;
            font-size: 0.82rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. INLADEN VAN WEDSTRIJDDATA (SERVER ARCHIEF / URL / FILE UPLOAD)
# ---------------------------------------------------------

query_params = st.query_params
url_file = query_params.get("file", None)

yaml_content = None

with st.sidebar:
    st.header("📂 Wedstrijd Archief")
    st.caption("Gekoppeld met team-level-up.com")
    
    # Haal recente wedstrijden op van team-level-up.com via PHP
    try:
        response = requests.get(API_LIST_URL, timeout=4)
        if response.status_code == 200:
            match_files = response.json()
            if isinstance(match_files, list) and len(match_files) > 0:
                file_options = {f["name"]: f["url"] for f in match_files}
                
                # Bepaal standaard index als er een bestand in de URL staat
                default_index = 0
                if url_file and url_file in file_options:
                    default_index = list(file_options.keys()).index(url_file)
                
                selected_filename = st.selectbox(
                    "Selecteer opgeslagen wedstrijd:", 
                    list(file_options.keys()),
                    index=default_index
                )
                
                if selected_filename:
                    fetch_res = requests.get(file_options[selected_filename], timeout=4)
                    if fetch_res.status_code == 200:
                        yaml_content = fetch_res.text
            else:
                st.info("Nog geen opgeslagen wedstrijden op de server.")
    except Exception as e:
        st.caption("ℹ️ Geen verbinding met het online archief.")

    st.markdown("---")
    st.caption("Match Report Generator v2.2")

# Fallback: URL Parameter direct inladen indien geselecteerd
if url_file and not yaml_content:
    try:
        res = requests.get(BASE_FILE_URL + url_file, timeout=4)
        if res.status_code == 200:
            yaml_content = res.text
            st.success(f"⚡ Wedstrijd `{url_file}` automatisch ingeladen!")
    except Exception as err:
        st.error(f"Fout bij automatisch inladen van bestand: {err}")

# Handmatige Upload Optie
uploaded_file = st.file_uploader("Upload handmatig een YAML-bestand", type=["yaml", "yml"])
if uploaded_file is not None:
    yaml_content = uploaded_file.getvalue().decode("utf-8")

# Voorbeelddata indien niks gekozen is
sample_yaml = """# Voorbeeld Wedstrijd Log
match:
  date: "2026-05-17"
  home: ZaVr2
  away: Ajax VR3

teams:
  home:
    starters:
      - name: Lisa
        number: 1
      - name: Kim
        number: 2
      - name: Mila
        number: 3
      - name: Sara
        number: 4
      - name: Lotte
        number: 5
      - name: Dane
        number: 7
      - name: Britt
        number: 8
      - name: Fatima
        number: 9
      - name: Nina
        number: 10
      - name: Roos
        number: 11
      - name: Anouk
        number: 15
    substitutes:
      - name: Jade
        number: 6
      - name: Eva
        number: 14
      - name: Fleur
        number: 17
  away:
    starters:
      - name: Sofie
        number: 1
      - name: Lena
        number: 3
      - name: Julia
        number: 5
      - name: Inge
        number: 6
      - name: Hanna
        number: 7
      - name: Noor
        number: 8
      - name: Petra
        number: 9
      - name: Vera
        number: 11
      - name: Rosa
        number: 13
      - name: Tara
        number: 16

events:
  - time: "P1 | 00:00"
    event: "Aanvang wedstrijd"
  - time: "P1 | 00:07"
    event: "Doelpunt"
    icon: "⚽"
    player: "Lotte"
    team: "home"
    extra: "Jade"
  - time: "P1 | 00:20"
    event: "Wissel"
    icon: "🔄"
    player: "Jade"
    team: "home"
    extra: "In: Anouk | Out: Jade"
  - time: "P1 | 00:28"
    event: "Gele kaart"
    icon: "🟨"
    player: "Petra"
    team: "away"
    extra: ""
  - time: "P1 | 00:33"
    event: "Doelpunt"
    icon: "⚽"
    player: "Lotte"
    team: "home"
    extra: "Fatima"
  - time: "P1 | 01:24"
    event: "Einde Periode 1"
  - time: "P2 | 00:00"
    event: "Start 2e periode"
  - time: "P2 | 00:23"
    event: "Doelpunt"
    icon: "⚽"
    player: "Dane"
    team: "home"
    extra: "Lotte"
  - time: "P2 | 00:35"
    event: "Einde wedstrijd"
"""

if not yaml_content:
    yaml_content = sample_yaml

data = parse_yaml_content(yaml_content)

# ---------------------------------------------------------
# 5. STREAMLIT APP WEERGAVE (DASHBOARD, SPEELMINUTEN, PDF)
# ---------------------------------------------------------

st.title("⚽ Match Report & Analytics")

if data:
    match = data.get('match', {})
    teams = data.get('teams', {})
    events = data.get('events', [])

    home_team_name = match.get('home', 'Thuis')
    away_team_name = match.get('away', 'Uit')
    match_date = str(match.get('date', 'Onbekend'))

    # Compute score
    goals = [e for e in events if normalize_event(e.get('event')) == 'goal']
    home_goals = len([g for g in goals if g.get('team') == 'home'])
    away_goals = len([g for g in goals if g.get('team') == 'away'])

    # Tabs Structure
    tab_dash, tab_minutes, tab_squads, tab_pdf, tab_yaml = st.tabs([
        "📊 Dashboard", 
        "⏱️ Speelminuten",
        "👥 Opstelling", 
        "📄 PDF Export", 
        "🛠️ YAML & Bewaren"
    ])

    # --- TAB 1: DASHBOARD ---
    with tab_dash:
        st.markdown(
            f"""
            <div class="scoreboard-box">
                <div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap;">
                    <div class="team-title-home">{home_team_name}</div>
                    <div class="score-badge">{home_goals} - {away_goals}</div>
                    <div class="team-title-away">{away_team_name}</div>
                </div>
                <div style="color: #64748b; font-size: 0.85rem; margin-top: 6px;">📅 Datum: {match_date}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        c1.metric(f"Goals {home_team_name}", home_goals)
        c2.metric(f"Goals {away_team_name}", away_goals)
        
        home_subs = len([e for e in events if normalize_event(e.get('event')) == 'subst' and e.get('team') == 'home'])
        away_subs = len([e for e in events if normalize_event(e.get('event')) == 'subst' and e.get('team') == 'away'])
        c3.metric("Wissels (T / U)", f"{home_subs} / {away_subs}")
        
        cards_count = len([e for e in events if normalize_event(e.get('event')) == 'card'])
        c4.metric("Kaarten", cards_count)

        st.subheader("⏱️ Wedstrijdtijdlijn")
        for e in events:
            time_str = e.get('time', '')
            event_raw = e.get('event', '')
            event_norm = normalize_event(event_raw)
            icon = e.get('icon', '📌')
            player = e.get('player', '')
            team = e.get('team', '')
            extra = e.get('extra', '')

            badge_color = "#ef4444" if team == "home" else ("#22c55e" if team == "away" else "#94a3b8")

            if event_norm in ['start_match', 'end_p1', 'start_p2', 'end_match']:
                st.markdown(f"<div style='text-align: center; color: #64748b; font-size: 0.8rem; margin: 10px 0; font-weight: bold;'>───── {time_str} | {event_raw.upper()} ─────</div>", unsafe_allow_html=True)
            else:
                player_str = f" • <span style='color: #cbd5e1;'>{player}</span>" if player else ""
                extra_str = f" <span style='color: #64748b; font-size: 0.8em;'>({extra})</span>" if extra else ""
                st.markdown(
                    f"""
                    <div style="background-color: #1e293b; padding: 10px 12px; border-radius: 8px; margin-bottom: 6px; border-left: 5px solid {badge_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                            <span style="color: #94a3b8; font-weight: bold; font-size: 0.8rem;">{time_str}</span>
                            <span style="font-size: 1rem;">{icon}</span>
                        </div>
                        <div>
                            <strong style="color: white;">{event_raw}</strong>{player_str}{extra_str}
                        </div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

    # --- TAB 2: SPEELMINUTEN OVERZICHT ---
    with tab_minutes:
        st.subheader("⏱️ Gespeelde Minuten per Speler")
        st.write("Automatisch berekend op basis van de opstelling en wissels:")
        
        minutes_data = calculate_player_minutes(data)
        col_m_home, col_m_away = st.columns(2)

        for idx, (team_name, (players_mins, total_mins)) in enumerate(minutes_data.items()):
            target_col = col_m_home if idx == 0 else col_m_away
            with target_col:
                st.markdown(f"### {team_name}")
                sorted_players = sorted(players_mins.items(), key=lambda x: x[1], reverse=True)
                
                if sorted_players:
                    for p_name, mins in sorted_players:
                        st.write(f"**{p_name}**: {mins} min")
                        progress_val = min(max(mins / float(total_mins if total_mins > 0 else 90), 0.0), 1.0)
                        st.progress(progress_val)
                else:
                    st.info("Geen speelminuten/opstelling gevonden voor dit team.")

    # --- TAB 3: SQUADS ---
    with tab_squads:
        col_home, col_away = st.columns(2)

        with col_home:
            st.subheader(f"🔴 {home_team_name}")
            starters, subs = get_squad_lists(teams.get('home'))

            st.markdown("**Basisopstelling:**")
            for p in starters:
                st.text(f"#{p.get('number', '')} - {p.get('name', '')}")
            
            if subs:
                st.markdown("**Wisselspelers:**")
                for p in subs:
                    st.text(f"#{p.get('number', '')} - {p.get('name', '')}")

        with col_away:
            st.subheader(f"🟢 {away_team_name}")
            starters, subs = get_squad_lists(teams.get('away'))

            st.markdown("**Basisopstelling:**")
            for p in starters:
                st.text(f"#{p.get('number', '')} - {p.get('name', '')}")
            
            if subs:
                st.markdown("**Wisselspelers:**")
                for p in subs:
                    st.text(f"#{p.get('number', '')} - {p.get('name', '')}")

    # --- TAB 4: PDF GENERATION ---
    with tab_pdf:
        st.subheader("📄 Genereer PDF Rapport")
        st.write("Exporteer de wedstrijd direct naar een A4 PDF-rapport inclusief speelminuten.")

        def build_html_report():
            # Bepaal speelminuten per speler voor de PDF
            minutes_data = calculate_player_minutes(data)
            
            timeline_rows = ""
            for e in events:
                event_raw = e.get('event', '')
                event_norm = normalize_event(event_raw)
                if event_norm in ['start_match', 'end_p1', 'start_p2', 'end_match']:
                    timeline_rows += f"""
                    <tr style="background-color: #0f172a; color: #64748b; font-weight: bold; font-size: 8pt;">
                        <td style="padding: 6px;">{e.get('time')}</td>
                        <td colspan="2" style="padding: 6px;">{event_raw.upper()}</td>
                    </tr>
                    """
                else:
                    team = e.get('team', '')
                    t_label = home_team_name if team == 'home' else (away_team_name if team == 'away' else '')
                    badge_cls = "background-color: #ef4444;" if team == 'home' else ("background-color: #22c55e;" if team == 'away' else "")
                    badge = f'<span style="{badge_cls} color: white; font-size: 7pt; padding: 2px 4px; border-radius: 3px; margin-right: 5px;">{t_label}</span>' if t_label else ''
                    icon = e.get('icon', '•')
                    extra_info = f"({e.get('extra')})" if e.get('extra') else ""
                    player_info = e.get('player', '')
                    
                    timeline_rows += f"""
                    <tr style="border-bottom: 1px solid #334155;">
                        <td style="color: #94a3b8; font-weight: bold; padding: 6px; width: 18%;">{e.get('time')}</td>
                        <td style="text-align: center; width: 8%;">{icon}</td>
                        <td style="color: #cbd5e1; padding: 6px;">{badge} <strong>{event_raw}</strong> {player_info} <span style="color: #64748b; font-size: 8pt;">{extra_info}</span></td>
                    </tr>
                    """

            # Render van de spelerslijsten met speelminutentags
            def render_squad_pdf_list(team_key, team_name):
                team_data = teams.get(team_key, {})
                starters, subs = get_squad_lists(team_data)
                all_players = starters + subs
                
                player_mins_dict, _ = minutes_data.get(team_name, ({}, 90))
                
                rows_html = ""
                for p in all_players:
                    p_name = p.get('name', '')
                    p_num = f"#{p.get('number')}" if p.get('number') else ""
                    mins = player_mins_dict.get(p_name, 0)
                    
                    rows_html += f"""
                    <li style="display: flex; justify-content: space-between; align-items: center; padding: 3px 0; border-bottom: 1px solid #283548;">
                        <span><strong style="color: #64748b; margin-right: 4px;">{p_num}</strong> {p_name}</span>
                        <span style="color: #38bdf8; font-size: 7.5pt; font-weight: bold; background: #0f172a; padding: 1px 5px; border-radius: 4px;">{mins} min</span>
                    </li>
                    """
                return rows_html

            home_squad_html = render_squad_pdf_list('home', home_team_name)
            away_squad_html = render_squad_pdf_list('away', away_team_name)

            return f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <style>
                @page {{
                    size: A4;
                    margin: 12mm;
                    background-color: #0f172a;
                }}
                body {{
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    color: #f8fafc;
                    background-color: #0f172a;
                    margin: 0;
                    padding: 0;
                }}
                .header {{
                    background: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                    margin-bottom: 15px;
                }}
                .card {{
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 12px;
                }}
                .card-title {{
                    font-size: 11pt;
                    font-weight: bold;
                    color: #f8fafc;
                    border-bottom: 2px solid #334155;
                    padding-bottom: 5px;
                    margin-bottom: 8px;
                }}
                ul {{ list-style: none; padding: 0; margin: 0; font-size: 8.5pt; color: #cbd5e1; }}
            </style>
            </head>
            <body>
            <div class="header">
                <div style="color: #94a3b8; font-size: 9pt;">OFFICIEEL WEDSTRIJDVERSLAG</div>
                <h1 style="margin: 10px 0; font-size: 24pt;">
                    <span style="color: #ef4444;">{home_team_name}</span> 
                    <span style="color: #f59e0b; margin: 0 15px;">{home_goals} - {away_goals}</span> 
                    <span style="color: #22c55e;">{away_team_name}</span>
                </h1>
                <div style="color: #64748b; font-size: 8.5pt;">Datum: {match_date}</div>
            </div>

            <table style="width: 100%; border-collapse: separate; border-spacing: 10px 0;">
                <tr>
                    <td style="width: 58%; vertical-align: top;">
                        <div class="card">
                            <div class="card-title">⏱️ WEDSTRIJD VERLOOP</div>
                            <table style="width: 100%; border-collapse: collapse; font-size: 8.5pt;">
                                {timeline_rows}
                            </table>
                        </div>
                    </td>
                    <td style="width: 42%; vertical-align: top;">
                        <div class="card">
                            <div class="card-title">🔴 {home_team_name} (SPEELMINUTEN)</div>
                            <ul>{home_squad_html}</ul>
                        </div>
                        <div class="card">
                            <div class="card-title">🟢 {away_team_name} (SPEELMINUTEN)</div>
                            <ul>{away_squad_html}</ul>
                        </div>
                    </td>
                </tr>
            </table>
            </body>
            </html>
            """

        html_doc = build_html_report()

        try:
            pdf_bytes = HTML(string=html_doc).write_pdf()
            st.download_button(
                label="📥 Download PDF Rapport",
                data=pdf_bytes,
                file_name=f"match_report_{home_team_name}_{away_team_name}.pdf",
                use_container_width=True,
                mime="application/pdf"
            )
            st.success("PDF is klaar voor download!")
        except Exception as err:
            st.error(f"Fout bij het genereren van PDF: {err}")

    # --- TAB 5: RAW YAML & BEWAREN ---
    with tab_yaml:
        st.subheader("🛠️ Ruwe YAML Data")
        st.code(yaml_content, language="yaml")
        
        st.download_button(
            label="💾 Bewaar/Download deze YAML",
            data=yaml_content,
            file_name=f"match_{home_team_name}_{away_team_name}_{match_date}.yaml",
            mime="text/yaml",
            use_container_width=True
        )