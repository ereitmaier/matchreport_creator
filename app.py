import streamlit as st
import yaml
import requests
import pandas as pd
import io

# Optionele import van WeasyPrint voor PDF-generatie
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False

# -----------------------------------------------------------------------------
# Pagina Configuratie
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Match Report Creator | Team Level Up",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
# Logica voor Minutenberekening
# -----------------------------------------------------------------------------
def parse_time_to_minutes(time_str):
    """Zet tijdnotaties zoals '27:38' of '45' om naar een float getal in minuten."""
    try:
        if ":" in str(time_str):
            parts = str(time_str).split(":")
            return float(parts[0]) + float(parts[1]) / 60.0
        return float(time_str)
    except Exception:
        return 0.0

def calculate_player_minutes(starters_h, subs_h, starters_a, subs_a, events_info, total_match_minutes):
    """
    Berekent het aantal gespeelde minuten per speler op basis van startopstelling en wissels.
    Retourneert een gesorteerde lijst van dicts.
    """
    players = {}

    def init_player(p, team_key, is_starter):
        name = p.get('name', 'Onbekend')
        num = p.get('number', '')
        key = f"{team_key}_{name}"
        players[key] = {
            'name': name,
            'number': num,
            'team': team_key,
            'on_field': is_starter,
            'last_in': 0.0 if is_starter else None,
            'total_minutes': 0.0
        }

    for p in starters_h: init_player(p, 'home', True)
    for p in subs_h: init_player(p, 'home', False)
    for p in starters_a: init_player(p, 'away', True)
    for p in subs_a: init_player(p, 'away', False)

    for ev in events_info:
        if ev.get('marker'):
            continue
        
        ev_name = str(ev.get('event', ''))
        ev_icon = str(ev.get('icon', ''))
        
        if "Wissel" in ev_name or "🔄" in ev_icon:
            t_min = parse_time_to_minutes(ev.get('time', 0))
            team = ev.get('team', '')
            
            # Formaat 'Speler Uit -> Speler In' of via extra veld
            player_info = ev.get('player', '')
            extra = ev.get('extra', '')
            
            p_out_name = None
            p_in_name = None

            if "->" in player_info:
                parts = player_info.split("->")
                p_out_name = parts[0].strip()
                p_in_name = parts[1].strip()
            elif "->" in extra:
                parts = extra.split("->")
                p_out_name = parts[0].strip()
                p_in_name = parts[1].strip()

            # Verwerk speler eruit
            if p_out_name:
                key_out = f"{team}_{p_out_name}"
                if key_out in players and players[key_out]['on_field']:
                    players[key_out]['total_minutes'] += (t_min - players[key_out]['last_in'])
                    players[key_out]['on_field'] = False

            # Verwerk speler erin
            if p_in_name:
                key_in = f"{team}_{p_in_name}"
                if key_in in players and not players[key_in]['on_field']:
                    players[key_in]['on_field'] = True
                    players[key_in]['last_in'] = t_min

    # Eindtijd berekenen voor alle spelers die aan het einde nog op het veld stonden
    for key, pdata in players.items():
        if pdata['on_field']:
            pdata['total_minutes'] += (total_match_minutes - pdata['last_in'])
        pdata['total_minutes'] = round(pdata['total_minutes'])

    # Converteren naar lijst en sorteren van hoog naar laag
    result = list(players.values())
    result.sort(key=lambda x: x['total_minutes'], reverse=True)
    return result

# -----------------------------------------------------------------------------
# PDF Generator
# -----------------------------------------------------------------------------
def generate_pdf_report(match_info, home_score, away_score, starters_h, subs_h, starters_a, subs_a, events_info, minutes_list):
    home_team = match_info.get("home", "Thuisploeg")
    away_team = match_info.get("away", "Uitploeg")
    match_date = match_info.get("date", "Onbekend")
    category = match_info.get("category", "B")
    fmt_val = match_info.get("format", 11)
    half_duration = match_info.get("half_duration", 45)

    ICON_HOME = '<img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/1f3e0.svg" class="icon-sm">'
    ICON_AWAY = '<img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/1f6a9.svg" class="icon-sm">'
    ICON_LINEUP = '<img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/1f465.svg" class="icon-md">'
    ICON_LOG = '<img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/1f4cb.svg" class="icon-md">'
    ICON_TIMER = '<img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/23f1.svg" class="icon-sm">'
    ICON_BALL = '<img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/26bd.svg" class="icon-sm">'
    ICON_SUB = '<img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/1f504.svg" class="icon-sm">'
    ICON_STATS = '<img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/1f4ca.svg" class="icon-md">'

    events_html = ""
    for ev in events_info:
        t_str = ev.get("time", "")
        if ev.get("marker"):
            events_html += f"<tr class='marker-row'><td colspan='4'><b>{ICON_TIMER}{ev.get('event', '')}</b> ({ev.get('extra', '')})</td></tr>"
        else:
            team_name = home_team if ev.get("team") == "home" else (away_team if ev.get("team") == "away" else "-")
            og = " (Eigen Doelpunt)" if ev.get("own_goal") else ""
            
            ev_name = ev.get('event', '')
            ev_icon = ev.get('icon', '')

            if "⚽" in ev_icon or "Goal" in ev_name or "Doelpunt" in ev_name:
                icon_html = ICON_BALL
            elif "🔄" in ev_icon or "Wissel" in ev_name:
                icon_html = ICON_SUB
            elif ev_icon:
                icon_html = f"{ev_icon} "
            else:
                icon_html = ""

            events_html += f"""
            <tr>
                <td><b>{t_str}</b></td>
                <td>{icon_html}{ev_name}{og}</td>
                <td>{team_name}</td>
                <td>{ev.get('player', '-')} {f"({ev.get('extra')})" if ev.get('extra') else ''}</td>
            </tr>
            """

    def render_player_list(players):
        if not players:
            return "<i>Geen spelers opgegeven</i>"
        return "<br>".join([f"#{p.get('number', '')} {p.get('name', '')}" for p in players])

    # HTML opbouw gespeelde minuten tabel
    minutes_html = ""
    for p in minutes_list:
        t_label = home_team if p['team'] == 'home' else away_team
        minutes_html += f"""
        <tr>
            <td>#{p['number']}</td>
            <td><b>{p['name']}</b></td>
            <td>{t_label}</td>
            <td><b>{int(p['total_minutes'])} min</b></td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 15mm; }}
            body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #333; margin: 0; padding: 0; }}
            img {{ max-width: 100%; }}
            .icon-sm {{ width: 14px !important; height: 14px !important; vertical-align: -2px; display: inline-block; margin-right: 6px !important; }}
            .icon-md {{ width: 18px !important; height: 18px !important; vertical-align: -3px; display: inline-block; margin-right: 8px !important; }}
            .header {{ text-align: center; background-color: #1e1e2e; color: #fff; padding: 15px; border-radius: 8px; }}
            .score {{ font-size: 26px; font-weight: bold; margin: 5px 0; }}
            .sub-info {{ font-size: 12px; color: #ccc; }}
            
            .section-title {{ font-size: 16px; font-weight: bold; border-bottom: 2px solid #2980b9; margin-top: 20px; padding-bottom: 5px; color: #2d2d3f; }}
            
            .teams-table {{ width: 100%; margin-top: 10px; border-collapse: separate; border-spacing: 10px 0; }}
            .team-box {{ width: 50%; vertical-align: top; background: #f8f9fa; padding: 12px; border-radius: 6px; border: 1px solid #ddd; font-size: 12px; }}
            .team-box h3 {{ margin-top: 0; margin-bottom: 8px; color: #2980b9; font-size: 14px; }}
            
            table.data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }}
            table.data-table th, table.data-table td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
            table.data-table th {{ background-color: #2d2d3f; color: white; }}
            .marker-row {{ background-color: #eaeded; text-align: center; }}
            .footer {{ margin-top: 25px; text-align: center; font-size: 10px; color: #888; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="score">{home_team} {home_score} - {away_score} {away_team}</div>
            <div class="sub-info">Datum: {match_date} | Categorie {category} | Wedstrijdvorm: {fmt_val}v{fmt_val} | Speeltijd: 2x {half_duration} min</div>
        </div>

        <div class="section-title">{ICON_LINEUP}Opstellingen</div>
        <table class="teams-table">
            <tr>
                <td class="team-box">
                    <h3>{ICON_HOME}{home_team}</h3>
                    <b>Basis:</b><br>{render_player_list(starters_h)}<br><br>
                    <b>Wissels:</b><br>{render_player_list(subs_h)}
                </td>
                <td class="team-box">
                    <h3>{ICON_AWAY}{away_team}</h3>
                    <b>Basis:</b><br>{render_player_list(starters_a)}<br><br>
                    <b>Wissels:</b><br>{render_player_list(subs_a)}
                </td>
            </tr>
        </table>

        <div class="section-title">{ICON_LOG}Wedstrijdverloop</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th width="15%">Tijd</th>
                    <th width="35%">Gebeurtenis</th>
                    <th width="25%">Team</th>
                    <th width="25%">Speler / Details</th>
                </tr>
            </thead>
            <tbody>
                {events_html}
            </tbody>
        </table>

        <div class="section-title">{ICON_STATS}Totaal Gespeelde Minuten per Speler</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th width="10%">#</th>
                    <th width="40%">Speler</th>
                    <th width="30%">Team</th>
                    <th width="20%">Gespeelde Minuten</th>
                </tr>
            </thead>
            <tbody>
                {minutes_html}
            </tbody>
        </table>

        <div class="footer">Gegenereerd door Team Level Up Match Report Creator</div>
    </body>
    </html>
    """

    if WEASYPRINT_AVAILABLE:
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    else:
        return html_content.encode('utf-8')

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
# Sidebar & Routing
# -----------------------------------------------------------------------------
st.sidebar.title("⚽ TLU Match Admin")

query_params = st.query_params
file_param = query_params.get("file", None)
data = None

if file_param:
    st.sidebar.success("🔗 Live Wedstrijd Geladen")
    base_url = "https://team-level-up.com/match-reporter/matches/"
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
    total_match_minutes = half_duration * 2

    # Spelers ophalen
    home_data = teams_info.get("home", {}) if isinstance(teams_info, dict) else data.get("home", [])
    starters_h, subs_h = extract_roster(home_data)

    away_data = teams_info.get("away", {}) if isinstance(teams_info, dict) else data.get("away", [])
    starters_a, subs_a = extract_roster(away_data)

    # Berekening uitslag
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

    # Bereken speelminuten gesorteerd van hoog naar laag
    minutes_list = calculate_player_minutes(starters_h, subs_h, starters_a, subs_a, events_info, total_match_minutes)

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

    # Genereer PDF data
    pdf_file_data = generate_pdf_report(match_info, home_score, away_score, starters_h, subs_h, starters_a, subs_a, events_info, minutes_list)
    mime_type = "application/pdf" if WEASYPRINT_AVAILABLE else "text/html"
    file_ext = "pdf" if WEASYPRINT_AVAILABLE else "html"

    st.sidebar.markdown("---")
    st.sidebar.download_button(
        label=f"📄 Download Wedstrijdrapport ({file_ext.upper()})",
        data=pdf_file_data,
        file_name=f"rapport_{match_date}_{home_team}_vs_{away_team}.{file_ext}",
        mime=mime_type,
        use_container_width=True
    )

    # Tabs
    tab_log, tab_lineup, tab_stats, tab_raw = st.tabs(["📋 Live Wedstrijdverloop", "👥 Opstellingen", "📊 Speelminuten", "📄 Ruwe Data & Export"])

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
        with col_h:
            st.subheader(f"🏠 {home_team}")
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

        with col_a:
            st.subheader(f"🚩 {away_team}")
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

    with tab_stats:
        st.subheader("Totaal Gespeelde Minuten per Speler")
        df_minutes = pd.DataFrame([
            {
                "Rugnummer": p['number'],
                "Speler": p['name'],
                "Team": home_team if p['team'] == 'home' else away_team,
                "Gespeelde Minuten": f"{int(p['total_minutes'])} min"
            }
            for p in minutes_list
        ])
        st.dataframe(df_minutes, use_container_width=True, hide_index=True)

    with tab_raw:
        st.subheader("Exporteer Opties")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.download_button(
                label=f"📄 Download Wedstrijdrapport als {file_ext.upper()}",
                data=pdf_file_data,
                file_name=f"rapport_{match_date}_{home_team}_vs_{away_team}.{file_ext}",
                mime=mime_type,
                use_container_width=True
            )
        with col_exp2:
            yaml_string = yaml.dump(data, default_flow_style=False, allow_unicode=True)
            st.download_button(
                label="💾 Download als YAML Bestand",
                data=yaml_string,
                file_name=f"export_match_{match_date}_{home_team}.yaml",
                mime="text/yaml",
                use_container_width=True
            )

        st.markdown("---")
        st.subheader("Ruwe YAML Code")
        st.code(yaml_string, language="yaml")

else:
    st.info("👋 Welkom bij de Match Report Creator.")