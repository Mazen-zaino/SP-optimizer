import streamlit as st
import anthropic
import requests
import json
import time

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SP Optimizer",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .section-header {
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.07em;
        text-transform: uppercase; color: #888;
        margin-top: 1.5rem; margin-bottom: 0.3rem;
    }
    .badge {
        display: inline-block; padding: 4px 14px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 600; margin-bottom: 0.6rem;
    }
    .badge-solar  { background:#EAF3DE; color:#3B6D11; }
    .badge-wind   { background:#E6F1FB; color:#185FA5; }
    .badge-hybrid { background:#EEEDFE; color:#534AB7; }
    .badge-hydro  { background:#E1F5EE; color:#0F6E56; }
    table { width:100%; font-size:0.82rem; border-collapse:collapse; }
    td { padding:6px 4px; border-bottom:1px solid #f0f0f0; }
    td:first-child { color:#666; width:55%; }
    td:last-child  { font-weight:600; text-align:right; }
    tr:last-child td { border-bottom:none; }
    .bullet { font-size:0.84rem; color:#555; padding:3px 0; line-height:1.55; }
    .source-note { font-size:0.72rem; color:#aaa; margin-top:0.3rem; font-style:italic; }
    .climate-card {
        background:#f8f9fa; border:1px solid #e9ecef;
        border-radius:10px; padding:1rem 1.2rem; margin:0.8rem 0;
    }
    .climate-card h4 {
        font-size:0.75rem; text-transform:uppercase;
        letter-spacing:0.06em; color:#888; margin-bottom:0.6rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Project types ─────────────────────────────────────────────────────────────
PROJECT_TYPES = {
    "⚡ Utility-scale IPP":           "utility",
    "🏭 Commercial & Industrial":     "ci",
    "🏘️ Residential / Community":     "residential",
    "🏕️ Remote / Off-grid":           "offgrid",
    "🏛️ Municipal / Public Sector":   "municipal",
    "🌾 Agri-PV / Agrivoltaics":      "agri",
    "🔥 Industrial Process Energy":   "industrial",
    "🚗 EV Charging / Mobility Hub":  "ev",
    "🖥️ Data Center / Tech Campus":   "datacenter",
    "🏙️ Mixed-use Development":       "mixed",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ SP Optimizer")
    st.markdown("---")
    api_key = ""
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.success("API key loaded ✅")
    except Exception:
        api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
        if not api_key:
            st.info("Enter your API key or add it to `.streamlit/secrets.toml`")
    st.markdown("---")
    st.markdown("""
**Auto-fetched from NASA POWER:**
- Global Horizontal Irradiance (GHI)
- Peak sun hours (PSH)
- Wind speed at 50m hub height
- Average temperature & humidity
- Precipitation data

22-year climatological average — covers every coordinate on Earth.
""")

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("SP Optimizer")
st.markdown("Enter your **connected load** and **location** — all climate and solar resource data is fetched automatically from NASA's global database.")

# ── Core inputs ───────────────────────────────────────────────────────────────
st.markdown('<p class="section-header">Core inputs</p>', unsafe_allow_html=True)

c1, c2, c3 = st.columns([3, 1.5, 1])
coord_input = c1.text_input(
    "📍 Project location",
    placeholder="Coordinates: 25.2048, 55.2708   or   City name: Dubai, UAE",
    help="Decimal lat/lon gives most accurate climate data. City name also accepted."
)
connected_power = c2.number_input(
    "⚡ Total connected power", min_value=0.0, value=None,
    placeholder="e.g. 50", format="%.2f",
    help="Total electrical load or power demand to be served by the renewable system."
)
power_unit = c3.selectbox("Unit", ["kW", "MW", "GW"])

st.markdown('<p class="section-header">Project type</p>', unsafe_allow_html=True)
project_label = st.selectbox("Project type", list(PROJECT_TYPES.keys()), label_visibility="collapsed")

with st.expander("💰 Financial parameters (optional — AI estimates if blank)"):
    f1, f2, f3, f4 = st.columns(4)
    budget   = f1.number_input("Budget (USD M)",              min_value=0.0, value=None, placeholder="e.g. 180",  format="%.1f")
    tariff   = f2.number_input("Target tariff / PPA (¢/kWh)", min_value=0.0, value=None, placeholder="e.g. 2.5",  format="%.2f")
    wacc     = f3.number_input("WACC / discount rate (%)",    min_value=0.0, max_value=30.0, value=None, placeholder="e.g. 7", format="%.1f")
    lifetime = f4.number_input("Project lifetime (years)",    min_value=1, max_value=50, value=None, placeholder="e.g. 25", format="%d")

with st.expander("🎯 Preferences (optional)"):
    preferred_sources = st.multiselect("Preferred energy sources (leave blank = AI decides)", [
        "Solar PV", "Onshore wind", "Offshore wind", "Solar + Wind hybrid",
        "BESS / storage", "Hydropower", "Green hydrogen", "AI decides best mix",
    ])
    priorities = st.multiselect("Project priorities", [
        "Maximize CO₂ offset", "Minimize LCOE", "Maximize IRR", "Minimize land use",
        "Energy security / resilience", "Water-scarce optimization",
        "Biodiversity-sensitive site", "Local content requirements",
        "Green certification (LEED/BREEAM)", "Net-zero roadmap alignment",
    ])
    notes = st.text_area("Additional notes", placeholder="e.g. COD deadline, height restrictions, local content %...")

st.markdown("")
go = st.button("⚡ Fetch climate data & generate report", use_container_width=True, type="primary")


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_coordinates(text):
    text = text.strip()
    parts = text.replace(";", ",").split(",")
    if len(parts) == 2:
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            pass
    return None


def geocode_city(city_name):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city_name, "format": "json", "limit": 1},
            headers={"User-Agent": "SPOptimizer/1.0"},
            timeout=10
        )
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def reverse_geocode(lat, lon):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "SPOptimizer/1.0"},
            timeout=10
        )
        addr = r.json().get("address", {})
        parts = [addr[k] for k in ["city","town","village","state","country"] if addr.get(k)]
        return ", ".join(parts[:2]) if parts else f"{lat:.3f}, {lon:.3f}"
    except Exception:
        return f"{lat:.4f}, {lon:.4f}"


def fetch_nasa_power(lat, lon):
    params_list = "ALLSKY_SFC_SW_DWN,CLRSKY_SFC_SW_DWN,WS50M,WS10M,T2M,PRECTOTCORR,RH2M"
    url = (
        f"https://power.larc.nasa.gov/api/temporal/climatology/point"
        f"?parameters={params_list}&community=RE"
        f"&longitude={lon}&latitude={lat}&format=JSON"
    )
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        props = r.json()["properties"]["parameter"]

        ghi_d  = props.get("ALLSKY_SFC_SW_DWN", {}).get("ANN")
        clr    = props.get("CLRSKY_SFC_SW_DWN", {}).get("ANN")
        ws50   = props.get("WS50M", {}).get("ANN")
        ws10   = props.get("WS10M", {}).get("ANN")
        temp   = props.get("T2M",   {}).get("ANN")
        precip = props.get("PRECTOTCORR", {}).get("ANN")
        humid  = props.get("RH2M",  {}).get("ANN")

        return {
            "ghi_daily_kwh_m2":  round(ghi_d, 2) if ghi_d else None,
            "ghi_annual_kwh_m2": int(ghi_d * 365) if ghi_d else None,
            "psh":               round(ghi_d, 2) if ghi_d else None,
            "clear_sky_ghi":     round(clr, 2) if clr else None,
            "wind_speed_50m":    round(ws50, 2) if ws50 else None,
            "wind_speed_10m":    round(ws10, 2) if ws10 else None,
            "avg_temp_c":        round(temp, 1) if temp else None,
            "avg_precip_mm_day": round(precip, 2) if precip else None,
            "avg_humidity_pct":  round(humid, 1) if humid else None,
            "source":            "NASA POWER Climatology API (22-year average)",
        }
    except Exception as e:
        return {"error": str(e)}


def to_kw(value, unit):
    return value * {"kW": 1, "MW": 1000, "GW": 1_000_000}[unit]


def build_prompt(project_label, connected_kw, location_name, lat, lon, climate, fin, pref):
    return f"""You are a senior renewable energy engineer and project finance advisor.

PROJECT TYPE: {project_label}
LOCATION: {location_name} (Lat {lat:.4f}, Lon {lon:.4f})
CONNECTED LOAD: {connected_kw:,.1f} kW ({connected_kw/1000:.3f} MW)

NASA POWER CLIMATE DATA (use these exact values in your sizing):
- Daily GHI: {climate.get('ghi_daily_kwh_m2','N/A')} kWh/m²/day
- Annual GHI: {climate.get('ghi_annual_kwh_m2','N/A')} kWh/m²/yr
- Peak sun hours: {climate.get('psh','N/A')} hrs/day
- Clear-sky GHI: {climate.get('clear_sky_ghi','N/A')} kWh/m²/day
- Wind speed at 50m: {climate.get('wind_speed_50m','N/A')} m/s
- Wind speed at 10m: {climate.get('wind_speed_10m','N/A')} m/s
- Avg temperature: {climate.get('avg_temp_c','N/A')} °C
- Avg humidity: {climate.get('avg_humidity_pct','N/A')} %
- Avg precipitation: {climate.get('avg_precip_mm_day','N/A')} mm/day

FINANCIAL INPUTS:
- Budget: {fin.get('budget') or 'not specified — AI to estimate based on system size'}
- Target tariff/PPA: {fin.get('tariff') or 'not specified — AI to estimate market rate'}
- WACC: {fin.get('wacc') or 8}%
- Project lifetime: {fin.get('lifetime') or 25} years

PREFERENCES:
- Sources: {pref.get('sources') or 'AI to select optimal mix based on climate data'}
- Priorities: {pref.get('priorities') or 'balanced optimisation'}
- Notes: {pref.get('notes') or 'none'}

Design the optimal renewable energy system to serve the connected load. Use the NASA climate data to derive specific yield, capacity factor, and generation estimates. Be quantitative and realistic throughout.

Respond ONLY with a valid JSON object — no markdown, no code fences.

{{
  "recommended_mix": "string",
  "source_badge": "solar or wind or hybrid or hydro",
  "executive_summary": "4-5 sentences: optimal source mix for this location, climate advantages, system design rationale, headline financial outcome",
  "climate_assessment": {{
    "solar_suitability": "Excellent / Good / Moderate / Poor — one-line reason citing the GHI value",
    "wind_suitability":  "Excellent / Good / Moderate / Poor — one-line reason citing the wind speed",
    "temperature_impact": "How {climate.get('avg_temp_c','N/A')}°C average affects panel efficiency and system design",
    "seasonal_note": "Key seasonal generation pattern for this latitude and climate zone"
  }},
  "kpis": [
    {{"label":"Renewable capacity","value":"string","unit":"kWp or MWp"}},
    {{"label":"Annual generation","value":"string","unit":"MWh/yr or GWh/yr"}},
    {{"label":"Self-sufficiency","value":"string","unit":"%"}},
    {{"label":"Capacity factor","value":"string","unit":"%"}},
    {{"label":"Specific yield","value":"string","unit":"kWh/kWp/yr"}},
    {{"label":"Total CAPEX","value":"string","unit":"USD M"}},
    {{"label":"CAPEX per kWp","value":"string","unit":"USD/kWp"}},
    {{"label":"LCOE","value":"string","unit":"$/MWh"}},
    {{"label":"Project IRR","value":"string","unit":"%"}},
    {{"label":"Simple payback","value":"string","unit":"years"}},
    {{"label":"CO₂ offset","value":"string","unit":"t/yr"}},
    {{"label":"Land required","value":"string","unit":"ha"}}
  ],
  "technical_sections": [
    {{"title":"Solar PV specifications","rows":[["param","value"]]}},
    {{"title":"Inverter & power conversion","rows":[["param","value"]]}},
    {{"title":"Battery storage (if applicable)","rows":[["param","value"]]}},
    {{"title":"Grid & balance of system","rows":[["param","value"]]}}
  ],
  "financial_sections": [
    {{"title":"Capital cost breakdown","rows":[["param","value"]]}},
    {{"title":"Financial returns","rows":[["param","value"]]}}
  ],
  "sustainability": {{
    "co2_offset_per_year": "string with unit",
    "lifetime_co2_offset": "string with unit",
    "equivalent_context": "string",
    "water_impact": "string",
    "biodiversity_risk": "Low / Medium / High + reason",
    "sdg_alignment": ["SDG 7 — string","SDG 13 — string","SDG string"]
  }},
  "key_risks": ["string","string","string","string"],
  "mitigations": ["string","string","string","string"],
  "permitting": ["string","string","string"],
  "next_steps": ["string","string","string","string","string"]
}}"""


def render(d, climate, location_name, lat, lon, connected_power, power_unit):
    badge_cls = {"solar":"badge-solar","wind":"badge-wind","hybrid":"badge-hybrid","hydro":"badge-hydro"}.get(d.get("source_badge","solar"),"badge-solar")
    st.markdown(f'<span class="badge {badge_cls}">{d.get("recommended_mix","")}</span>', unsafe_allow_html=True)
    st.markdown(d.get("executive_summary",""))

    ca = d.get("climate_assessment", {})
    if ca:
        st.markdown('<div class="climate-card"><h4>Climate assessment for this site</h4>', unsafe_allow_html=True)
        for label, key in [
            ("☀️ Solar suitability", "solar_suitability"),
            ("💨 Wind suitability",  "wind_suitability"),
            ("🌡️ Temperature impact","temperature_impact"),
            ("📅 Seasonal profile",  "seasonal_note"),
        ]:
            if ca.get(key):
                st.markdown(f"**{label}:** {ca[key]}")
        st.markdown("</div>", unsafe_allow_html=True)

    kpis = d.get("kpis", [])
    for row_start in range(0, min(len(kpis), 12), 4):
        chunk = kpis[row_start:row_start+4]
        cols = st.columns(len(chunk))
        for i, k in enumerate(chunk):
            cols[i].metric(k.get("label",""), f'{k.get("value","")}', k.get("unit",""))

    st.divider()

    tech = d.get("technical_sections", [])
    if tech:
        st.subheader("Technical specifications")
        for pair in [tech[i:i+2] for i in range(0, len(tech), 2)]:
            cols = st.columns(len(pair))
            for i, sec in enumerate(pair):
                with cols[i]:
                    with st.expander(sec["title"], expanded=True):
                        html = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td></tr>" for r in sec.get("rows",[]))
                        st.markdown(f"<table>{html}</table>", unsafe_allow_html=True)

    st.divider()

    fin = d.get("financial_sections", [])
    if fin:
        st.subheader("Financial analysis")
        for pair in [fin[i:i+2] for i in range(0, len(fin), 2)]:
            cols = st.columns(len(pair))
            for i, sec in enumerate(pair):
                with cols[i]:
                    with st.expander(sec["title"], expanded=True):
                        html = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td></tr>" for r in sec.get("rows",[]))
                        st.markdown(f"<table>{html}</table>", unsafe_allow_html=True)

    st.divider()

    sus = d.get("sustainability", {})
    if sus:
        st.subheader("Sustainability & environmental impact")
        c1, c2 = st.columns(2)
        c1.metric("CO₂ offset / year",  sus.get("co2_offset_per_year","—"))
        c1.metric("Lifetime CO₂ offset", sus.get("lifetime_co2_offset","—"))
        c2.metric("Equivalent impact",   sus.get("equivalent_context","—"))
        c2.metric("Biodiversity risk",   sus.get("biodiversity_risk","—"))
        st.caption(f"**Water:** {sus.get('water_impact','—')}")
        if sus.get("sdg_alignment"):
            st.caption("**SDG alignment:** " + "  ·  ".join(sus["sdg_alignment"]))

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Key risks")
        for r in d.get("key_risks", []):
            st.markdown(f'<p class="bullet">• {r}</p>', unsafe_allow_html=True)
    with c2:
        st.subheader("Mitigations")
        for m in d.get("mitigations", []):
            st.markdown(f'<p class="bullet">• {m}</p>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Permitting & regulatory approvals")
    for p in d.get("permitting", []):
        st.markdown(f'<p class="bullet">• {p}</p>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Recommended next steps")
    for i, s in enumerate(d.get("next_steps",[]), 1):
        st.markdown(f"**{i}.** {s}")


# ── Main execution ────────────────────────────────────────────────────────────
if go:
    if not api_key:
        st.error("Please enter your Anthropic API key in the sidebar.")
        st.stop()
    if not coord_input:
        st.error("Please enter a location.")
        st.stop()
    if not connected_power:
        st.error("Please enter the total connected power.")
        st.stop()

    with st.status("Running SP Optimizer...", expanded=True) as status:

        # Step 1 — Resolve coordinates
        st.write("📍 Resolving location...")
        coords = parse_coordinates(coord_input)
        if coords:
            lat, lon = coords
            location_name = reverse_geocode(lat, lon)
        else:
            st.write(f"🔍 Geocoding '{coord_input}'...")
            result = geocode_city(coord_input)
            if not result:
                status.update(label="Location not found", state="error")
                st.error(f"Could not find '{coord_input}'. Try decimal coordinates: e.g. 25.2048, 55.2708")
                st.stop()
            lat, lon = result
            location_name = coord_input
        st.write(f"✅ **{location_name}** — {lat:.4f}°N, {lon:.4f}°E")

        # Step 2 — NASA POWER
        st.write("🛰️ Fetching climate data from NASA POWER API...")
        climate = fetch_nasa_power(lat, lon)
        if "error" in climate:
            status.update(label="NASA API error", state="error")
            st.error(f"NASA POWER error: {climate['error']}. Try again shortly.")
            st.stop()
        st.write(f"✅ Climate data loaded — GHI: {climate.get('ghi_daily_kwh_m2','—')} kWh/m²/day, Wind @ 50m: {climate.get('wind_speed_50m','—')} m/s, Temp: {climate.get('avg_temp_c','—')}°C")

        # Step 3 — AI generation
        st.write("🤖 Generating technical and financial specification...")
        connected_kw = to_kw(connected_power, power_unit)
        fin  = {"budget": f"USD {budget:.1f}M" if budget else None, "tariff": f"{tariff:.2f} ¢/kWh" if tariff else None, "wacc": wacc, "lifetime": lifetime}
        pref = {"sources": ", ".join(preferred_sources) if preferred_sources else None, "priorities": ", ".join(priorities) if priorities else None, "notes": notes or None}

        try:
            client  = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=3500,
                messages=[{"role":"user","content": build_prompt(project_label, connected_kw, location_name, lat, lon, climate, fin, pref)}],
            )
            raw    = message.content[0].text.strip().replace("```json","").replace("```","").strip()
            result = json.loads(raw)
            status.update(label="Report ready ✅", state="complete", expanded=False)
        except json.JSONDecodeError as e:
            status.update(label="Parse error", state="error")
            st.error(f"AI response parse error — please try again. ({e})")
            st.stop()
        except anthropic.AuthenticationError:
            status.update(label="Auth error", state="error")
            st.error("Invalid Anthropic API key.")
            st.stop()
        except Exception as e:
            status.update(label="Error", state="error")
            st.error(f"Error: {e}")
            st.stop()

    # ── Climate data summary ──────────────────────────────────────────────────
    st.divider()
    st.subheader(f"📍 {location_name}")
    st.caption(f"Lat {lat:.4f}°, Lon {lon:.4f}°  ·  Connected load: {connected_power:,.1f} {power_unit}  ·  {project_label}")

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Daily GHI",       f"{climate.get('ghi_daily_kwh_m2','—')}",  "kWh/m²/day")
    k2.metric("Annual GHI",      f"{climate.get('ghi_annual_kwh_m2','—')}", "kWh/m²/yr")
    k3.metric("Peak sun hours",  f"{climate.get('psh','—')}",               "hrs/day")
    k4.metric("Wind speed @ 50m",f"{climate.get('wind_speed_50m','—')}",    "m/s")
    k5.metric("Avg temperature", f"{climate.get('avg_temp_c','—')}",        "°C")
    k6.metric("Avg humidity",    f"{climate.get('avg_humidity_pct','—')}",  "%")
    st.markdown(f'<p class="source-note">{climate.get("source","NASA POWER API")}</p>', unsafe_allow_html=True)

    st.divider()
    render(result, climate, location_name, lat, lon, connected_power, power_unit)

    st.download_button(
        "⬇ Download full report (JSON)",
        data=json.dumps({"project": project_label, "location": location_name, "lat": lat, "lon": lon, "connected_power": f"{connected_power} {power_unit}", "climate_data": climate, "report": result}, indent=2),
        file_name="sp_optimizer_report.json",
        mime="application/json",
    )
