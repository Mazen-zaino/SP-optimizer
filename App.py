import streamlit as st
import requests
import json
import math
import io
from datetime import datetime

# reportlab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, KeepTogether)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
AED_PER_USD          = 3.6725
UAE_EMISSION_FACTOR  = 0.341   # kg CO₂/kWh — DEWA 2023

UAE_TARIFFS = {
    "DEWA (Dubai)":            {"residential": 0.23, "commercial": 0.38, "industrial": 0.38},
    "SEWA (Sharjah)":          {"residential": 0.21, "commercial": 0.34, "industrial": 0.34},
    "FEWA (Northern Emirates)":{"residential": 0.22, "commercial": 0.36, "industrial": 0.36},
    "ADDC / AADC (Abu Dhabi)": {"residential": 0.21, "commercial": 0.33, "industrial": 0.33},
    "Custom / other":          {"residential": 0.25, "commercial": 0.38, "industrial": 0.38},
}

MODULE_SPECS = {
    "Monocrystalline PERC 440Wp":   {"wp":440,"eff":0.210,"temp_coef":-0.0034,"cost_wp_aed":0.95,"bifacial":False},
    "Monocrystalline TOPCon 580Wp": {"wp":580,"eff":0.223,"temp_coef":-0.0029,"cost_wp_aed":1.10,"bifacial":False},
    "Bifacial TOPCon 600Wp":        {"wp":600,"eff":0.226,"temp_coef":-0.0029,"cost_wp_aed":1.20,"bifacial":True,"bifacial_gain":0.08},
    "HJT (Heterojunction) 650Wp":   {"wp":650,"eff":0.242,"temp_coef":-0.0024,"cost_wp_aed":1.55,"bifacial":True,"bifacial_gain":0.10},
    "CdTe Thin Film 150Wp":         {"wp":150,"eff":0.185,"temp_coef":-0.0032,"cost_wp_aed":0.80,"bifacial":False},
}

MOUNTING_TYPES = {
    "Fixed tilt — ground mount":         {"gcr":0.40,"land_buffer":1.25,"capex_factor":1.00},
    "Single-axis tracker (SAT)":         {"gcr":0.33,"land_buffer":1.30,"capex_factor":1.12},
    "Dual-axis tracker (DAT)":           {"gcr":0.25,"land_buffer":1.35,"capex_factor":1.25},
    "Ballasted rooftop — flat roof":     {"gcr":0.30,"land_buffer":1.15,"capex_factor":1.08},
    "Flush-mounted — pitched roof":      {"gcr":0.85,"land_buffer":1.05,"capex_factor":1.05},
    "Carport / solar canopy":            {"gcr":0.70,"land_buffer":1.10,"capex_factor":1.35},
    "Agri-PV — elevated 3m clearance":  {"gcr":0.20,"land_buffer":1.40,"capex_factor":1.45},
    "Floating PV (reservoir / pond)":    {"gcr":0.60,"land_buffer":1.20,"capex_factor":1.50},
}

INVERTER_TYPES = {
    "String inverter (≤100 kW)":   {"eff":0.975,"cost_f":1.00},
    "Central inverter (100 kW–5 MW)":{"eff":0.980,"cost_f":0.85},
    "Large central (>5 MW)":        {"eff":0.982,"cost_f":0.75},
    "Microinverter (residential)":  {"eff":0.960,"cost_f":1.40},
}

PROJECT_TYPES = {
    "⚡ Utility-scale IPP":           {"ptype":"utility",    "op_h":24,"bess_h":0, "sector":"industrial"},
    "🏭 Commercial & Industrial":     {"ptype":"ci",         "op_h":14,"bess_h":2, "sector":"commercial"},
    "🏘️ Residential / Community":     {"ptype":"residential","op_h":6, "bess_h":4, "sector":"residential"},
    "🏕️ Remote / Off-grid":           {"ptype":"offgrid",    "op_h":20,"bess_h":48,"sector":"commercial"},
    "🏛️ Municipal / Public Sector":   {"ptype":"municipal",  "op_h":12,"bess_h":3, "sector":"commercial"},
    "🌾 Agri-PV / Agrivoltaics":      {"ptype":"agri",       "op_h":14,"bess_h":2, "sector":"commercial"},
    "🔥 Industrial Process Energy":   {"ptype":"industrial", "op_h":20,"bess_h":4, "sector":"industrial"},
    "🚗 EV Charging / Mobility Hub":  {"ptype":"ev",         "op_h":16,"bess_h":4, "sector":"commercial"},
    "🖥️ Data Center / Tech Campus":   {"ptype":"datacenter", "op_h":24,"bess_h":2, "sector":"industrial"},
    "🏙️ Mixed-use Development":       {"ptype":"mixed",      "op_h":16,"bess_h":3, "sector":"commercial"},
}

TRACKER_BOOST = {
    "Fixed tilt — ground mount":0.97, "Single-axis tracker (SAT)":1.17,
    "Dual-axis tracker (DAT)":1.28,   "Ballasted rooftop — flat roof":0.96,
    "Flush-mounted — pitched roof":0.95,"Carport / solar canopy":0.94,
    "Agri-PV — elevated 3m clearance":0.91,"Floating PV (reservoir / pond)":1.03,
}

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="SP Optimizer", page_icon="⚡", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.8rem;padding-bottom:2rem}
.sh{font-size:.71rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;
    color:#888;margin-top:1.4rem;margin-bottom:.35rem}
.badge{display:inline-block;padding:5px 16px;border-radius:20px;
       font-size:.85rem;font-weight:600;margin-bottom:.8rem}
.badge-solar{background:#EAF3DE;color:#3B6D11}
.badge-wind{background:#E6F1FB;color:#185FA5}
.badge-hybrid{background:#EEEDFE;color:#534AB7}
/* Big area card */
.area-hero{background:linear-gradient(135deg,#0F6E56 0%,#1D9E75 100%);
           border-radius:12px;padding:1.5rem 2rem;margin:1rem 0;color:white}
.area-hero h2{color:white;font-size:1.1rem;font-weight:600;margin-bottom:1rem;
              letter-spacing:.04em;text-transform:uppercase}
.area-stat{background:rgba(255,255,255,0.15);border-radius:8px;
           padding:.8rem 1rem;text-align:center}
.area-stat .av{font-size:1.6rem;font-weight:700;color:white;line-height:1.1}
.area-stat .al{font-size:.72rem;color:rgba(255,255,255,.8);
               text-transform:uppercase;letter-spacing:.05em;margin-top:3px}
.area-warn{background:#FFF3CD;border:1px solid #ffc107;border-radius:8px;
           padding:.8rem 1rem;font-size:.84rem;color:#856404;margin-top:.8rem}
table{width:100%;font-size:.82rem;border-collapse:collapse}
td{padding:6px 4px;border-bottom:1px solid #f0f0f0;vertical-align:top}
td:first-child{color:#666;width:58%}
td:last-child{font-weight:600;text-align:right}
tr:last-child td{border-bottom:none}
.bullet{font-size:.84rem;color:#555;padding:3px 0;line-height:1.6}
.src{font-size:.7rem;color:#aaa;font-style:italic;margin-top:.3rem}
.info-banner{background:#fffbe6;border-left:3px solid #f5a623;
             border-radius:4px;padding:.7rem 1rem;font-size:.83rem;
             color:#7a5200;margin-bottom:1rem}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ SP Optimizer")
    st.markdown("---")
    st.success("✅ No API key required — 100% free")
    st.markdown("""
**Data sources:**
- 🛰️ NASA POWER API (22-yr avg)
- 🌍 PVGIS EU JRC (yield check)
- 🗺️ OpenStreetMap (geocoding)
- 🇦🇪 DEWA/SEWA/FEWA tariffs 2024

**Report formats:** PDF download

**Currency:** AED (1 USD = 3.6725 AED)
""")

# ─────────────────────────────────────────────────────────────────────────────
# TITLE
# ─────────────────────────────────────────────────────────────────────────────
st.title("⚡ SP Optimizer — UAE Edition")
st.markdown('<div class="info-banner">🇦🇪 AED pricing · UAE utility tariffs · NASA POWER + PVGIS climate data · PDF report download · No API key needed</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# INPUTS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="sh">Step 1 — Project location & load</p>', unsafe_allow_html=True)
c1,c2,c3 = st.columns([3,1.5,1])
coord_input     = c1.text_input("📍 Location", placeholder="Dubai, UAE  or  25.2048, 55.2708")
connected_power = c2.number_input("⚡ Connected load", min_value=0.0, value=None, placeholder="e.g. 500", format="%.2f")
power_unit      = c3.selectbox("Unit", ["kW","MW","GW"])

st.markdown('<p class="sh">Step 2 — Project type & utility</p>', unsafe_allow_html=True)
c1,c2 = st.columns(2)
project_label = c1.selectbox("Project type", list(PROJECT_TYPES.keys()))
utility       = c2.selectbox("UAE utility provider", list(UAE_TARIFFS.keys()))

st.markdown('<p class="sh">Step 3 — System design</p>', unsafe_allow_html=True)
c1,c2,c3 = st.columns(3)
module_choice   = c1.selectbox("PV module", list(MODULE_SPECS.keys()), index=1)
mounting_choice = c2.selectbox("Mounting system", list(MOUNTING_TYPES.keys()))
inverter_choice = c3.selectbox("Inverter type", list(INVERTER_TYPES.keys()), index=1)

c1,c2,c3,c4 = st.columns(4)
oversizing    = c1.slider("Oversizing factor", 1.00, 1.50, 1.15, 0.05)
tilt_angle    = c2.number_input("Fixed tilt (°)", min_value=0, max_value=45, value=25)
soiling_loss  = c3.slider("Soiling loss (%)", 1.0, 15.0, 4.0, 0.5)
ground_albedo = c4.slider("Ground albedo (%)", 5, 40, 20)

st.markdown('<p class="sh">Step 4 — Site area & space constraint</p>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
space_type = c1.radio("Space type",
    ["Roof area (rooftop solar)", "Land plot (ground mount)", "No constraint — calculate required area"],
    horizontal=True,
    help="Choose what limits your available space.")
azimuth = c2.selectbox("Panel orientation",
    ["South (optimal)","South-East","South-West","East-West (split)"])

# Show area input only when a constraint is selected
available_area = 0.0
setback_pct    = 15
if space_type != "No constraint — calculate required area":
    area_label = "Roof area available (m²)" if "Roof" in space_type else "Land plot area (m²)"
    c1, c2, c3 = st.columns(3)
    available_area = c1.number_input(area_label, min_value=0.0, value=0.0, format="%.0f",
        help="The app will calculate max system capacity and load coverage based on this constraint.")
    setback_pct = c2.slider("Setback / unusable (%)", 0, 40,
        10 if "Roof" in space_type else 15,
        help="Roof: parapets, HVAC, fire breaks typically 10–15%. Ground: roads, fencing, equipment 15–20%.")
    if available_area > 0:
        c3.markdown(f"""
<div style="background:#f0faf4;border:1px solid #9FE1CB;border-radius:8px;padding:.7rem .9rem;margin-top:1.5rem">
<p style="font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:#0F6E56;font-weight:600;margin-bottom:.3rem">Space constraint active</p>
<p style="font-size:.85rem;color:#0F6E56;font-weight:600;margin:0">{int(available_area):,} m² {("roof" if "Roof" in space_type else "plot")} entered</p>
<p style="font-size:.75rem;color:#555;margin:0">Max capacity &amp; coverage % will be shown in results</p>
</div>
""", unsafe_allow_html=True)
else:
    setback_pct = 15

st.markdown('<p class="sh">Step 5 — Financial parameters</p>', unsafe_allow_html=True)
ptype_cfg  = PROJECT_TYPES[project_label]
sector     = ptype_cfg["sector"]
default_t  = UAE_TARIFFS[utility][sector]

c1,c2,c3,c4 = st.columns(4)
custom_tariff = c1.number_input("Tariff (fils/kWh)",
    min_value=0.0, value=float(int(default_t*100)), format="%.0f",
    help=f"Auto-filled from {utility} {sector} rate. 100 fils = 1 AED.")
wacc         = c2.number_input("WACC (%)", min_value=0.0, max_value=30.0, value=7.0, format="%.1f")
lifetime     = c3.number_input("Project lifetime (years)", min_value=5, max_value=40, value=25, format="%d")
degradation  = c4.number_input("Panel degradation (%/yr)", min_value=0.0, max_value=2.0, value=0.50, format="%.2f")

c1,c2,c3,c4 = st.columns(4)
opex_pct    = c1.slider("O&M (% CAPEX/yr)", 0.5, 3.0, 1.0, 0.1)
debt_ratio  = c2.slider("Debt ratio (%)", 0, 80, 60)
debt_rate   = c3.number_input("Debt interest rate (%)", min_value=0.0, max_value=15.0, value=5.5, format="%.1f")
carbon_price= c4.number_input("Carbon price (AED/tonne)", min_value=0.0, value=55.0, format="%.1f")

with st.expander("🔋 BESS options"):
    b1,b2,b3 = st.columns(3)
    bess_override = b1.selectbox("BESS", ["Auto","Force include","No BESS"])
    bess_chem     = b2.selectbox("Chemistry", ["LFP (recommended)","NMC","Lead-Acid"])
    bess_h_custom = b3.number_input("Override hours (0=auto)", min_value=0.0, value=0.0, format="%.0f")

with st.expander("🌬️ Wind & other options"):
    w1,w2,w3 = st.columns(3)
    include_wind  = w1.checkbox("Include wind assessment", value=True)
    net_metering  = w2.checkbox("Net metering available", value=True)
    grid_type     = w3.radio("Grid connection", ["Grid-connected","Hybrid + BESS","Off-grid"], horizontal=True)

st.markdown("")
go = st.button("⚡ Calculate system design & generate report", use_container_width=True, type="primary")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def parse_coords(text):
    parts = text.strip().replace(";",",").split(",")
    if len(parts)==2:
        try:
            la,lo = float(parts[0].strip()), float(parts[1].strip())
            if -90<=la<=90 and -180<=lo<=180: return la,lo
        except: pass
    return None

def geocode(name):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q":name,"format":"json","limit":1},
            headers={"User-Agent":"SPOptimizer/2.0"}, timeout=10)
        d = r.json()
        if d: return float(d[0]["lat"]), float(d[0]["lon"])
    except: pass
    return None

def rev_geocode(lat,lon):
    """Reverse geocode with English language preference to avoid Arabic/non-Latin names."""
    try:
        r = requests.get("https://nominatim.openstreetmap.org/reverse",
            params={"lat":lat,"lon":lon,"format":"json","accept-language":"en"},
            headers={"User-Agent":"SPOptimizer/2.0","Accept-Language":"en"}, timeout=10)
        data = r.json()
        addr = data.get("address",{})
        # Prefer English name fields
        parts=[addr[k] for k in ["suburb","city","town","village","state","country"] if addr.get(k)]
        name = ", ".join(parts[:3]) if parts else ""
        # If still non-Latin (Arabic etc.), fall back to display_name english portion or coords
        if name and any(ord(c) > 1000 for c in name):
            # Try display_name which sometimes has English
            dn = data.get("display_name","")
            latin_parts = [p.strip() for p in dn.split(",") if p.strip() and not any(ord(c)>1000 for c in p)]
            name = ", ".join(latin_parts[-3:]) if latin_parts else f"Site ({lat:.4f}N, {lon:.4f}E)"
        return name if name else f"Site ({lat:.4f}N, {lon:.4f}E)"
    except: return f"Site ({lat:.4f}N, {lon:.4f}E)"

def fetch_nasa(lat, lon):
    """
    Fetch NASA POWER climatology data in two small requests to avoid 422 errors.
    NASA POWER RE community supports max ~8 parameters per call reliably.
    WS80M is excluded — not available in RE community for all regions.
    """
    base = (f"https://power.larc.nasa.gov/api/temporal/climatology/point"
            f"?community=RE&longitude={lon:.6f}&latitude={lat:.6f}&format=JSON")

    # Request 1 — solar parameters
    solar_params = "ALLSKY_SFC_SW_DWN,CLRSKY_SFC_SW_DWN,ALLSKY_KT,T2M,T2M_MAX,T2M_MIN"
    # Request 2 — wind + humidity
    wind_params  = "WS50M,WS10M,RH2M,PRECTOTCORR"

    p = {}
    for params in [solar_params, wind_params]:
        try:
            r = requests.get(f"{base}&parameters={params}", timeout=35)
            if r.status_code == 200:
                p.update(r.json().get("properties", {}).get("parameter", {}))
            else:
                # Try each param individually if batch fails
                for param in params.split(","):
                    try:
                        r2 = requests.get(f"{base}&parameters={param}", timeout=20)
                        if r2.status_code == 200:
                            p.update(r2.json().get("properties", {}).get("parameter", {}))
                    except Exception:
                        pass
        except Exception:
            pass

    if not p:
        return {"error": "NASA POWER returned no data. Please try again in a moment."}

    def g(k):
        return p.get(k, {}).get("ANN")

    ghi_d = g("ALLSKY_SFC_SW_DWN")
    kt    = g("ALLSKY_KT")
    ws50  = g("WS50M")
    ws10  = g("WS10M")
    # Estimate ws80 from ws50 using wind shear power law (α=0.14 for open terrain)
    ws80  = round(ws50 * (80/50)**0.14, 2) if ws50 else None

    # Monthly data — NASA POWER uses 3-letter keys JAN..DEC
    MONTHS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
    DAYS   = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    def gm(param, mon):
        return p.get(param, {}).get(mon)

    monthly = {}
    for i, m in enumerate(MONTHS):
        ghi_m  = gm("ALLSKY_SFC_SW_DWN", m)
        clr_m  = gm("CLRSKY_SFC_SW_DWN", m)
        t_m    = gm("T2M", m)
        tmax_m = gm("T2M_MAX", m)
        ws_m   = gm("WS50M", m)
        kt_m   = gm("ALLSKY_KT", m)
        monthly[m] = {
            "days":       DAYS[i],
            "ghi_daily":  round(ghi_m, 3) if ghi_m else None,
            "ghi_month":  round(ghi_m * DAYS[i], 1) if ghi_m else None,
            "clear_sky":  round(clr_m, 2) if clr_m else None,
            "clearness":  round(kt_m, 3) if kt_m else None,
            "temp_avg":   round(t_m, 1) if t_m else None,
            "temp_max":   round(tmax_m, 1) if tmax_m else None,
            "wind_50m":   round(ws_m, 2) if ws_m else None,
        }

    return {
        "ghi_daily":   round(ghi_d, 3) if ghi_d else None,
        "ghi_annual":  int(ghi_d * 365) if ghi_d else None,
        "psh":         round(ghi_d, 3) if ghi_d else None,
        "clear_sky":   round(g("CLRSKY_SFC_SW_DWN"), 2) if g("CLRSKY_SFC_SW_DWN") else None,
        "clearness":   round(kt, 3) if kt else None,
        "ws50":        round(ws50, 2) if ws50 else None,
        "ws80":        ws80,
        "ws10":        round(ws10, 2) if ws10 else None,
        "temp":        round(g("T2M"), 1) if g("T2M") else None,
        "temp_max":    round(g("T2M_MAX"), 1) if g("T2M_MAX") else None,
        "temp_min":    round(g("T2M_MIN"), 1) if g("T2M_MIN") else None,
        "humidity":    round(g("RH2M"), 1) if g("RH2M") else None,
        "monthly":     monthly,
        "source":      "NASA POWER Climatology API (2001–2022)",
    }

def fetch_pvgis(lat,lon,tilt,az_deg,kwp):
    try:
        r=requests.get("https://re.jrc.ec.europa.eu/api/v5_2/PVcalc",
            params={"lat":lat,"lon":lon,"peakpower":kwp,"loss":14,
                    "angle":tilt,"aspect":az_deg,"outputformat":"json","pvtechchoice":"crystSi"},
            timeout=20)
        if r.status_code==200:
            t=r.json().get("outputs",{}).get("totals",{}).get("fixed",{})
            return {"yield_kwh_yr":round(t["E_y"],0) if t.get("E_y") else None,
                    "irr_kwh_m2_yr":round(t["H(i)_y"],0) if t.get("H(i)_y") else None,
                    "loss_pct":round(t["l_total"],1) if t.get("l_total") else None,
                    "source":"PVGIS 5.2 — EU Joint Research Centre (JRC)"}
    except: pass
    return None

def az_deg(label): return {"South (optimal)":0,"South-East":-45,"South-West":45,"East-West (split)":0}.get(label,0)
def to_kw(v,u): return v*{"kW":1,"MW":1e3,"GW":1e6}[u]
def fmt(n,d=0): 
    if n is None or (isinstance(n,float) and math.isnan(n)): return "—"
    return f"{int(round(n)):,}" if d==0 else f"{round(n,d):,.{d}f}"
def aed_s(n,d=0):
    if n is None: return "—"
    if abs(n)>=1e6: return f"AED {round(n/1e6,2):,.2f}M"
    if abs(n)>=1e3: return f"AED {round(n/1e3,1):,.1f}K"
    return f"AED {round(n,d):,.{d}f}"
def irr_b(cfs):
    def npv(r): return sum(cf/(1+r)**i for i,cf in enumerate(cfs))
    lo,hi=-0.99,5.0
    if npv(lo)*npv(hi)>0: return None
    for _ in range(300):
        mid=(lo+hi)/2
        if npv(mid)>0: lo=mid
        else: hi=mid
        if hi-lo<1e-7: break
    return (lo+hi)/2*100
def npv_c(cfs,cap,w):
    r=w/100
    return sum(cf/(1+r)**(i+1) for i,cf in enumerate(cfs))-cap

# ─────────────────────────────────────────────────────────────────────────────
# CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────
def calculate(connected_kw, ptype_cfg, climate, pvgis_data,
              module_choice, mounting_choice, inverter_choice,
              grid_type, oversizing, tilt, az_label, soiling_pct, albedo_pct,
              tariff_aed, wacc, life, degr, opex_pct, debt_ratio, debt_rate,
              bess_override, bess_chem, bess_h_custom, include_wind,
              carbon_price_aed, net_metering, avail_m2, setback_pct, lat, lon):
    """
    Dual-mode calculator:
    MODE A — Load-constrained (avail_m2 = 0):
        Size system to cover the connected load → calculate area needed.
    MODE B — Area-constrained (avail_m2 > 0):
        Size system to fit the available area → calculate load coverage %.
    """
    mod = MODULE_SPECS[module_choice]
    mnt = MOUNTING_TYPES[mounting_choice]
    inv_eff = INVERTER_TYPES[inverter_choice]["eff"]
    inv_cf  = INVERTER_TYPES[inverter_choice]["cost_f"]
    op_h    = ptype_cfg["op_h"]

    psh   = climate.get("psh", 5.5)
    temp  = climate.get("temp", 28.0)
    tmax  = climate.get("temp_max", 42.0)
    ws50  = climate.get("ws50", 4.5)

    # ── Performance ratio (common to both modes) ───────────────────────────
    cell_temp  = temp + 25
    temp_dera  = 1 + mod["temp_coef"] * (cell_temp - 25)
    temp_dera  = max(0.75, min(1.02, temp_dera))
    bifacial_g = mod.get("bifacial_gain", 0) * (albedo_pct / 20) if mod.get("bifacial") else 0
    az_d = {"South (optimal)":1.00,"South-East":0.95,"South-West":0.95,"East-West (split)":0.89}.get(az_label,1.0)
    pr = (temp_dera * (1-soiling_pct/100) * inv_eff * 0.980 * 0.980 *
          az_d * TRACKER_BOOST.get(mounting_choice,1.0) * (1+bifacial_g))
    pr = round(max(0.60, min(1.05, pr)), 3)

    # ── Source recommendation (common to both modes) ───────────────────────
    sol_score = psh / 6.0; wnd_score = ws50 / 8.0
    if include_wind and wnd_score >= 0.75 and sol_score >= 0.70:
        source = "Solar PV + Wind Hybrid"; badge = "hybrid"; sf = 0.70; wf = 0.30
    elif include_wind and wnd_score > sol_score * 1.2 and wnd_score >= 0.75:
        source = "Onshore Wind"; badge = "wind"; sf = 0.0; wf = 1.0
    else:
        source = "Solar PV"; badge = "solar"; sf = 1.0; wf = 0.0

    # ── Demand ─────────────────────────────────────────────────────────────
    daily_kwh = connected_kw * op_h
    ann_dem   = daily_kwh * 365

    # ── Geometry constants ─────────────────────────────────────────────────
    gcr          = mnt["gcr"]
    m2_per_panel = mod["wp"] / 1000 / mod["eff"]   # m² per panel at STC
    usable_f     = (1 - setback_pct/100) / mnt["land_buffer"]  # usable fraction of site

    # ═══════════════════════════════════════════════════════════════════════
    # MODE B — Area-constrained: derive system from available space
    # ═══════════════════════════════════════════════════════════════════════
    area_mode = "area" if (avail_m2 and avail_m2 > 0) else "load"

    if area_mode == "area":
        # Step 1: work out usable panel area from the site footprint
        usable_site_m2  = avail_m2 * (1 - setback_pct/100)        # remove setbacks
        array_m2_fit    = usable_site_m2 / mnt["land_buffer"]      # remove land buffer
        panel_m2_fit    = array_m2_fit * gcr                       # panel area within array

        # Step 2: max panels and DC capacity that fit
        num_pan_max = int(panel_m2_fit / m2_per_panel)             # floor — no partial panels
        num_pan_max = max(1, num_pan_max)
        act_kwp_max = (num_pan_max * mod["wp"]) / 1000             # kWp solar

        # Step 3: apply solar fraction for hybrid
        act_kwp = act_kwp_max * sf if sf > 0 else act_kwp_max
        num_pan = math.ceil(act_kwp * 1000 / mod["wp"]) if act_kwp > 0 else 0
        act_kwp = (num_pan * mod["wp"]) / 1000

        # Step 4: wind capacity proportional to solar (hybrid only)
        wind_kw = act_kwp_max * wf if wf > 0 else 0

        # Step 5: actual areas for this system
        panel_m2 = num_pan * m2_per_panel
        array_m2 = panel_m2 / gcr if gcr > 0 else panel_m2
        site_m2  = avail_m2   # constrained — system designed to fit this
        site_ha  = site_m2 / 10000
        area_ok  = True        # system is sized TO FIT, always OK
        max_kwp_area = act_kwp_max   # document what fits

        # What load capacity this covers
        load_kwp_needed = (daily_kwh / (psh * pr)) * sf if psh > 0 else connected_kw
        load_covered_pct = min(100.0, act_kwp / load_kwp_needed * 100) if load_kwp_needed > 0 else 100.0

    # ═══════════════════════════════════════════════════════════════════════
    # MODE A — Load-constrained: derive system from demand
    # ═══════════════════════════════════════════════════════════════════════
    else:
        min_kwp = (daily_kwh / (psh * pr)) if psh > 0 else connected_kw * 1.5
        sys_kwp = min_kwp * oversizing * sf
        wind_kw = min_kwp * oversizing * wf if wf > 0 else 0

        num_pan  = math.ceil((sys_kwp * 1000) / mod["wp"]) if sys_kwp > 0 else 0
        act_kwp  = (num_pan * mod["wp"]) / 1000
        panel_m2 = num_pan * m2_per_panel
        array_m2 = panel_m2 / gcr if gcr > 0 else panel_m2
        site_m2  = array_m2 / usable_f if usable_f > 0 else array_m2 * mnt["land_buffer"]
        site_ha  = site_m2 / 10000
        area_ok  = True
        max_kwp_area = None
        load_covered_pct = min(100.0, act_kwp / (sys_kwp if sys_kwp > 0 else act_kwp) * 100)

    # ── Common area metrics ────────────────────────────────────────────────
    site_m2_kwp = site_m2 / act_kwp if act_kwp > 0 else 0
    arr_m2_kwp  = array_m2 / act_kwp if act_kwp > 0 else 0

    # Generation
    # NASA-based yield (always calculated — used as fallback and in area mode)
    ann_solar_nasa = act_kwp * psh * 365 * pr

    # PVGIS is now always fetched with the correct act_kwp (calculate runs first,
    # then PVGIS is fetched, then calculate re-runs). Safe to use in both modes.
    pvgis_used = False
    if pvgis_data and pvgis_data.get("yield_kwh_yr"):
        ann_solar  = pvgis_data["yield_kwh_yr"]
        pvgis_used = True
    else:
        ann_solar  = ann_solar_nasa
    wind_cf=0; ann_wind=0
    if wind_kw>0:
        # Rayleigh distribution wind CF — IEC power curve approximation
        # Extrapolate NASA 50m wind to 100m hub height (wind shear α=0.14)
        v_hub = ws50 * (100/50)**0.14
        vc, vr, vo = 3.5, 12.0, 25.0   # cut-in, rated, cut-out (m/s)
        c_ray = v_hub / 0.8862          # Rayleigh scale param (=vm/Γ(1.5))
        # Time fraction above rated (= full power)
        import math as _m
        p_full = _m.exp(-(vr/c_ray)**2) - _m.exp(-(vo/c_ray)**2)
        # Integrate partial power region (cut-in to rated) numerically
        n_seg, p_partial = 12, 0.0
        dv = (vr - vc) / n_seg
        for _i in range(n_seg):
            vi = vc + (_i + 0.5)*dv
            f_vi = 2*vi/c_ray**2 * _m.exp(-(vi/c_ray)**2)  # Rayleigh pdf
            p_frac = (vi**3 - vc**3)/(vr**3 - vc**3)       # cubic power curve
            p_partial += p_frac * f_vi * dv
        wind_cf = round(min(0.50, max(0.05, p_partial + p_full)), 3)
        ann_wind = wind_kw * wind_cf * 8760
    ann_gen  = ann_solar+ann_wind
    spec_yld = ann_solar/act_kwp if act_kwp>0 else 0
    cap_f    = ann_gen/((act_kwp+wind_kw)*8760)*100 if (act_kwp+wind_kw)>0 else 0
    # Self-sufficiency:
    # - Load mode: how much of annual demand the system covers (can exceed 100% with oversizing)
    # - Area mode: use load_covered_pct (derived from actual kwp vs required kwp)
    if area_mode == "area":
        self_s = load_covered_pct   # already capped at 100
    else:
        self_s = min(100.0, ann_gen/ann_dem*100) if ann_dem>0 else 100.0

    # BESS
    def_bh = ptype_cfg["bess_h"]
    if bess_override=="No BESS": bh=0
    elif bess_override=="Force include": bh=bess_h_custom if bess_h_custom>0 else max(def_bh,2)
    else:
        if grid_type=="Off-grid":       bh = max(def_bh, 48)
        elif grid_type=="Hybrid + BESS":bh = max(def_bh, 4)
        else:                           bh = 0   # Grid-connected → no BESS
    bess_kwh=bess_kw=bess_cap_aed=0
    if bh>0:
        bess_kwh=connected_kw*bh; bess_kw=connected_kw
        cst={"LFP (recommended)":1200,"NMC":1100,"Lead-Acid":600}.get(bess_chem,1200)
        bess_cap_aed=bess_kwh*cst

    # CAPEX (AED)
    cap_mod = act_kwp*1000*mod["cost_wp_aed"]*mnt["capex_factor"]
    cap_inv = act_kwp*1000*0.18*inv_cf*AED_PER_USD
    cap_mnt = act_kwp*1000*0.22*AED_PER_USD*mnt["capex_factor"]
    cap_bos = act_kwp*1000*0.16*AED_PER_USD
    cap_epc = (cap_mod+cap_inv+cap_mnt+cap_bos)*0.10
    cap_con = (cap_mod+cap_inv+cap_mnt+cap_bos+cap_epc)*0.05
    cap_wnd = wind_kw*1000*4.0*AED_PER_USD
    total_cap= cap_mod+cap_inv+cap_mnt+cap_bos+cap_epc+cap_con+cap_wnd+bess_cap_aed
    cap_wp      = total_cap/(act_kwp*1000) if act_kwp>0 else 0
    total_kw    = act_kwp + wind_kw   # combined solar + wind capacity
    cap_kw_tot  = total_cap/total_kw if total_kw>0 else 0   # AED per kW total
    def pct(x): return round(x/total_cap*100,1) if total_cap>0 else 0
    cb={"Modules":pct(cap_mod),"Inverters":pct(cap_inv),"Mounting &amp; civil":pct(cap_mnt),
        "BOS &amp; electrical":pct(cap_bos),"EPC / design":pct(cap_epc),
        "Contingency":pct(cap_con),"BESS":pct(bess_cap_aed),"Wind turbines":pct(cap_wnd)}

    # Financials
    degr_r   = degr/100
    ann_opex = total_cap*(opex_pct/100)
    cfs=[-total_cap]
    for yr in range(1,int(life)+1):
        g_yr=ann_gen*((1-degr_r)**(yr-1))
        cfs.append(g_yr*tariff_aed - ann_opex*(1.025**(yr-1)))
    npv_v = npv_c(cfs[1:],total_cap,wacc)
    irr_v = irr_b(cfs)
    pay   = total_cap/cfs[1] if cfs[1]>0 else 99
    tgl   = sum(ann_gen*((1-degr_r)**yr) for yr in range(int(life)))
    pv_c  = total_cap+npv_c([ann_opex*(1.025**yr) for yr in range(int(life))],0,wacc)
    lcoe  = pv_c/tgl*1000 if tgl>0 else 0
    y1rev = cfs[1]+ann_opex
    eq    = total_cap*(1-debt_ratio/100); dbt=total_cap*(debt_ratio/100)
    r_d=debt_rate/100/12; n_m=int(life)*12
    ann_ds = dbt*(r_d*(1+r_d)**n_m)/((1+r_d)**n_m-1)*12 if dbt>0 and debt_rate>0 else 0
    dscr  = cfs[1]/ann_ds if ann_ds>0 else None
    eq_cfs=[-eq]+[cf-ann_ds for cf in cfs[1:]]
    eq_irr= irr_b(eq_cfs)
    co2_yr = ann_gen*UAE_EMISSION_FACTOR/1000
    co2_lf = co2_yr*life
    co2_rev= co2_yr*carbon_price_aed
    hh     = int(ann_gen/12000)

    # Wind specs
    if wind_kw>0:
        t_kw=3000 if wind_kw>10000 else 1500 if wind_kw>2000 else 500
        n_t=max(1,math.ceil(wind_kw/t_kw))
        h_hub=120 if t_kw>=3000 else 100 if t_kw>=1500 else 65
        r_dt=136 if t_kw>=3000 else 90 if t_kw>=1500 else 54
    else: t_kw=n_t=h_hub=r_dt=0

    return dict(
        source=source,badge=badge,pvgis_used=pvgis_used,
        act_kwp=round(act_kwp,1),wind_kw=round(wind_kw,1),
        num_pan=num_pan,panel_m2=round(panel_m2,1),
        gcr=gcr,array_m2=round(array_m2,1),
        site_m2=round(site_m2,1),site_ha=round(site_ha,3),
        site_m2_kwp=round(site_m2_kwp,1),arr_m2_kwp=round(arr_m2_kwp,1),
        area_mode=area_mode,area_ok=area_ok,max_kwp_area=max_kwp_area,
        load_covered_pct=round(load_covered_pct,1),
        pr=round(pr*100,1),cell_temp=round(cell_temp,1),
        temp_dera=round((1-temp_dera)*100,2),bifacial_g=round(bifacial_g*100,1),
        ann_gen=round(ann_gen,0),ann_gen_mwh=round(ann_gen/1000,1),
        ann_dem=round(ann_dem,0),self_s=round(self_s,1),
        cap_f=round(cap_f,1),spec_yld=round(spec_yld,0),
        daily_kwh=round(daily_kwh,1),op_h=op_h,
        bess_kwh=round(bess_kwh,1),bess_kw=round(bess_kw,1),
        bess_h=round(bess_kwh/bess_kw,1) if bess_kw>0 else 0,
        bess_cap_aed=round(bess_cap_aed,0),
        total_cap=round(total_cap,0),cap_wp=round(cap_wp,2),cap_kw_tot=round(cap_kw_tot,0),
        ann_opex=round(ann_opex,0),lcoe=round(lcoe,1),
        tariff_aed=tariff_aed,y1rev=round(y1rev,0),
        y1net=round(cfs[1],0),npv=round(npv_v,0),
        irr=round(irr_v,1) if irr_v else None,
        eq_irr=round(eq_irr,1) if eq_irr else None,
        payback=round(pay,1),wacc=wacc,life=int(life),
        dscr=round(dscr,2) if dscr else None,
        eq_aed=round(eq,0),dbt_aed=round(dbt,0),ann_ds=round(ann_ds,0),
        debt_ratio=debt_ratio,debt_rate=debt_rate,cb=cb,
        co2_yr=round(co2_yr,1),co2_lf=round(co2_lf,0),
        co2_rev=round(co2_rev,0),hh=hh,
        t_kw=t_kw,n_t=n_t,h_hub=h_hub,r_dt=r_dt,
        wind_cf=round(wind_cf*100,1),ann_wind_mwh=round(ann_wind/1000,1),
        degr=degr,net_metering=net_metering,
    )

# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
MONTH_KEYS  = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]

def calc_monthly(climate, act_kwp, pr, degr_pct):
    """
    Calculate monthly generation, peak sun hours, capacity factor, and temp derating.
    Uses NASA POWER monthly GHI data and the system PR.
    Returns list of 12 dicts.
    """
    rows = []
    monthly = climate.get("monthly", {})
    base_temp_coef = -0.0029  # TOPCon default

    for i, mk in enumerate(MONTH_KEYS):
        m = monthly.get(mk, {})
        ghi_d = m.get("ghi_daily") or climate.get("psh", 5.5)
        days  = m.get("days", 30)
        temp  = m.get("temp_avg") or climate.get("temp", 28)
        tmax  = m.get("temp_max") or temp + 12

        # Monthly cell temp (use avg + NOCT offset)
        cell_temp = temp + 25
        t_dera    = 1 + base_temp_coef * (cell_temp - 25)
        t_dera    = max(0.75, min(1.02, t_dera))

        # Monthly PR (temperature varies month to month)
        monthly_pr = pr / 100 * t_dera / (1 + base_temp_coef * (climate.get("temp", 28) + 25 - 25))
        monthly_pr = min(1.0, monthly_pr)

        gen_kwh = act_kwp * ghi_d * days * monthly_pr
        cf      = gen_kwh / (act_kwp * days * 24) * 100 if act_kwp > 0 else 0

        rows.append({
            "month":     MONTH_NAMES[i],
            "days":      days,
            "ghi_daily": round(ghi_d, 2),
            "ghi_total": round(ghi_d * days, 1),
            "temp_avg":  temp,
            "temp_max":  tmax,
            "cell_temp": round(cell_temp, 1),
            "t_dera_pct":round((1 - t_dera) * 100, 1),
            "wind_50m":  m.get("wind_50m") or climate.get("ws50", 4.5),
            "clearness": m.get("clearness") or climate.get("clearness", 0.62),
            "gen_mwh":   round(gen_kwh / 1000, 1),
            "cf_pct":    round(cf, 1),
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# APPLIANCE DATABASE — watts, daily hours by context
# Source: UAE DEWA energy guidelines, IEC typical values
# ─────────────────────────────────────────────────────────────────────────────
APPLIANCES = {
    "Home": [
        {"name": "Split AC (1.5 ton)",       "watts": 1500, "hours": 8,  "icon": "❄️"},
        {"name": "Split AC (2.5 ton)",        "watts": 2500, "hours": 8,  "icon": "❄️"},
        {"name": "Refrigerator",              "watts": 150,  "hours": 24, "icon": "🧊"},
        {"name": "Washing machine",           "watts": 500,  "hours": 1,  "icon": "🫧"},
        {"name": "Clothes dryer",             "watts": 3000, "hours": 1,  "icon": "💨"},
        {"name": "Dishwasher",                "watts": 1200, "hours": 1,  "icon": "🍽️"},
        {"name": "Electric oven",             "watts": 2000, "hours": 1,  "icon": "🍳"},
        {"name": "Microwave",                 "watts": 1000, "hours": 0.5,"icon": "📡"},
        {"name": "Water heater (electric)",   "watts": 3000, "hours": 2,  "icon": "🚿"},
        {"name": "LED TV (55 inch)",             "watts": 80,   "hours": 5,  "icon": "📺"},
        {"name": "LED lighting (whole home)", "watts": 200,  "hours": 6,  "icon": "💡"},
        {"name": "Laptop / computer",         "watts": 100,  "hours": 8,  "icon": "💻"},
        {"name": "Pool pump",                 "watts": 750,  "hours": 6,  "icon": "🏊"},
        {"name": "Electric vehicle charger",  "watts": 7000, "hours": 4,  "icon": "🚗"},
        {"name": "Water pump (villa)",        "watts": 500,  "hours": 3,  "icon": "💧"},
    ],
    "Office": [
        {"name": "Central HVAC (per 100m²)",  "watts": 3500, "hours": 10, "icon": "❄️"},
        {"name": "Desktop computer + monitor","watts": 200,  "hours": 9,  "icon": "🖥️"},
        {"name": "Laptop",                    "watts": 65,   "hours": 9,  "icon": "💻"},
        {"name": "LED office lighting (100m²)","watts": 400, "hours": 10, "icon": "💡"},
        {"name": "Printer (laser, A4)",       "watts": 400,  "hours": 2,  "icon": "🖨️"},
        {"name": "Server rack (2U)",          "watts": 500,  "hours": 24, "icon": "🗄️"},
        {"name": "Elevator (8-person)",       "watts": 5500, "hours": 4,  "icon": "🛗"},
        {"name": "Projector / display",       "watts": 350,  "hours": 4,  "icon": "📽️"},
        {"name": "Coffee machine",            "watts": 1200, "hours": 2,  "icon": "☕"},
        {"name": "Water cooler / dispenser",  "watts": 100,  "hours": 24, "icon": "💧"},
        {"name": "CCTV system (8 cameras)",   "watts": 80,   "hours": 24, "icon": "📷"},
        {"name": "Access control / alarms",   "watts": 50,   "hours": 24, "icon": "🔒"},
        {"name": "Refrigerator (office)",     "watts": 150,  "hours": 24, "icon": "🧊"},
        {"name": "EV charging station (22kW)","watts": 22000,"hours": 4,  "icon": "🔌"},
        {"name": "UPS system (10 kVA)",       "watts": 500,  "hours": 24, "icon": "⚡"},
    ],
    "Industrial": [
        {"name": "Air compressor (10 HP)",    "watts": 7500, "hours": 8,  "icon": "🔧"},
        {"name": "Air compressor (50 HP)",    "watts": 37000,"hours": 8,  "icon": "🔧"},
        {"name": "Centrifugal pump (7.5 kW)", "watts": 7500, "hours": 16, "icon": "💧"},
        {"name": "Conveyor motor (5 kW)",     "watts": 5000, "hours": 10, "icon": "⚙️"},
        {"name": "CNC machine",               "watts": 10000,"hours": 8,  "icon": "🏭"},
        {"name": "Welding machine",           "watts": 8000, "hours": 6,  "icon": "🔥"},
        {"name": "Industrial chiller (20 ton)","watts":25000,"hours": 12, "icon": "❄️"},
        {"name": "Warehouse lighting (1000m²)","watts":2000, "hours": 12, "icon": "💡"},
        {"name": "Forklift charger",          "watts": 3000, "hours": 8,  "icon": "🚜"},
        {"name": "Dust extraction system",    "watts": 4000, "hours": 8,  "icon": "💨"},
        {"name": "Water treatment pump",      "watts": 5500, "hours": 20, "icon": "💧"},
        {"name": "Industrial oven (electric)","watts":15000, "hours": 6,  "icon": "🔥"},
        {"name": "Injection moulding machine","watts":20000, "hours": 8,  "icon": "🏭"},
        {"name": "Office / welfare block AC", "watts": 5000, "hours": 10, "icon": "❄️"},
        {"name": "Security / CCTV / access",  "watts": 500,  "hours": 24, "icon": "📷"},
    ],
}

def calc_appliance_runs(daily_gen_kwh, context):
    """
    Given daily generation in kWh and a context (Home/Office/Industrial),
    calculate how many of each appliance can run per day.
    Returns list of dicts sorted by daily consumption desc.
    """
    appliances = APPLIANCES.get(context, [])
    results = []
    for a in appliances:
        daily_kwh_each = a["watts"] * a["hours"] / 1000
        qty = int(daily_gen_kwh // daily_kwh_each) if daily_kwh_each > 0 else 0
        results.append({
            "icon":      a["icon"],
            "name":      a["name"],
            "watts":     a["watts"],
            "hours":     a["hours"],
            "daily_kwh": round(daily_kwh_each, 2),
            "qty":       qty,
        })
    return sorted(results, key=lambda x: x["daily_kwh"], reverse=True)


def safe_pdf_text(text):
    """
    Make text safe for ReportLab PDF rendering.
    Handles Arabic / RTL text using arabic-reshaper + python-bidi if available.
    Falls back to coordinate-style label if libraries are missing.
    """
    if not text:
        return text
    # Check if text contains Arabic/RTL characters (Unicode range 0x0600-0x06FF)
    has_arabic = any(0x0600 <= ord(c) <= 0x06FF for c in text)
    if not has_arabic:
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        # Libraries not installed — strip Arabic, keep any Latin parts
        latin = " ".join(p.strip() for p in text.split() if not any(0x0600<=ord(c)<=0x06FF for c in p))
        return latin.strip() if latin.strip() else text


def generate_pdf(r, climate, pvgis_data, location_name, lat, lon,
                 connected_power, power_unit, project_label, utility,
                 module_choice, mounting_choice, inverter_choice, soiling_loss,
                 tilt_angle, azimuth, ground_albedo, setback_pct, avail_m2,
                 custom_tariff, wacc, lifetime, degradation, opex_pct,
                 debt_ratio, debt_rate, carbon_price, bess_chem, net_metering):

    buf = io.BytesIO()

    # Register DejaVu fonts for full Unicode / Arabic support
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.registerFont(TTFont('DejaVu',     '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuBold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        BODY_FONT  = 'DejaVu'
        BOLD_FONT  = 'DejaVuBold'
    except Exception:
        BODY_FONT  = 'Helvetica'
        BOLD_FONT  = 'Helvetica-Bold'


    # Page width: A4 = 595pt, margins 2cm each side (56.7pt each) → usable = ~481pt
    PAGE_W = A4[0]
    L_MARGIN = R_MARGIN = 2 * cm
    W = PAGE_W - L_MARGIN - R_MARGIN   # ~481 pt — NEVER use fractions of this in nested tables

    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=2.2*cm, bottomMargin=2*cm)

    # ── Colours ───────────────────────────────────────────────────────────────
    G_DARK  = colors.HexColor("#0F6E56")
    G_MID   = colors.HexColor("#1D9E75")
    G_LIGHT = colors.HexColor("#E1F5EE")
    G_PALE  = colors.HexColor("#F0FAF6")
    AMBER   = colors.HexColor("#F5A623")
    GR_LT   = colors.HexColor("#F8F9FA")
    GR_MD   = colors.HexColor("#DEE2E6")
    BLACK   = colors.HexColor("#212529")
    GRAY6   = colors.HexColor("#666666")
    WHITE   = colors.white

    # ── Styles ────────────────────────────────────────────────────────────────
    ss = getSampleStyleSheet()
    def ps(nm, **kw):
        return ParagraphStyle(nm, parent=ss["Normal"], **kw)

    S_title  = ps("Tt", fontSize=18, fontName=BOLD_FONT, textColor=WHITE, leading=22)
    S_sub    = ps("Sb", fontSize=10, fontName=BODY_FONT,      textColor=WHITE, leading=14)
    S_h2     = ps("H2", fontSize=11, fontName=BOLD_FONT, textColor=G_DARK, spaceAfter=3)
    S_body   = ps("Bd", fontSize=9,  fontName=BODY_FONT,      textColor=BLACK,  leading=13)
    S_lbl    = ps("Lb", fontSize=8.5,fontName=BODY_FONT,      textColor=GRAY6)
    S_val    = ps("Vl", fontSize=8.5,fontName=BOLD_FONT, textColor=BLACK,  alignment=TA_RIGHT)
    S_note   = ps("Nt", fontSize=7.5,fontName="Helvetica-Oblique", textColor=colors.HexColor("#888888"), leading=11)
    S_footer = ps("Ft", fontSize=7,  fontName="Helvetica-Oblique", textColor=colors.HexColor("#aaaaaa"))
    S_white  = ps("Wh", fontSize=8.5,fontName=BOLD_FONT, textColor=WHITE,  alignment=TA_CENTER)

    now = datetime.now().strftime("%d %B %Y")

    # ── Reusable table style builders ─────────────────────────────────────────
    def ts_header():
        """Green header, alternating rows, grid."""
        return TableStyle([
            ("BACKGROUND",  (0,0),(-1,0), G_DARK),
            ("TEXTCOLOR",   (0,0),(-1,0), WHITE),
            ("FONTNAME",    (0,0),(-1,0), BOLD_FONT),
            ("FONTSIZE",    (0,0),(-1,0), 8.5),
            ("FONTNAME",    (0,1),(-1,-1),BODY_FONT),
            ("FONTSIZE",    (0,1),(-1,-1), 8.5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GR_LT]),
            ("GRID",        (0,0),(-1,-1), 0.3, GR_MD),
            ("TOPPADDING",  (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("LEFTPADDING", (0,0),(-1,-1), 6),
            ("RIGHTPADDING",(0,0),(-1,-1), 6),
            ("VALIGN",      (0,0),(-1,-1),"MIDDLE"),
        ])

    def ts_section_header():
        """Lighter green section header (for 2-col label/value tables)."""
        return TableStyle([
            ("BACKGROUND",  (0,0),(-1,0), G_MID),
            ("TEXTCOLOR",   (0,0),(-1,0), WHITE),
            ("FONTNAME",    (0,0),(-1,0), BOLD_FONT),
            ("FONTSIZE",    (0,0),(-1,0), 8.5),
            ("SPAN",        (0,0),(-1,0)),
            ("ALIGN",       (0,0),(-1,0),"CENTER"),
            ("FONTNAME",    (0,1),(-1,-1),BODY_FONT),
            ("FONTSIZE",    (0,1),(-1,-1), 8.5),
            ("FONTNAME",    (1,1),(1,-1),  BOLD_FONT),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GR_LT]),
            ("GRID",        (0,0),(-1,-1), 0.3, GR_MD),
            ("TOPPADDING",  (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("LEFTPADDING", (0,0),(-1,-1), 6),
            ("RIGHTPADDING",(0,0),(-1,-1), 6),
            ("VALIGN",      (0,0),(-1,-1),"MIDDLE"),
        ])

    def kv_tbl(title, rows, c1=None, c2=None):
        """Simple 2-col label/value table with a section header row. Full width."""
        c1 = c1 or W * 0.56
        c2 = c2 or W * 0.44
        data = [[Paragraph(title, S_white), ""]] + \
               [[Paragraph(str(k), S_lbl), Paragraph(str(v), S_val)] for k,v in rows]
        t = Table(data, colWidths=[c1, c2])
        t.setStyle(ts_section_header())
        return t

    def section_bar(title):
        """Full-width dark green section divider bar."""
        t = Table([[Paragraph(title, ps("SB2", fontSize=10, fontName=BOLD_FONT,
                                        textColor=WHITE))]],
                  colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), G_DARK),
            ("TOPPADDING", (0,0),(-1,-1), 7),
            ("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("LEFTPADDING",(0,0),(-1,-1), 10),
        ]))
        return t

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # COVER BANNER
    # ══════════════════════════════════════════════════════════════════════════
    # Title bar — single full-width table, safe
    title_tbl = Table(
        [[Paragraph("SP Optimizer", S_title)],
         [Paragraph("Renewable Energy System Design Report — UAE Edition", S_sub)]],
        colWidths=[W])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), G_DARK),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 4))

    # Meta strip — 3 equally wide columns, safe
    col3 = W / 3
    meta_tbl = Table([[
        Paragraph(f"<b>Location:</b> {safe_pdf_text(location_name)}", S_lbl),
        Paragraph(f"<b>Date:</b> {now}", S_lbl),
        Paragraph(f"<b>Utility:</b> {utility}", S_lbl),
    ]], colWidths=[col3, col3, col3])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), G_LIGHT),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.3, GR_MD),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 8))

    # Recommended source badge
    badge_col = {"solar": G_MID, "wind": colors.HexColor("#185FA5"),
                 "hybrid": colors.HexColor("#534AB7")}.get(r["badge"], G_MID)
    rec_tbl = Table([[Paragraph(f"Recommended system: {r['source']}",
                                ps("RC", fontSize=11, fontName=BOLD_FONT, textColor=WHITE))]],
                    colWidths=[W])
    rec_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), badge_col),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    story.append(rec_tbl)
    story.append(Spacer(1, 6))

    # Executive summary
    story.append(Paragraph(
        f"Based on NASA POWER climate data ({climate.get('psh','—')} kWh/m²/day GHI, "
        f"{climate.get('ws50','—')} m/s wind at 50m), {r['source']} is the optimal system for "
        f"{safe_pdf_text(location_name)}. The {fmt(r['act_kwp'],1)} kWp system generates {fmt(r['ann_gen_mwh'],1)} MWh/yr, "
        f"covering {r['self_s']}% of the {fmt(r['daily_kwh'],1)} kWh/day demand at a performance ratio of "
        f"{r['pr']}%. At {int(r['tariff_aed']*100)} fils/kWh ({utility}), "
        f"the project achieves a {r['payback']}-year simple payback and {r['irr']}% IRR over {r['life']} years.",
        S_body))
    story.append(Spacer(1, 10))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1: REQUIRED SITE AREA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_bar("SECTION 1 — REQUIRED SITE AREA FOR IMPLEMENTATION"))
    story.append(Spacer(1, 5))

    # Big area highlight row — 5 equal columns
    col5 = W / 5
    area_highlight = Table(
        [[Paragraph(f"{fmt(r['panel_m2'],0)} m²",   ps("AV1",fontSize=16,fontName=BOLD_FONT,textColor=WHITE,alignment=TA_CENTER)),
          Paragraph(f"{fmt(r['array_m2'],0)} m²",   ps("AV2",fontSize=16,fontName=BOLD_FONT,textColor=WHITE,alignment=TA_CENTER)),
          Paragraph(f"{fmt(r['site_m2'],0)} m²",    ps("AV3",fontSize=18,fontName=BOLD_FONT,textColor=WHITE,alignment=TA_CENTER)),
          Paragraph(f"{fmt(r['site_ha'],3)} ha",     ps("AV4",fontSize=16,fontName=BOLD_FONT,textColor=WHITE,alignment=TA_CENTER)),
          Paragraph(f"{fmt(r['site_m2_kwp'],1)} m²/kWp",ps("AV5",fontSize=14,fontName=BOLD_FONT,textColor=WHITE,alignment=TA_CENTER)),
         ],
         [Paragraph("Panel active area",   ps("AL1",fontSize=7.5,textColor=G_LIGHT,alignment=TA_CENTER)),
          Paragraph("Array footprint",     ps("AL2",fontSize=7.5,textColor=G_LIGHT,alignment=TA_CENTER)),
          Paragraph("TOTAL SITE REQUIRED", ps("AL3",fontSize=7.5,fontName=BOLD_FONT,textColor=AMBER,alignment=TA_CENTER)),
          Paragraph("In hectares",         ps("AL4",fontSize=7.5,textColor=G_LIGHT,alignment=TA_CENTER)),
          Paragraph("Area per kWp",        ps("AL5",fontSize=7.5,textColor=G_LIGHT,alignment=TA_CENTER)),
         ]],
        colWidths=[col5, col5, col5, col5, col5])
    area_highlight.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), G_DARK),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("LINEAFTER",     (0,0),(3,1),   0.5, colors.HexColor("#1D9E75")),
        ("BACKGROUND",    (2,0),(2,1),   colors.HexColor("#085041")),  # highlight total
    ]))
    story.append(area_highlight)
    story.append(Spacer(1, 6))

    # Area breakdown table
    if r["area_mode"] == "area":
        area_title_row = ["AREA-CONSTRAINED DESIGN — system sized to fit available space","",""]
        avail_note = f"Input: {fmt(avail_m2,0)} m²"
    else:
        area_title_row = ["LOAD-CONSTRAINED DESIGN — area calculated to cover full load","",""]
        avail_note = "Calculated from load demand"

    area_rows = [
        ["Parameter", "Value", "Explanation"],
        [area_title_row[0], "", ""],
        ["Calculation mode",             "Area → System" if r["area_mode"]=="area" else "Load → Area",
                                         avail_note],
        ["PV module active area",        f"{fmt(r['panel_m2'],1)} m²",
                                         f"{fmt(r['num_pan'])} panels x {round(r['panel_m2']/r['num_pan'] if r['num_pan'] else 0,2)} m² each"],
        ["Ground cover ratio (GCR)",     f"{r['gcr']}",
                                         f"{int(r['gcr']*100)}% of ground covered — {mounting_choice.split('—')[0].strip()}"],
        ["Array footprint (panel/GCR)",  f"{fmt(r['array_m2'],1)} m²",  "Minimum ground area for the panel array"],
        ["Land buffer factor",           f"{MOUNTING_TYPES[mounting_choice]['land_buffer']}x",
                                         "Roads, inverter pads, fencing, fire clearance"],
        ["Site setback / unusable",      f"{setback_pct}%",             "Excluded from usable site area"],
        ["TOTAL SITE AREA",              f"{fmt(r['site_m2'],0)} m²",
                                         "Available site" if r["area_mode"]=="area" else "Required to cover full load"],
        ["In hectares",                  f"{fmt(r['site_ha'],3)} ha",    "1 hectare = 10,000 m²"],
        ["Array area per kWp",           f"{fmt(r['arr_m2_kwp'],1)} m²/kWp", "Array footprint per kWp installed"],
        ["Total site per kWp",           f"{fmt(r['site_m2_kwp'],1)} m²/kWp", "Total site per kWp installed"],
        ["LOAD COVERAGE",                f"{r['load_covered_pct']}%",
                                         "Full load covered" if r['load_covered_pct']>=95 else f"{round(100-r['load_covered_pct'],1)}% from grid / other source"],
    ]
    if avail_m2 and avail_m2 > 0 and r["area_mode"]=="area" and r["max_kwp_area"]:
        area_rows.append(["Max solar capacity in area",  f"{fmt(r['max_kwp_area'],0)} kWp",
                           "Based on GCR and setbacks"])

    at = Table(area_rows, colWidths=[W*0.38, W*0.22, W*0.40])
    at.setStyle(ts_header())
    # Highlight the "TOTAL SITE AREA" row (row index 6)
    at.setStyle(TableStyle(list(ts_header()._cmds) + [
        ("BACKGROUND",  (0,6),(-1,6), G_PALE),
        ("FONTNAME",    (0,6),(-1,6), BOLD_FONT),
        ("BACKGROUND",  (0,7),(-1,7), G_PALE),
        ("FONTNAME",    (0,7),(-1,7), BOLD_FONT),
    ]))
    story.append(at)
    story.append(Spacer(1, 4))
    mode_txt = ("Area-constrained mode: system sized to fit available space" if r["area_mode"]=="area"
                else "Load-constrained mode: area calculated to cover full load demand")
    story.append(Paragraph(
        f"Mode: {mode_txt}   |   "
        f"Mounting: {mounting_choice}   |   Module: {module_choice}   |   "
        f"GCR: {r['gcr']}   |   Setback: {setback_pct}%   |   "
        f"Load coverage: {r['load_covered_pct']}%", S_note))

    # Space constraint summary if applicable
    if avail_m2 and avail_m2 > 0 and not r["area_ok"] and r["max_kwp_area"]:
        max_kw   = r["max_kwp_area"]
        max_gen  = max_kw * r["spec_yld"] / 1000
        coverage = min(100.0, max_gen * 1000 / r["ann_dem"] * 100) if r["ann_dem"] > 0 else 0
        story.append(Spacer(1, 6))
        sc_data = [
            ["SPACE CONSTRAINT ANALYSIS", "", "", ""],
            ["Maximum capacity in available space", f"{fmt(max_kw,0)} kWp",
             "Annual generation (space-limited)", f"{fmt(max_gen,1)} MWh/yr"],
            ["Load coverage achievable", f"{round(coverage,1)}%",
             "Uncovered load", f"{round(100-coverage,1)}%"],
        ]
        sc_tbl = Table(sc_data, colWidths=[W*0.35, W*0.15, W*0.35, W*0.15])
        sc_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), AMBER),
            ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
            ("FONTNAME",      (0,0),(-1,0), BOLD_FONT),
            ("FONTSIZE",      (0,0),(-1,0), 8.5),
            ("SPAN",          (0,0),(-1,0)),
            ("ALIGN",         (0,0),(-1,0), "CENTER"),
            ("FONTNAME",      (0,1),(-1,-1), BODY_FONT),
            ("FONTSIZE",      (0,1),(-1,-1), 8.5),
            ("FONTNAME",      (1,1),(1,-1),  BOLD_FONT),
            ("FONTNAME",      (3,1),(3,-1),  BOLD_FONT),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GR_LT]),
            ("GRID",          (0,0),(-1,-1), 0.3, GR_MD),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ]))
        story.append(sc_tbl)
    story.append(Spacer(1, 12))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2: KPI SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_bar("SECTION 2 — KEY PERFORMANCE INDICATORS"))
    story.append(Spacer(1, 5))

    kpi_data = [
        ["Indicator",           "Value",                             "Indicator",          "Value"],
        ["Renewable capacity",  f"{fmt(r['act_kwp'],1)} kWp",        "Self-sufficiency",   f"{r['self_s']}%"],
        ["Annual generation",   f"{fmt(r['ann_gen_mwh'],1)} MWh/yr", "Capacity factor",    f"{r['cap_f']}%"],
        ["Specific yield",      f"{fmt(r['spec_yld'],0)} kWh/kWp/yr","Performance ratio",  f"{r['pr']}%"],
        ["Total CAPEX",         aed_s(r['total_cap']),
         "CAPEX per kW (total)" if r['wind_kw']>0 else "CAPEX per Wp",
         f"AED {fmt(r['cap_kw_tot'],0)}/kW" if r['wind_kw']>0 else f"AED {r['cap_wp']:.2f}/Wp"],
        ["LCOE",                f"AED {r['lcoe']:.0f}/MWh",          "Tariff (avoided)",   f"{int(r['tariff_aed']*100)} fils/kWh"],
        ["Simple payback",      f"{r['payback']} years",             "Project IRR",        f"{r['irr']}%" if r['irr'] else "—"],
        [f"NPV ({r['life']} yr)", aed_s(r['npv']),                   "Equity IRR",         f"{r['eq_irr']}%" if r['eq_irr'] else "—"],
        ["CO2 offset/year",     f"{fmt(r['co2_yr'],1)} tonnes/yr",   "Households powered", fmt(r['hh'])],
        ["Total site required", f"{fmt(r['site_m2'],0)} m²",         "Panels required",    fmt(r['num_pan'])],
    ]
    col4 = [W*0.30, W*0.20, W*0.30, W*0.20]
    kpi_tbl = Table(kpi_data, colWidths=col4)
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  G_DARK),
        ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
        ("FONTNAME",      (0,0),(-1,0),  BOLD_FONT),
        ("FONTSIZE",      (0,0),(-1,0),  8.5),
        ("FONTNAME",      (0,1),(-1,-1), BODY_FONT),
        ("FONTSIZE",      (0,1),(-1,-1), 8.5),
        ("FONTNAME",      (1,1),(1,-1),  BOLD_FONT),
        ("FONTNAME",      (3,1),(3,-1),  BOLD_FONT),
        ("BACKGROUND",    (2,1),(-1,-1), GR_LT),
        ("ROWBACKGROUNDS",(0,1),(1,-1),  [WHITE, colors.HexColor("#F5FBF8")]),
        ("GRID",          (0,0),(-1,-1), 0.3, GR_MD),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 12))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3: CLIMATE DATA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_bar("SECTION 3 — CLIMATE &amp; SOLAR RESOURCE DATA"))
    story.append(Spacer(1, 5))
    src_txt = "NASA POWER Climatology API (2001–2022, 22-year average)"
    if pvgis_data and pvgis_data.get("yield_kwh_yr"):
        src_txt += "   |   PVGIS 5.2 EU Joint Research Centre (yield cross-check)"
    story.append(Paragraph(f"Sources: {src_txt}", S_note))
    story.append(Spacer(1, 4))

    clim_data = [
        ["Parameter",            "Value",                          "Parameter",          "Value"],
        ["Location",             safe_pdf_text(location_name),                    "Coordinates",        f"{lat:.4f}N, {lon:.4f}E"],
        ["Daily GHI (PSH)",      f"{climate.get('psh','—')} kWh/m2/day", "Annual GHI", f"{climate.get('ghi_annual','—')} kWh/m2/yr"],
        ["Clear-sky GHI",        f"{climate.get('clear_sky','—')} kWh/m2/day","Clearness index (Kt)", str(climate.get('clearness','—'))],
        ["Wind speed @ 50m",     f"{climate.get('ws50','—')} m/s","Wind speed @ 10m",   f"{climate.get('ws10','—')} m/s"],
        ["Avg temperature",      f"{climate.get('temp','—')} C",   "Max temperature",   f"{climate.get('temp_max','—')} C"],
        ["Min temperature",      f"{climate.get('temp_min','—')} C","Avg humidity",      f"{climate.get('humidity','—')} %"],
        ["PVGIS yield check",    f"{fmt(pvgis_data['yield_kwh_yr'],0)} kWh/yr" if pvgis_data and pvgis_data.get("yield_kwh_yr") else "Not available",
         "PVGIS total losses",   f"{pvgis_data.get('loss_pct','—')}%" if pvgis_data else "—"],
    ]
    clim_tbl = Table(clim_data, colWidths=col4)
    clim_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  G_DARK),
        ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
        ("FONTNAME",      (0,0),(-1,0),  BOLD_FONT),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("FONTNAME",      (0,1),(-1,-1), BODY_FONT),
        ("FONTNAME",      (1,1),(1,-1),  BOLD_FONT),
        ("FONTNAME",      (3,1),(3,-1),  BOLD_FONT),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GR_LT]),
        ("GRID",          (0,0),(-1,-1), 0.3, GR_MD),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
    ]))
    story.append(clim_tbl)
    story.append(Spacer(1, 12))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3b: MONTHLY SOLAR RESOURCE & GENERATION TABLE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_bar("SECTION 3b — MONTHLY SOLAR RESOURCE &amp; GENERATION FORECAST"))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"Monthly averages from NASA POWER 22-year climatology (2001–2022). "
        f"Generation calculated for {fmt(r['act_kwp'],1)} kWp system at PR {r['pr']}%.",
        S_note))
    story.append(Spacer(1, 5))

    monthly_rows_pdf = calc_monthly(climate, r['act_kwp'], r['pr'], r['degr'])
    annual_total_mwh = sum(row['gen_mwh'] for row in monthly_rows_pdf)

    # Column headers
    mo_header = ["Month", "Days", "GHI\n(kWh/m\u00b2/day)", "Monthly GHI\n(kWh/m\u00b2)",
                 "Kt", "Avg Temp\n(\u00b0C)", "Max Temp\n(\u00b0C)", "Wind\n(m/s)",
                 "Temp\nDerating", "Generation\n(MWh)", "Cap.\nFactor %"]
    mo_data = [mo_header]
    for row in monthly_rows_pdf:
        mo_data.append([
            row["month"],
            str(row["days"]),
            f"{row['ghi_daily']:.2f}",
            f"{row['ghi_total']:.0f}",
            f"{row['clearness']:.3f}" if row['clearness'] else "—",
            f"{row['temp_avg']:.1f}",
            f"{row['temp_max']:.1f}",
            f"{row['wind_50m']:.1f}" if row['wind_50m'] else "—",
            f"-{row['t_dera_pct']}%",
            f"{row['gen_mwh']:.1f}",
            f"{row['cf_pct']:.1f}%",
        ])

    # Annual totals row
    avg_ghi  = round(sum(r2["ghi_daily"] for r2 in monthly_rows_pdf)/12, 2)
    tot_ghi  = round(sum(r2["ghi_total"] for r2 in monthly_rows_pdf), 0)
    avg_kt   = round(sum(r2["clearness"] for r2 in monthly_rows_pdf if r2["clearness"])/12, 3)
    avg_temp = round(sum(r2["temp_avg"]  for r2 in monthly_rows_pdf)/12, 1)
    max_temp = round(max(r2["temp_max"]  for r2 in monthly_rows_pdf), 1)
    avg_wind = round(sum(r2["wind_50m"]  for r2 in monthly_rows_pdf if r2["wind_50m"])/12, 1)
    avg_dera = round(sum(r2["t_dera_pct"]for r2 in monthly_rows_pdf)/12, 1)
    avg_cf   = round(sum(r2["cf_pct"]    for r2 in monthly_rows_pdf)/12, 1)
    mo_data.append([
        "ANNUAL", "365",
        f"{avg_ghi:.2f}", f"{int(tot_ghi)}",
        f"{avg_kt:.3f}", f"{avg_temp:.1f}", f"{max_temp:.1f}",
        f"{avg_wind:.1f}", f"-{avg_dera}% avg",
        f"{round(annual_total_mwh,1)}", f"{avg_cf:.1f}%",
    ])

    # Column widths — 11 columns, must sum exactly to W
    cw11 = [
        W*0.072, W*0.046, W*0.095, W*0.100,
        W*0.065, W*0.082, W*0.082, W*0.075,
        W*0.095, W*0.100, W*0.088,
    ]
    mo_tbl = Table(mo_data, colWidths=cw11, repeatRows=1)
    mo_style = TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  G_DARK),
        ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
        ("FONTNAME",      (0,0),(-1,0),  BOLD_FONT),
        ("FONTSIZE",      (0,0),(-1,0),  7),
        ("FONTNAME",      (0,1),(-1,-2), BODY_FONT),
        ("FONTSIZE",      (0,1),(-1,-1), 7.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [WHITE, G_PALE]),
        ("GRID",          (0,0),(-1,-1), 0.3, GR_MD),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("ALIGN",         (1,0),(-1,-1), "CENTER"),
        # Highlight annual totals row
        ("BACKGROUND",    (0,-1),(-1,-1), G_DARK),
        ("TEXTCOLOR",     (0,-1),(-1,-1), WHITE),
        ("FONTNAME",      (0,-1),(-1,-1), BOLD_FONT),
        ("FONTSIZE",      (0,-1),(-1,-1), 7.5),
        # Highlight peak generation month
    ])
    mo_tbl.setStyle(mo_style)
    story.append(mo_tbl)
    story.append(Spacer(1, 4))
    _peak_m = max(monthly_rows_pdf, key=lambda x: x['gen_mwh'])
    _low_m  = min(monthly_rows_pdf, key=lambda x: x['gen_mwh'])
    wind_note_pdf = (f"   |   Wind contribution: +{fmt(r['ann_wind_mwh'],1)} MWh/yr (annual total incl. wind: "
                     f"{round(annual_total_mwh + r['ann_wind_mwh'],1)} MWh/yr)") if r['wind_kw']>0 else ""
    story.append(Paragraph(
        f"Peak solar month: {_peak_m['month']} ({_peak_m['gen_mwh']:.1f} MWh)   |   "
        f"Lowest solar month: {_low_m['month']} ({_low_m['gen_mwh']:.1f} MWh)   |   "
        f"Solar annual total: {round(annual_total_mwh,1)} MWh/yr{wind_note_pdf}",
        S_note))
    story.append(Spacer(1, 12))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4: TECHNICAL SPECIFICATIONS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_bar("SECTION 4 — TECHNICAL SPECIFICATIONS"))
    story.append(Spacer(1, 5))

    c55 = W * 0.55
    c45 = W * 0.45

    # PV module table
    panel_tech = module_choice.split(" (")[0]
    tracker_note = mounting_choice.split("—")[0].strip()
    if pvgis_data and pvgis_data.get("yield_kwh_yr") and r["pvgis_used"]:
        pvgis_src = f"PVGIS JRC: {fmt(pvgis_data['yield_kwh_yr'],0)} kWh/yr"
    elif pvgis_data and pvgis_data.get("yield_kwh_yr"):
        pvgis_src = f"NASA POWER model (PVGIS cross-check: {fmt(pvgis_data['yield_kwh_yr'],0)} kWh/yr)"
    else:
        pvgis_src = "NASA POWER model"
    story.append(kv_tbl("PV MODULE &amp; SOLAR SYSTEM", [
        ("Module technology",        panel_tech),
        ("Module wattage",           f"{MODULE_SPECS[module_choice]['wp']} Wp"),
        ("Module efficiency",        f"{MODULE_SPECS[module_choice]['eff']*100:.1f}%"),
        ("Temp. coefficient (Pmax)", f"{MODULE_SPECS[module_choice]['temp_coef']*100:.3f}%/C"),
        ("Number of panels",         fmt(r['num_pan'])),
        ("DC system capacity",       f"{fmt(r['act_kwp'],1)} kWp"),
        ("Mounting system",          tracker_note),
        ("Ground cover ratio (GCR)", f"{r['gcr']}  ({int(r['gcr']*100)}% ground coverage)"),
        ("Panel orientation",        azimuth),
        ("Fixed tilt angle",         f"{tilt_angle} degrees"),
        ("Soiling loss assumed",      f"{soiling_loss}%"),
        ("Operating cell temp (avg)",f"{r['cell_temp']} C"),
        ("Temperature derating",     f"-{r['temp_dera']}% vs nameplate (STC)"),
        ("Bifacial/albedo gain",     f"+{r['bifacial_g']}%" if r['bifacial_g'] > 0 else "N/A"),
        ("Performance ratio (PR)",   f"{r['pr']}%"),
        ("Specific yield",           f"{fmt(r['spec_yld'],0)} kWh/kWp/yr"),
        ("Annual degradation",       f"{r['degr']}%/yr"),
        ("Generation data source",   pvgis_src),
    ], c55, c45))
    story.append(Spacer(1, 6))

    # Inverter &amp; grid table
    inv_rows_data = [
        ("Inverter type",     inverter_choice.split("(")[0].strip()),
        ("Inverter efficiency",f"{INVERTER_TYPES[inverter_choice]['eff']*100:.1f}%"),
        ("Grid connection",   grid_type),
        ("Net metering",      "Yes — available" if r['net_metering'] else "No"),
    ]
    if r['bess_kwh'] > 0:
        inv_rows_data += [
            ("Battery chemistry",  bess_chem),
            ("BESS total capacity",f"{fmt(r['bess_kwh'],1)} kWh"),
            ("BESS power rating",  f"{fmt(r['bess_kw'],1)} kW"),
            ("BESS duration",      f"{r['bess_h']} hours"),
            ("Round-trip efficiency","92-95%"),
            ("Cycle life",         "4,000-6,000 cycles (LFP)"),
            ("BESS CAPEX",         aed_s(r['bess_cap_aed'])),
        ]
    story.append(kv_tbl("INVERTER, GRID &amp; BESS", inv_rows_data, c55, c45))
    story.append(Spacer(1, 6))

    # Wind turbine specs (hybrid only)
    if r['wind_kw'] > 0:
        iec_class = "IEC Class I" if r['h_hub'] >= 100 else "IEC Class II"
        turbine_spacing_m = r['r_dt'] * 5 if r['r_dt'] > 0 else 0
        wind_rows_data = [
            ("Wind capacity",            f"{fmt(r['wind_kw'],1)} kW total"),
            ("Turbine rated power",       f"{fmt(r['t_kw'])} kW each"),
            ("Number of turbines",        fmt(r['n_t'])),
            ("IEC wind class",            iec_class),
            ("Hub height",               f"{r['h_hub']} m"),
            ("Rotor diameter",            f"{r['r_dt']} m"),
            ("Minimum turbine spacing",   f"{turbine_spacing_m} m (5x rotor dia.)"),
            ("Capacity factor (modelled)",f"{r['wind_cf']}%"),
            ("Annual wind generation",    f"{fmt(r['ann_wind_mwh'],1)} MWh/yr"),
        ]
        story.append(kv_tbl("WIND TURBINE SPECIFICATIONS", wind_rows_data, c55, c45))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 6))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5: FINANCIAL ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_bar("SECTION 5 — FINANCIAL ANALYSIS (AED)"))
    story.append(Spacer(1, 5))

    # CAPEX breakdown
    capex_rows = [
        ("Total CAPEX",          aed_s(r['total_cap'])),
        ("CAPEX per kW (total system)" if r['wind_kw']>0 else "CAPEX per Wp",
         f"AED {fmt(r['cap_kw_tot'],0)}/kW (solar+wind)" if r['wind_kw']>0 else f"AED {r['cap_wp']:.2f}/Wp"),
    ] + [(f"  {k}", f"{v}%") for k, v in r['cb'].items() if v > 0] + [
        ("Equity required",      aed_s(r['eq_aed'])),
        ("Project debt",         aed_s(r['dbt_aed'])),
        ("Debt ratio",           f"{r['debt_ratio']}%"),
        ("Debt interest rate",   f"{r['debt_rate']}%"),
        ("Annual O&amp;M cost",      aed_s(r['ann_opex'])),
    ]
    story.append(kv_tbl("CAPITAL EXPENDITURE BREAKDOWN", capex_rows, c55, c45))
    story.append(Spacer(1, 6))

    # Financial returns
    returns_rows = [
        ("Electricity tariff (avoided cost)", f"{int(r['tariff_aed']*100)} fils/kWh"),
        ("Year-1 gross revenue",   aed_s(r['y1rev'])),
        ("Year-1 net income",      aed_s(r['y1net'])),
        ("LCOE",                   f"AED {r['lcoe']:.0f}/MWh  ({r['lcoe']/10:.1f} fils/kWh)"),
        ("Simple payback period",  f"{r['payback']} years"),
        ("Project IRR",            f"{r['irr']}%" if r['irr'] else "—"),
        ("Equity IRR",             f"{r['eq_irr']}%" if r['eq_irr'] else "—"),
        (f"NPV ({r['life']} yr, {r['wacc']}% WACC)", aed_s(r['npv'])),
        ("DSCR (year 1)",          f"{r['dscr']}x" if r['dscr'] else "N/A (no debt)"),
        ("Annual debt service",    aed_s(r['ann_ds']) if r['ann_ds'] > 0 else "—"),
        ("Carbon credit revenue",  f"{aed_s(r['co2_rev'])}/yr  (at AED {carbon_price:.0f}/tonne)"),
    ]
    story.append(kv_tbl("FINANCIAL RETURNS", returns_rows, c55, c45))
    story.append(Spacer(1, 12))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6: SUSTAINABILITY
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_bar("SECTION 6 — SUSTAINABILITY &amp; ENVIRONMENTAL IMPACT"))
    story.append(Spacer(1, 5))
    story.append(kv_tbl("ENVIRONMENTAL METRICS", [
        ("CO2 avoided per year",            f"{fmt(r['co2_yr'],1)} tonnes/yr"),
        (f"CO2 avoided over {r['life']} years", f"{fmt(r['co2_lf'],0)} tonnes"),
        ("UAE households powered / year",   fmt(r['hh'])),
        ("Carbon credit value",             f"{aed_s(r['co2_rev'])}/yr"),
        ("Grid emission factor",            "0.341 kgCO2/kWh  (DEWA Clean Energy Report 2023)"),
        ("UAE Net Zero alignment",          "Supports UAE 2050 Net Zero &amp; 44% clean energy target"),
        ("SDG alignment",                   "SDG 7 (Clean Energy), SDG 11 (Sustainable Cities), SDG 13 (Climate Action)"),
    ], c55, c45))
    story.append(Spacer(1, 12))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7: RISKS &amp; NEXT STEPS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_bar("SECTION 7 — KEY RISKS &amp; MITIGATIONS"))
    story.append(Spacer(1, 5))

    risk_data = [
        ["Risk",                                            "Mitigation"],
        # Soiling risk description adapts to humidity/climate
        ["Soiling & dust" + (" — arid/desert" if climate.get("humidity",50)<55 else " — coastal/tropical"),
         "Bi-weekly dry cleaning or robotic auto-cleaning; anti-soiling glass coating" if climate.get("humidity",50)<55
         else "Monthly cleaning sufficient; anti-reflective coating recommended for high-humidity/coastal sites"],
        [f"High cell temperature ({r['cell_temp']}C avg operating)", "Specify TOPCon/HJT modules with temp. coeff. below -0.30%/C"],
        ["Grid curtailment by DEWA/SEWA",                  "Include active power control in inverter spec; evaluate BESS for peak shifting"],
        ["Tariff / regulatory change",                     "Lock in net metering agreement or long-term PPA before financial close"],
        ["Sand abrasion on anti-reflective coating",       "Specify IEC 61215 / IP67 rated modules with hardened AR glass"],
    ]
    risk_tbl = Table(risk_data, colWidths=[W*0.42, W*0.58])
    risk_tbl.setStyle(ts_header())
    story.append(risk_tbl)
    story.append(Spacer(1, 10))

    story.append(section_bar("SECTION 8 — RECOMMENDED NEXT STEPS"))
    story.append(Spacer(1, 6))
    util_short = utility.split("(")[0].strip()
    steps = [
        f"Submit interconnection / net metering application to {util_short} — " + ("Shams Dubai portal (shams.dewa.gov.ae)" if "DEWA" in utility else "SEWA online portal (sewa.gov.ae)" if "SEWA" in utility else "FEWA customer portal" if "FEWA" in utility else "ADDC/AADC customer portal" if "ADDC" in utility else "local utility customer portal"),
        f"Commission bankable P50/P90 energy yield assessment for {safe_pdf_text(location_name)} — required for project financing at {aed_s(r['total_cap'])} scale",
        f"Appoint DEWA/Trakhees-approved EPC contractor and obtain No Objection Certificate (NOC) from relevant authority",
        f"Confirm site land availability: minimum {fmt(r['site_m2'],0)} m2 ({fmt(r['site_ha'],2)} ha) required for this system",
        f"Develop lender-ready financial model using P90 scenario — target DSCR of 1.20x or above (current model: {r['dscr']}x)" if r['dscr'] else "Develop lender-ready financial model using P90 generation scenario",
    ]
    for i, step in enumerate(steps, 1):
        story.append(Paragraph(f"{i}.   {step}", S_body))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=GR_MD))
    story.append(Spacer(1, 4))
    footer_src = "NASA POWER API (2001-2022)"
    if pvgis_data and pvgis_data.get("yield_kwh_yr"):
        footer_src += "  |  PVGIS 5.2 EU JRC"
    story.append(Paragraph(
        f"Report generated: {now}   |   Climate data: {footer_src}"
        f"   |   Tariffs: DEWA/SEWA/FEWA 2024   |   SP Optimizer UAE Edition",
        S_footer))

    doc.build(story)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT DISPLAY RENDERER
# ─────────────────────────────────────────────────────────────────────────────
def render_screen(r, climate, pvgis_data, location_name, lat, lon,
                  connected_power, power_unit, project_label, utility, mounting_choice):

    bc={"solar":"badge-solar","wind":"badge-wind","hybrid":"badge-hybrid"}.get(r["badge"],"badge-solar")
    st.markdown(f'<span class="badge {bc}">{r["source"]}</span>', unsafe_allow_html=True)
    pvgis_note="PVGIS JRC" if r["pvgis_used"] else "NASA model"
    st.markdown(
        f"**{fmt(r['act_kwp'],1)} kWp** system · {fmt(r['ann_gen_mwh'],1)} MWh/yr · "
        f"{r['self_s']}% self-sufficiency · PR {r['pr']}% · "
        f"{r['payback']} yr payback · {r['irr']}% IRR · yield source: {pvgis_note}")

    # ── BIG AREA CARD ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="area-hero">
      <h2>📐 Required site area for implementation</h2>
    """, unsafe_allow_html=True)

    ac1,ac2,ac3,ac4,ac5 = st.columns(5)
    ac1.markdown(f'<div class="area-stat"><div class="av">{fmt(r["panel_m2"],0)}</div><div class="al">Panel area (m²)</div></div>', unsafe_allow_html=True)
    ac2.markdown(f'<div class="area-stat"><div class="av">{fmt(r["array_m2"],0)}</div><div class="al">Array footprint (m²)</div></div>', unsafe_allow_html=True)
    ac3.markdown(f'<div class="area-stat"><div class="av">{fmt(r["site_m2"],0)}</div><div class="al">Total site (m²)</div></div>', unsafe_allow_html=True)
    ac4.markdown(f'<div class="area-stat"><div class="av">{fmt(r["site_ha"],3)}</div><div class="al">Total site (ha)</div></div>', unsafe_allow_html=True)
    ac5.markdown(f'<div class="area-stat"><div class="av">{fmt(r["site_m2_kwp"],1)}</div><div class="al">m² per kWp</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if not r["area_ok"] and r["max_kwp_area"]:
        st.markdown(f'<div class="area-warn">⚠️ Your available area ({fmt(avail_m2_g,0)} m²) can fit max <b>{fmt(r["max_kwp_area"],0)} kWp</b> — below the required {fmt(r["act_kwp"],0)} kWp. Consider a higher-efficiency module or single-axis tracker.</div>', unsafe_allow_html=True)
    elif avail_m2_g and avail_m2_g > 0:
        st.success(f"✅ Available area ({fmt(avail_m2_g,0)} m²) is sufficient for the {fmt(r['act_kwp'],0)} kWp system.")

    # Area breakdown detail
    with st.expander("📐 Area breakdown detail"):
        mode_label = "🔒 Area-constrained mode — system sized to fit available space" if r["area_mode"]=="area" else "📏 Load-constrained mode — area calculated for full load coverage"
        st.caption(mode_label)
        ad1,ad2 = st.columns(2)
        ad1.markdown(f"""
| Component | Value |
|---|---|
| Mode | {"Area → System" if r["area_mode"]=="area" else "Load → Area"} |
| Panels | {fmt(r['num_pan'])} × {MODULE_SPECS[module_choice]['wp']} Wp |
| Panel area each | {round(MODULE_SPECS[module_choice]['wp']/1000/MODULE_SPECS[module_choice]['eff'],2)} m² |
| Total panel area | **{fmt(r['panel_m2'],1)} m²** |
| GCR | {r['gcr']} ({int(r['gcr']*100)}% coverage) |
| Array footprint | **{fmt(r['array_m2'],1)} m²** |
        """)
        ad2.markdown(f"""
| Component | Value |
|---|---|
| Available / required area | **{fmt(avail_m2_g,0) if avail_m2_g else fmt(r["site_m2"],0)} m²** |
| Land buffer factor | {MOUNTING_TYPES[mounting_choice]['land_buffer']}× |
| Setback / unusable | {setback_pct}% |
| Total site area | **{fmt(r['site_m2'],0)} m²** |
| In hectares | **{fmt(r['site_ha'],3)} ha** |
| Load coverage | **{r["load_covered_pct"]}%** |
| Site m²/kWp | **{fmt(r['site_m2_kwp'],1)} m²/kWp** |
        """)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.divider()
    k=st.columns(4)
    k[0].metric("Renewable capacity",  f"{fmt(r['act_kwp'],1)} kWp")
    k[1].metric("Annual generation",   f"{fmt(r['ann_gen_mwh'],1)} MWh/yr")
    k[2].metric("Self-sufficiency",    f"{r['self_s']}%")
    k[3].metric("Capacity factor",     f"{r['cap_f']}%")
    k=st.columns(4)
    k[0].metric("Total CAPEX",         aed_s(r['total_cap']))
    k[1].metric("CAPEX / Wp",          f"AED {r['cap_wp']:.2f}")
    k[2].metric("LCOE",                f"AED {r['lcoe']:.0f}/MWh")
    k[3].metric("Project IRR",         f"{r['irr']}%" if r['irr'] else "—")
    k=st.columns(4)
    k[0].metric("Simple payback",      f"{r['payback']} yrs")
    k[1].metric(f"NPV ({r['life']} yr)",aed_s(r['npv']))
    k[2].metric("CO₂ offset / year",   f"{fmt(r['co2_yr'],1)} t/yr")
    k[3].metric("Households powered",  fmt(r['hh']))


    # ── Monthly solar & generation breakdown ──────────────────────────────────
    st.divider()
    st.subheader("📅 Monthly solar resource & generation forecast")
    monthly_rows = calc_monthly(climate, r['act_kwp'], r['pr'], r['degr'])
    annual_gen_check = sum(row['gen_mwh'] for row in monthly_rows)

    # Display as a clean table
    import pandas as pd
    df = pd.DataFrame([{
        "Month":         row["month"],
        "Days":          row["days"],
        "GHI (kWh/m²/day)": row["ghi_daily"],
        "Monthly GHI (kWh/m²)": row["ghi_total"],
        "Clearness (Kt)":row["clearness"],
        "Avg Temp (°C)": row["temp_avg"],
        "Max Temp (°C)": row["temp_max"],
        "Wind @ 50m (m/s)":row["wind_50m"],
        "Temp Derating (%)":f"-{row['t_dera_pct']}%",
        "Generation (MWh)":row["gen_mwh"],
        "Capacity Factor (%)":row["cf_pct"],
    } for row in monthly_rows])

    # Add totals / averages row
    totals = {
        "Month": "ANNUAL",
        "Days": 365,
        "GHI (kWh/m²/day)": round(sum(r2["ghi_daily"] for r2 in monthly_rows)/12, 2),
        "Monthly GHI (kWh/m²)": round(sum(r2["ghi_total"] for r2 in monthly_rows), 0),
        "Clearness (Kt)": round(sum(r2["clearness"] for r2 in monthly_rows if r2["clearness"])/12, 3),
        "Avg Temp (°C)": round(sum(r2["temp_avg"] for r2 in monthly_rows)/12, 1),
        "Max Temp (°C)": round(max(r2["temp_max"] for r2 in monthly_rows), 1),
        "Wind @ 50m (m/s)": round(sum(r2["wind_50m"] for r2 in monthly_rows if r2["wind_50m"])/12, 2),
        "Temp Derating (%)": f"-{round(sum(float(r2['t_dera_pct']) for r2 in monthly_rows)/12, 1)}% avg",
        "Generation (MWh)": round(annual_gen_check, 1),
        "Capacity Factor (%)": round(sum(r2["cf_pct"] for r2 in monthly_rows)/12, 1),
    }
    df_total = pd.DataFrame([totals])
    df_full  = pd.concat([df, df_total], ignore_index=True)
    st.dataframe(df_full, use_container_width=True, hide_index=True)
    wind_monthly_note = ""
    if r['wind_kw'] > 0:
        wind_monthly_note = (f" + {fmt(r['ann_wind_mwh'],1)} MWh/yr wind (distributed evenly, "
                             f"not shown per month). Total system: {round(annual_gen_check + r['ann_wind_mwh'],1)} MWh/yr.")
    st.caption(f"Monthly averages from NASA POWER 22-year climatology · Solar generation: {round(annual_gen_check,1)} MWh/yr · "
               f"System: {fmt(r['act_kwp'],1)} kWp at PR {r['pr']}%{wind_monthly_note}")

    # ── What can you run daily ────────────────────────────────────────────────
    st.divider()
    st.subheader("⚡ What can you run daily on this system?")
    st.markdown("Based on your **average daily generation** — select your project context to see what the system can power:")

    daily_gen_avg = r["ann_gen"] / 365   # kWh/day — ann_gen is in kWh

    # Pre-calculate monthly rows once for efficiency
    _monthly_rows = calc_monthly(climate, r['act_kwp'], r['pr'], r['degr'])
    _peak_row  = max(_monthly_rows, key=lambda x: x['gen_mwh'])
    _low_row   = min(_monthly_rows, key=lambda x: x['gen_mwh'])
    peak_day_kwh = _peak_row['gen_mwh'] * 1000 / _peak_row['days']   # MWh/month → kWh/day
    low_day_kwh  = _low_row['gen_mwh']  * 1000 / _low_row['days']

    wc1, wc2 = st.columns([1, 3])
    with wc1:
        context = st.radio("Context", ["Home", "Office", "Industrial"],
            help="Home = villa/residential. Office = commercial building. Industrial = factory/warehouse.")
        st.metric("Avg daily generation", f"{round(daily_gen_avg,1)} kWh/day")
        st.metric(f"Peak day ({_peak_row['month']} avg)",  f"{round(peak_day_kwh,1)} kWh/day")
        st.metric(f"Lowest day ({_low_row['month']} avg)", f"{round(low_day_kwh,1)} kWh/day")

    with wc2:
        app_results = calc_appliance_runs(daily_gen_avg, context)
        import pandas as pd
        df_app = pd.DataFrame([{
            "Appliance":            f"{a['icon']} {a['name']}",
            "Power (W)":            f"{a['watts']:,}",
            "Daily use (hrs)":      a["hours"],
            "Energy / day (kWh)":   a["daily_kwh"],
            "Units the system runs": a["qty"] if a["qty"] > 0 else "< 1",
        } for a in app_results])
        st.dataframe(df_app, use_container_width=True, hide_index=True)
        st.caption(
            f"Based on {round(daily_gen_avg,1)} kWh/day average generation from {fmt(r['act_kwp'],1)} kWp system. "
            f"'Units the system runs' = how many of each appliance can operate simultaneously at listed daily hours. "
            f"Actual usage depends on operating schedule and coincidence factor.")

    # ── Technical ─────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Technical specifications")
    c1,c2=st.columns(2)
    with c1:
        with st.expander("☀️ PV module & system",expanded=True):
            rows=[("Module",module_choice.split(" (")[0]),
                  ("Module wattage",f"{MODULE_SPECS[module_choice]['wp']} Wp"),
                  ("Efficiency",f"{MODULE_SPECS[module_choice]['eff']*100:.1f}%"),
                  ("Temp. coefficient",f"{MODULE_SPECS[module_choice]['temp_coef']*100:.3f}%/°C"),
                  ("Number of panels",fmt(r['num_pan'])),
                  ("DC capacity",f"{fmt(r['act_kwp'],1)} kWp"),
                  ("Mounting",mounting_choice.split("—")[0].strip()),
                  ("GCR",f"{r['gcr']}"),("PR",f"{r['pr']}%"),
                  ("Cell temp (avg)",f"{r['cell_temp']}°C"),
                  ("Temp. derating",f"−{r['temp_dera']}%"),
                  ("Specific yield",f"{fmt(r['spec_yld'],0)} kWh/kWp/yr")]
            st.markdown("<table>"+"".join(f"<tr><td>{a}</td><td>{b}</td></tr>"for a,b in rows)+"</table>",unsafe_allow_html=True)
        if r['bess_kwh']>0:
            with st.expander("🔋 BESS",expanded=True):
                rows=[("Chemistry",bess_chem),("Capacity",f"{fmt(r['bess_kwh'],1)} kWh"),
                      ("Power",f"{fmt(r['bess_kw'],1)} kW"),("Duration",f"{r['bess_h']} hrs"),
                      ("BESS CAPEX",aed_s(r['bess_cap_aed']))]
                st.markdown("<table>"+"".join(f"<tr><td>{a}</td><td>{b}</td></tr>"for a,b in rows)+"</table>",unsafe_allow_html=True)
    with c2:
        with st.expander("💰 Financial breakdown",expanded=True):
            rows=[("Total CAPEX",aed_s(r['total_cap'])),
                  ("CAPEX/Wp",f"AED {r['cap_wp']:.2f}"),
                  ("Tariff",f"{int(r['tariff_aed']*100)} fils/kWh"),
                  ("Year-1 revenue",aed_s(r['y1rev'])),
                  ("Year-1 net income",aed_s(r['y1net'])),
                  ("LCOE",f"AED {r['lcoe']:.0f}/MWh"),
                  ("Payback",f"{r['payback']} years"),
                  ("Project IRR",f"{r['irr']}%" if r['irr'] else "—"),
                  ("Equity IRR",f"{r['eq_irr']}%" if r['eq_irr'] else "—"),
                  (f"NPV ({r['life']} yr)",aed_s(r['npv'])),
                  ("DSCR yr-1",f"{r['dscr']}×" if r['dscr'] else "N/A"),
                  ("CO₂ credit revenue",f"{aed_s(r['co2_rev'])}/yr")]
            st.markdown("<table>"+"".join(f"<tr><td>{a}</td><td>{b}</td></tr>"for a,b in rows)+"</table>",unsafe_allow_html=True)
        with st.expander("🌱 Sustainability",expanded=False):
            rows=[("CO₂ offset/yr",f"{fmt(r['co2_yr'],1)} tonnes"),
                  ("Lifetime CO₂",f"{fmt(r['co2_lf'],0)} tonnes"),
                  ("Households powered",fmt(r['hh'])),
                  ("Carbon credit value",f"{aed_s(r['co2_rev'])}/yr"),
                  ("Emission factor","0.341 kgCO₂/kWh (DEWA 2023)")]
            st.markdown("<table>"+"".join(f"<tr><td>{a}</td><td>{b}</td></tr>"for a,b in rows)+"</table>",unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
avail_m2_g = 0  # global for use in render
num_pan_global = 0

if go:
    if not coord_input: st.error("Please enter a location."); st.stop()
    if not connected_power: st.error("Please enter the connected load."); st.stop()

    avail_m2_g = available_area

    with st.status("Running SP Optimizer...", expanded=True) as status:
        st.write("📍 Resolving location...")
        coords = parse_coords(coord_input)
        if coords:
            lat,lon=coords
            location_name=rev_geocode(lat,lon)
            # If rev_geocode just returned coordinates, label it nicely
            if location_name.replace(".","").replace(",","").replace("-","").replace(" ","").isdigit() or (location_name.count(",")==1 and all(c in "0123456789.,- " for c in location_name)):
                location_name=f"Site ({lat:.4f}N, {lon:.4f}E)"
        else:
            gc=geocode(coord_input)
            if not gc:
                status.update(label="Not found",state="error")
                st.error(f"Cannot locate '{coord_input}'. Try: 25.2048, 55.2708"); st.stop()
            lat,lon=gc; location_name=coord_input
        st.write(f"✅ **{location_name}** — {lat:.4f}°N, {lon:.4f}°E")

        st.write("🛰️ NASA POWER climate data...")
        climate=fetch_nasa(lat,lon)
        if "error" in climate:
            status.update(label="NASA error",state="error")
            st.error(f"NASA POWER error: {climate['error']}"); st.stop()
        st.write(f"✅ GHI {climate.get('ghi_daily','—')} kWh/m²/day · Wind {climate.get('ws50','—')} m/s · Temp {climate.get('temp','—')}°C · Kt {climate.get('clearness','—')}")

        connected_kw = to_kw(connected_power, power_unit)
        ptype_cfg_v  = PROJECT_TYPES[project_label]
        psh_v        = climate.get("psh", 5.5)
        tariff_aed   = custom_tariff / 100

        # ── Step A: Run calculations first (needed to get actual act_kwp) ──
        st.write("⚙️ Engineering calculations...")
        result = calculate(
            connected_kw=connected_kw, ptype_cfg=ptype_cfg_v,
            climate=climate, pvgis_data=None,   # no PVGIS yet — fetch after sizing
            module_choice=module_choice, mounting_choice=mounting_choice,
            inverter_choice=inverter_choice, grid_type=grid_type,
            oversizing=oversizing, tilt=tilt_angle, az_label=azimuth,
            soiling_pct=soiling_loss, albedo_pct=ground_albedo,
            tariff_aed=tariff_aed, wacc=wacc, life=lifetime,
            degr=degradation, opex_pct=opex_pct, debt_ratio=debt_ratio,
            debt_rate=debt_rate, bess_override=bess_override,
            bess_chem=bess_chem, bess_h_custom=bess_h_custom,
            include_wind=include_wind, carbon_price_aed=carbon_price,
            net_metering=net_metering, avail_m2=available_area,
            setback_pct=setback_pct, lat=lat, lon=lon,
        )
        act_kwp_final = result["act_kwp"]   # correct kWp for this project

        # ── Step B: Fetch PVGIS with the CORRECT system size ───────────────
        st.write("🌍 PVGIS cross-check (EU JRC) — using actual system size...")
        pvgis_data = fetch_pvgis(lat, lon, tilt_angle, az_deg(azimuth), round(act_kwp_final, 1))
        if pvgis_data and pvgis_data.get("yield_kwh_yr"):
            st.write(f"✅ PVGIS yield {fmt(pvgis_data['yield_kwh_yr'],0)} kWh/yr · losses {pvgis_data.get('loss_pct','—')}% · system {act_kwp_final} kWp")
        else:
            st.write("ℹ️ PVGIS not available — using NASA model")
            pvgis_data = None

        # ── Step C: Re-run calculations with PVGIS if available ────────────
        if pvgis_data and pvgis_data.get("yield_kwh_yr"):
            st.write("🔄 Updating generation with PVGIS verified yield...")
            result = calculate(
                connected_kw=connected_kw, ptype_cfg=ptype_cfg_v,
                climate=climate, pvgis_data=pvgis_data,
                module_choice=module_choice, mounting_choice=mounting_choice,
                inverter_choice=inverter_choice, grid_type=grid_type,
                oversizing=oversizing, tilt=tilt_angle, az_label=azimuth,
                soiling_pct=soiling_loss, albedo_pct=ground_albedo,
                tariff_aed=tariff_aed, wacc=wacc, life=lifetime,
                degr=degradation, opex_pct=opex_pct, debt_ratio=debt_ratio,
                debt_rate=debt_rate, bess_override=bess_override,
                bess_chem=bess_chem, bess_h_custom=bess_h_custom,
                include_wind=include_wind, carbon_price_aed=carbon_price,
                net_metering=net_metering, avail_m2=available_area,
                setback_pct=setback_pct, lat=lat, lon=lon,
            )

        num_pan_global = result["num_pan"]
        st.write("✅ Complete")
        status.update(label="Report ready ✅", state="complete", expanded=False)

    # Climate bar
    st.divider()
    st.subheader(f"📍 {location_name}")
    st.caption(f"Lat {lat:.4f}°, Lon {lon:.4f}°  ·  Load: {connected_power:,.1f} {power_unit}  ·  {project_label}  ·  {utility}")
    c1,c2,c3,c4,c5,c6,c7=st.columns(7)
    c1.metric("Daily GHI",     f"{climate.get('ghi_daily','—')}","kWh/m²/day")
    c2.metric("Annual GHI",    f"{climate.get('ghi_annual','—')}","kWh/m²/yr")
    c3.metric("PSH",           f"{climate.get('psh','—')}","hrs/day")
    c4.metric("Clearness Kt",  f"{climate.get('clearness','—')}")
    c5.metric("Wind @ 50m",    f"{climate.get('ws50','—')}","m/s")
    c6.metric("Avg temp",      f"{climate.get('temp','—')}","°C")
    c7.metric("Max temp",      f"{climate.get('temp_max','—')}","°C")
    src="NASA POWER (22-yr avg, 2001–2022)"
    if pvgis_data and pvgis_data.get("yield_kwh_yr"): src+="  ·  PVGIS 5.2 EU JRC"
    st.markdown(f'<p class="src">{src}</p>',unsafe_allow_html=True)

    st.divider()
    render_screen(result,climate,pvgis_data,location_name,lat,lon,
                  connected_power,power_unit,project_label,utility,mounting_choice)

    # PDF download
    st.divider()
    with st.spinner("Generating PDF report..."):
        pdf_buf=generate_pdf(
            result,climate,pvgis_data,location_name,lat,lon,
            connected_power,power_unit,project_label,utility,
            module_choice,mounting_choice,inverter_choice,soiling_loss,
            tilt_angle,azimuth,ground_albedo,setback_pct,available_area,
            custom_tariff,wacc,lifetime,degradation,opex_pct,
            debt_ratio,debt_rate,carbon_price,bess_chem,net_metering)

    fname=f"SP_Optimizer_{location_name.split(',')[0].strip().replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    st.download_button(
        "📄 Download Professional PDF Report",
        data=pdf_buf,
        file_name=fname,
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )
    st.caption("PDF includes: cover page, area calculations, KPI summary, climate data, technical specs, financial analysis, sustainability metrics, risks & next steps.")
