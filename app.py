import streamlit as st
import json
import base64
from weasyprint import HTML

# Safely import yaml or provide fallback parser
try:
    import yaml
    def parse_yaml(content_str):
        return yaml.safe_load(content_str)
except ImportError:
    import json
    def parse_yaml(content_str):
        st.warning("PyYAML is niet geïnstalleerd. Zorg dat `pyyaml` in requirements.txt staat.")
        return {}

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

# 1. Page Configuration
st.set_page_config(
    page_title="Match Report Generator",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Theme Sports Look)
st.markdown("""
<style>
    .main {
        background-color: #0f172a;
    }
    .stMetric {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
    .metric-label {
        color: #94a3b8 !important;
    }
    .event-card {
        background-color: #1e293b;
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 4px solid #ef4444;
    }
    .squad-box {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar Settings
with st.sidebar:
    st.header("⚙️ Instellingen")
    st.write("Upload een `.yaml` wedstrijdlogboek om een dashboard en PDF-verslag te genereren.")
    st.markdown("---")
    st.caption("Match Report Generator v1.1")

# 3. Main Header
st.title("⚽ Match Report Generator")
st.write("Genereer direct een visueel wedstrijddashboard en PDF-rapport op basis van je YAML match logs.")

# 4. File Upload
uploaded_file = st.file_uploader("Upload YAML Wedstrijdbestand", type=["yaml", "yml"])

# Sample Data if no file is uploaded yet
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

if uploaded_file is not None:
    yaml_content = uploaded_file.getvalue().decode("utf-8")
else:
    st.info("💡 Tip: Upload een YAML-bestand. Een voorbeeld-wedstrijd wordt hieronder getoond.")
    yaml_content = sample_yaml

# Parse YAML
try:
    data = parse_yaml(yaml_content)
except Exception as e:
    st.error(f"Fout bij het lezen van het YAML bestand: {e}")
    data = None

if data:
    match = data.get('match', {})
    teams = data.get('teams', {})
    events = data.get('events', [])

    home_team_name = match.get('home', 'Thuisspelend team')
    away_team_name = match.get('away', 'Uitspelend team')
    match_date = match.get('date', 'Onbekend')

    # Compute score flexibly for NL / EN
    goals = [e for e in events if normalize_event(e.get('event')) == 'goal']
    home_goals = len([g for g in goals if g.get('team') == 'home'])
    away_goals = len([g for g in goals if g.get('team') == 'away'])

    # Tabs structure
    tab_dash, tab_squads, tab_pdf, tab_yaml = st.tabs([
        "📊 Dashboard & Tijdlijn", 
        "👥 Opstellingen", 
        "📄 PDF Rapport Export", 
        "🛠️ Ruwe YAML Data"
    ])

    # --- TAB 1: DASHBOARD ---
    with tab_dash:
        # Scoreboard
        st.markdown("---")
        m_col1, m_col2, m_col3 = st.columns([2, 1, 2])
        with m_col1:
            st.markdown(f"<h1 style='text-align: right; color: #ef4444;'>{home_team_name}</h1>", unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"<h1 style='text-align: center; color: #f59e0b;'>{home_goals} - {away_goals}</h1>", unsafe_allow_html=True)
            st.caption(f"<p style='text-align: center;'>{match_date}</p>", unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"<h1 style='text-align: left; color: #22c55e;'>{away_team_name}</h1>", unsafe_allow_html=True)
        st.markdown("---")

        # Stats Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Goals {home_team_name}", home_goals)
        c2.metric(f"Goals {away_team_name}", away_goals)
        
        home_subs = len([e for e in events if normalize_event(e.get('event')) == 'subst' and e.get('team') == 'home'])
        away_subs = len([e for e in events if normalize_event(e.get('event')) == 'subst' and e.get('team') == 'away'])
        c3.metric(f"Wissels ({home_team_name} / {away_team_name})", f"{home_subs} / {away_subs}")
        
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
            team_label = home_team_name if team == "home" else (away_team_name if team == "away" else "")

            if event_norm in ['start_match', 'end_p1', 'start_p2', 'end_match']:
                st.markdown(f"**───── {time_str} | {event_raw.upper()} ─────**")
            else:
                player_str = f" - <span style='color: #cbd5e1;'>{player}</span>" if player else ""
                extra_str = f" <span style='color: #64748b; font-size: 0.85em;'>({extra})</span>" if extra else ""
                st.markdown(
                    f"""
                    <div style="background-color: #1e293b; padding: 10px; border-radius: 6px; margin-bottom: 6px; border-left: 5px solid {badge_color};">
                        <span style="color: #94a3b8; font-weight: bold; margin-right: 15px;">{time_str}</span>
                        <span style="font-size: 1.1em; margin-right: 10px;">{icon}</span>
                        <strong style="color: white;">{event_raw}</strong>{player_str}{extra_str}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

    # --- TAB 2: SQUADS ---
    with tab_squads:
        col_home, col_away = st.columns(2)

        with col_home:
            st.subheader(f"🔴 {home_team_name} (Thuis)")
            home_data = teams.get('home', {})
            
            starters = home_data.get('starters', home_data if isinstance(home_data, list) else [])
            subs = home_data.get('substitutes', [])

            st.markdown("**Basisopstelling:**")
            for p in starters:
                st.text(f"#{p.get('number', '')} - {p.get('name', '')}")
            
            if subs:
                st.markdown("**Wisselspelers:**")
                for p in subs:
                    st.text(f"#{p.get('number', '')} - {p.get('name', '')}")

        with col_away:
            st.subheader(f"🟢 {away_team_name} (Uit)")
            away_data = teams.get('away', {})
            
            starters = away_data.get('starters', away_data if isinstance(away_data, list) else [])
            subs = away_data.get('substitutes', [])

            st.markdown("**Basisopstelling:**")
            for p in starters:
                st.text(f"#{p.get('number', '')} - {p.get('name', '')}")
            
            if subs:
                st.markdown("**Wisselspelers:**")
                for p in subs:
                    st.text(f"#{p.get('number', '')} - {p.get('name', '')}")

    # --- TAB 3: PDF GENERATION ---
    with tab_pdf:
        st.subheader("📄 Genereer PDF Rapport")
        st.write("Klik op onderstaande knop om het PDF-rapport op te bouwen en te downloaden.")

        def build_html_report():
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

            home_starters = teams.get('home', {}).get('starters', []) if isinstance(teams.get('home'), dict) else teams.get('home', [])
            away_starters = teams.get('away', {}).get('starters', []) if isinstance(teams.get('away'), dict) else teams.get('away', [])

            home_squad_html = "".join([f"<li>#{p.get('number', '')} {p.get('name', '')}</li>" for p in home_starters])
            away_squad_html = "".join([f"<li>#{p.get('number', '')} {p.get('name', '')}</li>" for p in away_starters])

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
                li {{ padding: 2px 0; border-bottom: 1px solid #283548; }}
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
                    <td style="width: 60%; vertical-align: top;">
                        <div class="card">
                            <div class="card-title">⏱️ WEDSTRIJD VERLOOP</div>
                            <table style="width: 100%; border-collapse: collapse; font-size: 8.5pt;">
                                {timeline_rows}
                            </table>
                        </div>
                    </td>
                    <td style="width: 40%; vertical-align: top;">
                        <div class="card">
                            <div class="card-title">🔴 {home_team_name}</div>
                            <ul>{home_squad_html}</ul>
                        </div>
                        <div class="card">
                            <div class="card-title">🟢 {away_team_name}</div>
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
                mime="application/pdf"
            )
            st.success("PDF is succesvol gegenereerd en klaar voor download!")
        except Exception as err:
            st.error(f"Fout bij het genereren van PDF: {err}")

    # --- TAB 4: RAW YAML ---
    with tab_yaml:
        st.subheader("🛠️ Ruwe YAML Inhoud")
        st.code(yaml_content, language="yaml")
