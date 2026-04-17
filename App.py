import streamlit as st
import anthropic
import json

st.set_page_config(page_title="Renewable Energy Project Advisor", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.metric-card{background:#f8f9fa;border-radius:8px;padding:14px 16px;margin-bottom:8px}
.metric-label{font-size:12px;color:#6c757d;margin-bottom:4px}
.metric-value{font-size:22px;font-weight:600;color:#212529}
.metric-unit{font-size:11px;color:#adb5bd}
.section-card{background:#ffffff;border:1px solid #e9ecef;border-radius:10px;padding:18px 20px;margin-bottom:14px}
.badge-solar{background:#d4edda;color:#155724;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600}
.badge-wind{background:#cce5ff;color:#004085;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600}
.badge-hybrid{background:#e2d9f3;color:#432874;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600}
.badge-hydro{background:#d1ecf1;color:#0c5460;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600}
.sdg-tag{display:inline-block;background:#e9ecef;border-radius:20px;padding:3px 10px;font-size:12px;margin:2px;color:#495057}
.risk-item{padding:6px 0;border-bottom:1px solid #f1f3f4;font-size:14px}
.step-item{padding:6px 0;font-size:14px}
</style>
""", unsafe_allow_html=True)

PROJECT_TYPES = {
    "⚡ Utility-scale IPP":           "utility",
    "🏭 Commercial & Industrial":     "ci",
    "🏘️ Residential / Community":    "residential",
    "🏕️ Remote / Off-grid":          "offgrid",
    "🏛️ Municipal / Public Sector":  "municipal",
    "🌾 Agri-PV / Agrivoltaics":     "agri",
    "🔥 Industrial Process Energy":   "industrial",
    "🚗 EV Charging / Mobility Hub":  "ev",
    "🖥️ Data Center / Tech Campus":  "datacenter",
    "🏙️ Mixed-Use Development":      "mixed",
}

TYPE_CONFIG = {
    "utility":    {"cap":"Target capacity (MWp)","gen":"Target generation (GWh/yr)","area":"Land area (hectares)","budget":"CAPEX budget (USD M)","tariff":"PPA / tariff target (¢/kWh)","kv":True,"desc":"50 MW+ grid-connected power plant, PPA or tariff-based revenue"},
    "ci":         {"cap":"System capacity (kWp)","gen":"Annual generation (MWh/yr)","area":"Roof / land area (m²)","budget":"Budget (USD)","tariff":"Grid tariff / avoided cost (¢/kWh)","kv":False,"desc":"Factory, warehouse, office, mall — behind-the-meter self-consumption"},
    "residential":{"cap":"System capacity (kWp)","gen":"Annual generation (MWh/yr)","area":"Roof area per unit (m²)","budget":"Budget per unit (USD)","tariff":"Grid tariff (¢/kWh)","kv":False,"desc":"Housing developments, villas, community microgrids"},
    "offgrid":    {"cap":"Required capacity (kWp)","gen":"Daily energy need (kWh/day)","area":"Available area (m²)","budget":"Total budget (USD)","tariff":"Diesel avoided cost ($/L)","kv":False,"desc":"Mining camps, telecom towers, rural electrification, islands"},
    "municipal":  {"cap":"System capacity (kWp)","gen":"Annual generation (MWh/yr)","area":"Roof / land area (m²)","budget":"Public budget (USD)","tariff":"Utility tariff (¢/kWh)","kv":False,"desc":"Government buildings, schools, hospitals, streetlighting"},
    "agri":       {"cap":"Solar capacity (MWp)","gen":"Annual generation (GWh/yr)","area":"Agricultural land (hectares)","budget":"Budget (USD M)","tariff":"Energy tariff / PPA (¢/kWh)","kv":False,"desc":"Dual land-use: crops or livestock beneath solar panels"},
    "industrial": {"cap":"Renewable capacity (MWp/MW)","gen":"Annual generation (GWh/yr)","area":"Site area (hectares)","budget":"Budget (USD M)","tariff":"Current energy cost ($/MWh)","kv":True,"desc":"Green hydrogen, desalination, process heat, EAF steelmaking"},
    "ev":         {"cap":"Solar canopy capacity (kWp)","gen":"Daily EV charging need (MWh/day)","area":"Canopy / parking area (m²)","budget":"Budget (USD)","tariff":"Grid / charging tariff (¢/kWh)","kv":False,"desc":"Solar canopy + BESS for fleet charging or public EVSE stations"},
    "datacenter": {"cap":"IT load to power (MW)","gen":"Annual consumption (GWh/yr)","area":"Data center footprint (m²)","budget":"Renewable energy budget (USD M)","tariff":"Current power cost ($/MWh)","kv":True,"desc":"24/7 renewable matching, PUE optimisation, RECs / CFE"},
    "mixed":      {"cap":"Total system capacity (MWp)","gen":"Total generation (GWh/yr)","area":"Master plan area (hectares)","budget":"Energy infrastructure budget (USD M)","tariff":"Blended tariff target (¢/kWh)","kv":False,"desc":"Master-planned community with residential, retail, and commercial loads"},
}

def kpi_card(label, value, unit=""):
    return f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value} <span class="metric-unit">{unit}</span></div></div>'

def section_table(title, rows):
    rows_html = "".join(f"<tr><td style='color:#6c757d;padding:6px 0;font-size:13px;border-bottom:1px solid #f1f3f4;width:52%'>{r[0]}</td><td style='font-weight:600;font-size:13px;padding:6px 0;border-bottom:1px solid #f1f3f4;text-align:right'>{r[1]}</td></tr>" for r in rows)
    return f'<div class="section-card"><p style="font-weight:600;font-size:15px;margin-bottom:12px">{title}</p><table style="width:100%;border-collapse:collapse">{rows_html}</table></div>'

def build_prompt(pt_name, inputs):
    return f"""You are a senior renewable energy engineer and project finance advisor for {pt_name} projects.
Generate a comprehensive technical and financial specification for the parameters below. Be realistic and quantitative.

PARAMETERS:
{json.dumps(inputs, indent=2)}

Respond ONLY with valid JSON. No markdown, no code fences. Schema:
{{
  "recommended_mix": "string",
  "source_badge": "solar or wind or hybrid or hydro",
  "executive_summary": "3-4 sentences tailored to this project type",
  "kpis": [{{"label":"string","value":"string","unit":"string"}}],
  "technical_sections": [{{"title":"string","rows":[["param","value"]]}}],
  "financial_sections": [{{"title":"string","rows":[["param","value"]]}}],
  "sustainability": {{
    "co2_offset_per_year":"string","lifetime_co2_offset":"string",
    "equivalent_context":"string","water_impact":"string",
    "biodiversity_risk":"string","sdg_alignment":["string","string","string"]
  }},
  "key_risks":["string","string","string","string"],
  "mitigations":["string","string","string","string"],
  "permitting":["string","string","string"],
  "next_steps":["string","string","string","string","string"]
}}"""

def call_claude(prompt, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(model="claude-opus-4-5", max_tokens=3000,
                                  messages=[{"role":"user","content":prompt}])
    raw = msg.content[0].text
    return json.loads(raw.replace("```json","").replace("```","").strip())

def render_results(d):
    sus = d.get("sustainability", {})
    bt = d.get("source_badge","solar")
    st.markdown("---")
    st.markdown(f'<span class="badge-{bt}">{d.get("recommended_mix","")}</span>', unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:10px;color:#495057;line-height:1.7'>{d.get('executive_summary','')}</p>", unsafe_allow_html=True)

    st.markdown("#### Key performance indicators")
    kpis = d.get("kpis",[])
    cols = st.columns(4)
    for i,k in enumerate(kpis[:12]):
        with cols[i%4]:
            st.markdown(kpi_card(k.get("label",""),k.get("value",""),k.get("unit","")), unsafe_allow_html=True)

    st.markdown("#### Technical specifications")
    tech = d.get("technical_sections",[])
    if len(tech) >= 2:
        l,r = st.columns(2)
        for i,s in enumerate(tech):
            with (l if i%2==0 else r):
                st.markdown(section_table(s["title"],s.get("rows",[])), unsafe_allow_html=True)
    else:
        for s in tech: st.markdown(section_table(s["title"],s.get("rows",[])), unsafe_allow_html=True)

    st.markdown("#### Financial analysis")
    fins = d.get("financial_sections",[])
    if len(fins) >= 2:
        l,r = st.columns(2)
        for i,s in enumerate(fins):
            with (l if i%2==0 else r):
                st.markdown(section_table(s["title"],s.get("rows",[])), unsafe_allow_html=True)
    else:
        for s in fins: st.markdown(section_table(s["title"],s.get("rows",[])), unsafe_allow_html=True)

    st.markdown("#### Sustainability & environmental impact")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown(section_table("Environmental metrics",[
            ["CO₂ offset per year",sus.get("co2_offset_per_year","—")],
            ["Lifetime CO₂ offset",sus.get("lifetime_co2_offset","—")],
            ["Equivalent impact",sus.get("equivalent_context","—")],
            ["Water impact",sus.get("water_impact","—")],
            ["Biodiversity risk",sus.get("biodiversity_risk","—")],
        ]), unsafe_allow_html=True)
    with c2:
        sdg_html=" ".join(f'<span class="sdg-tag">{s}</span>' for s in sus.get("sdg_alignment",[]))
        st.markdown(f'<div class="section-card"><p style="font-weight:600;font-size:15px;margin-bottom:12px">SDG alignment</p><div style="line-height:2">{sdg_html}</div></div>', unsafe_allow_html=True)

    st.markdown("#### Risks & mitigations")
    rc1,rc2 = st.columns(2)
    with rc1:
        st.markdown("**Key technical risks**")
        for r in d.get("key_risks",[]): st.markdown(f"<div class='risk-item'>• {r}</div>", unsafe_allow_html=True)
    with rc2:
        st.markdown("**Mitigation measures**")
        for m in d.get("mitigations",[]): st.markdown(f"<div class='risk-item'>• {m}</div>", unsafe_allow_html=True)

    st.markdown("#### Permitting & regulatory approvals")
    for p in d.get("permitting",[]): st.markdown(f"<div class='risk-item'>• {p}</div>", unsafe_allow_html=True)

    st.markdown("#### Recommended next steps")
    for i,s in enumerate(d.get("next_steps",[]),1): st.markdown(f"<div class='step-item'><strong>{i}.</strong> {s}</div>", unsafe_allow_html=True)


def main():
    st.title("⚡ Renewable Energy Project Advisor")
    st.caption("Enter your project parameters — the AI will recommend the optimal energy mix and generate full technical and financial specifications.")

    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Anthropic API key", type="password", placeholder="sk-ant-...",
                                 help="Get your key from console.anthropic.com")
        st.caption("Your key is never stored. [Get a key →](https://console.anthropic.com)")
        st.markdown("---")
        st.caption("All outputs are AI-generated estimates for early-stage screening only. Engage a certified engineer before FID.")

    # Step 1
    st.markdown("### Step 1 — Select project type")
    selected_pt = st.selectbox("Project type", list(PROJECT_TYPES.keys()))
    cfg_key = PROJECT_TYPES[selected_pt]
    cfg = TYPE_CONFIG[cfg_key]
    st.caption(cfg["desc"])

    st.markdown("### Step 2 — Project details")

    # Location
    col1,col2,col3 = st.columns(3)
    location = col1.text_input("Country / region *", placeholder="e.g. Saudi Arabia")
    city = col2.text_input("City or coordinates", placeholder="e.g. Riyadh or 24.7°N 46.7°E")
    offtake = col3.selectbox("Offtake / revenue structure", [
        "","PPA (Power Purchase Agreement)","Merchant / spot market",
        "IPP with government tariff","Self-consumption + export",
        "Behind-the-meter (no export)","Captive power","Not yet determined"])

    # Sizing
    st.markdown("**Sizing & site**")
    sc1,sc2,sc3,sc4 = st.columns(4)
    capacity   = sc1.number_input(cfg["cap"], min_value=0.0, value=0.0, format="%.2f")
    generation = sc2.number_input(cfg["gen"], min_value=0.0, value=0.0, format="%.2f")
    area       = sc3.number_input(cfg["area"], min_value=0.0, value=0.0, format="%.2f")
    grid_kv    = sc4.number_input("Grid interconnect voltage (kV)", min_value=0.0, value=0.0, format="%.0f") if cfg["kv"] else None

    # Project-type extras
    extra = {}
    if cfg_key == "ci":
        e1,e2,e3 = st.columns(3)
        extra["peak_demand_kw"]        = e1.number_input("Peak demand (kW)", min_value=0.0, value=0.0)
        extra["daily_consumption_kwh"] = e2.number_input("Daily consumption (kWh/day)", min_value=0.0, value=0.0)
        extra["operating_hours"]       = e3.number_input("Operating hours/day", min_value=0, max_value=24, value=16)
    elif cfg_key == "residential":
        e1,e2,e3 = st.columns(3)
        extra["num_units"]              = e1.number_input("Number of homes / units", min_value=0, value=0)
        extra["daily_demand_per_home"]  = e2.number_input("Daily demand per home (kWh)", min_value=0.0, value=0.0)
        extra["microgrid"]              = e3.selectbox("Community microgrid?", ["","Yes — shared BESS","No — individual systems"])
    elif cfg_key == "offgrid":
        e1,e2,e3 = st.columns(3)
        extra["diesel_gen_kva"]    = e1.number_input("Diesel gen size (kVA)", min_value=0.0, value=0.0)
        extra["diesel_litres_day"] = e2.number_input("Diesel consumption (L/day)", min_value=0.0, value=0.0)
        extra["backup_days"]       = e3.number_input("Required autonomy (days)", min_value=0, value=3)
    elif cfg_key == "municipal":
        e1,e2 = st.columns(2)
        extra["num_buildings"]  = e1.number_input("Number of buildings", min_value=0, value=0)
        extra["facility_type"]  = e2.selectbox("Facility type",["","Government offices","Schools & universities","Hospitals & clinics","Streetlighting","Water / wastewater plant","Mixed municipal"])
    elif cfg_key == "agri":
        e1,e2,e3 = st.columns(3)
        extra["crop_type"]       = e1.text_input("Crop / livestock type", placeholder="e.g. tomatoes, sheep grazing")
        extra["min_clearance_m"] = e2.number_input("Min ground clearance (m)", min_value=0.0, value=2.5)
        extra["irrigation"]      = e3.selectbox("Irrigation water source",["","Groundwater","Surface water","Rainwater / none"])
    elif cfg_key == "industrial":
        e1,e2,e3 = st.columns(3)
        extra["process"]          = e1.selectbox("Industrial process",["","Green hydrogen (electrolysis)","Desalination (RO)","Process heat / steam","EAF steelmaking","Cement / lime","Ammonia / fertiliser","Other"])
        extra["process_load_mw"]  = e2.number_input("Process load (MW)", min_value=0.0, value=0.0)
        extra["load_factor_pct"]  = e3.number_input("Load factor (%)", min_value=0.0, max_value=100.0, value=90.0)
    elif cfg_key == "ev":
        e1,e2,e3 = st.columns(3)
        extra["num_chargers"]  = e1.number_input("Number of chargers", min_value=0, value=0)
        extra["charger_type"]  = e2.selectbox("Charger type",["","AC Level 2 (7–22 kW)","DC Fast Charge (50–150 kW)","Ultra-fast HPC (150–350 kW)","Mixed fleet"])
        extra["use_type"]      = e3.selectbox("Fleet or public?",["","Captive fleet","Public EVSE","Mixed"])
    elif cfg_key == "datacenter":
        e1,e2,e3 = st.columns(3)
        extra["pue"]             = e1.number_input("Current / target PUE", min_value=1.0, value=1.35, format="%.2f")
        extra["matching_target"] = e2.selectbox("Renewable matching",["","Annual (RECs)","Monthly","24/7 CFE"])
        extra["onsite_gen"]      = e3.selectbox("On-site generation?",["","Yes — rooftop + land","Limited rooftop only","No — off-site PPA only"])
    elif cfg_key == "mixed":
        e1,e2,e3,e4 = st.columns(4)
        extra["residential_units"] = e1.number_input("Residential units", min_value=0, value=0)
        extra["retail_gfa_m2"]     = e2.number_input("Retail GFA (m²)", min_value=0.0, value=0.0)
        extra["hotel_rooms"]       = e3.number_input("Hotel rooms", min_value=0, value=0)
        extra["office_gfa_m2"]     = e4.number_input("Office GFA (m²)", min_value=0.0, value=0.0)

    # Climate
    st.markdown("**Climatic resource data**")
    cc1,cc2,cc3,cc4 = st.columns(4)
    psh  = cc1.number_input("Peak sun hours (PSH/day)", min_value=0.0, value=0.0, format="%.1f")
    ghi  = cc2.number_input("GHI (kWh/m²/yr)", min_value=0.0, value=0.0, format="%.0f")
    wind = cc3.number_input("Mean wind speed (m/s)", min_value=0.0, value=0.0, format="%.1f")
    temp = cc4.number_input("Ambient temp avg (°C)", min_value=-50.0, value=25.0, format="%.0f")

    # Financial
    st.markdown("**Financial parameters**")
    fc1,fc2,fc3,fc4 = st.columns(4)
    capex = fc1.number_input(cfg["budget"], min_value=0.0, value=0.0, format="%.2f")
    ppa   = fc2.number_input(cfg["tariff"], min_value=0.0, value=0.0, format="%.2f")
    wacc  = fc3.number_input("Discount rate / WACC (%)", min_value=0.0, value=7.0, format="%.1f")
    life  = fc4.number_input("Project lifetime (years)", min_value=1, max_value=50, value=25)

    # Grid & terrain
    st.markdown("**Grid & site**")
    gc1,gc2 = st.columns(2)
    grid_type = gc1.radio("Grid connection", ["Grid-connected","Hybrid + BESS","Off-grid"], horizontal=True)
    terrain = gc2.selectbox("Terrain / site type",["","Flat desert / semi-arid","Hilly / rolling terrain","Coastal / offshore","Agricultural land","Rooftop (flat)","Rooftop (pitched)","Floating (reservoir / dam)","Brownfield / industrial","Urban / constrained"])

    # Sources & priorities
    st.markdown("**Preferred energy sources** — leave blank for AI to decide")
    preferred = st.multiselect("", ["Solar PV","Onshore wind","Offshore wind","Solar + Wind hybrid","BESS / storage","Hydropower","Green hydrogen","AI decides best mix"], placeholder="Select (optional)")

    st.markdown("**Priorities & sustainability goals**")
    priorities = st.multiselect("", ["Maximize CO₂ offset","Minimize LCOE","Maximize IRR","Minimize land use","Energy security / resilience","Water-scarce optimization","Biodiversity-sensitive site","Local content requirements","Green certification (LEED/BREEAM)","Net-zero roadmap alignment"], placeholder="Select (optional)")

    notes = st.text_area("Additional constraints or notes", placeholder="e.g. COD deadline, planning restrictions, equipment preferences, local content %...", height=80)

    st.markdown("---")
    run = st.button("🔍 Generate full technical report", type="primary", use_container_width=False)

    if run:
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
            return
        if not location:
            st.error("Please enter a project location.")
            return
        if not capacity and not generation and not area:
            st.error("Please provide at least one sizing parameter.")
            return

        inputs = {
            "project_type": selected_pt,
            "location": location,
            "coordinates": city or "estimate from location",
            "offtake": offtake or "not specified",
            "sizing": {cfg["cap"]: capacity or "derive", cfg["gen"]: generation or "derive", cfg["area"]: area or "derive"},
            "grid_kv": grid_kv or "not specified",
            "climate": {"psh": psh or "estimate","ghi": ghi or "estimate","wind_speed_ms": wind or "estimate","ambient_temp_c": temp},
            "financials": {cfg["budget"]: capex or "not specified", cfg["tariff"]: ppa or "not specified","wacc_pct": wacc,"project_life_years": life},
            "grid_type": grid_type,
            "terrain": terrain or "not specified",
            "project_specific": {k:v for k,v in extra.items() if v},
            "preferred_sources": ", ".join(preferred) if preferred else "AI to decide",
            "priorities": ", ".join(priorities) if priorities else "balanced",
            "notes": notes or "none",
        }

        with st.spinner("Analysing parameters and generating specification..."):
            try:
                result = call_claude(build_prompt(selected_pt, inputs), api_key)
                render_results(result)
            except json.JSONDecodeError:
                st.error("Unexpected AI response format. Please try again.")
            except anthropic.AuthenticationError:
                st.error("Invalid API key. Please check your Anthropic API key in the sidebar.")
            except anthropic.RateLimitError:
                st.error("Rate limit reached. Please wait a moment and try again.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
