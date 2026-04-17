import streamlit as st
import requests
import json
import math

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
        display: inline-block; padding: 5px 16px; border-radius: 20px;
        font-size: 0.82rem; font-weight: 600; margin-bottom: 0.8rem;
    }
    .badge-solar  { background:#EAF3DE; color:#3B6D11; }
    .badge-wind   { background:#E6F1FB; color:#185FA5; }
    .badge-hybrid { background:#EEEDFE; color:#534AB7; }
    table { width:100%; font-size:0.83rem; border-collapse:collapse; }
    td { padding:7px 4px; border-bottom:1px solid #f0f0f0; vertical-align:top; }
    td:first-child { color:#666; width:58%; }
    td:last-child  { font-weight:600; text-align:right; }
    tr:last-child td { border-bottom:none; }
    .bullet { font-size:0.84rem; color:#555; padding:3px 0; line-height:1.6; }
    .source-note { font-size:0.71rem; color:#aaa; margin-top:0.3rem; font-style:italic; }
    .info-box {
        background:#f0f7ff; border-left:3px solid #378ADD;
        border-radius:4px; padding:0.8rem 1rem; font-size:0.84rem;
        color:#185FA5; margin-bottom:1rem;
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

# ── Project type engineering parameters ──────────────────────────────────────
TYPE_PARAMS = {
    "utility":     {"op_hours": 24, "pv_wp": 580, "pv_eff": 0.223, "capex_wp": 0.55, "dc_ac": 1.28, "soiling": 0.95, "land_m2_kwp": 6.5,  "bess_hours": 0,   "label": "Utility-scale IPP"},
    "ci":          {"op_hours": 14, "pv_wp": 545, "pv_eff": 0.210, "capex_wp": 0.78, "dc_ac": 1.20, "soiling": 0.97, "land_m2_kwp": 7.0,  "bess_hours": 2,   "label": "Commercial & Industrial"},
    "residential": {"op_hours": 6,  "pv_wp": 415, "pv_eff": 0.200, "capex_wp": 1.05, "dc_ac": 1.10, "soiling": 0.98, "land_m2_kwp": 8.0,  "bess_hours": 4,   "label": "Residential / Community"},
    "offgrid":     {"op_hours": 20, "pv_wp": 545, "pv_eff": 0.210, "capex_wp": 1.10, "dc_ac": 1.15, "soiling": 0.95, "land_m2_kwp": 7.5,  "bess_hours": 48,  "label": "Remote / Off-grid"},
    "municipal":   {"op_hours": 12, "pv_wp": 545, "pv_eff": 0.210, "capex_wp": 0.85, "dc_ac": 1.18, "soiling": 0.97, "land_m2_kwp": 7.0,  "bess_hours": 3,   "label": "Municipal / Public Sector"},
    "agri":        {"op_hours": 14, "pv_wp": 545, "pv_eff": 0.210, "capex_wp": 0.82, "dc_ac": 1.15, "soiling": 0.96, "land_m2_kwp": 18.0, "bess_hours": 2,   "label": "Agri-PV / Agrivoltaics"},
    "industrial":  {"op_hours": 20, "pv_wp": 580, "pv_eff": 0.223, "capex_wp": 0.70, "dc_ac": 1.25, "soiling": 0.95, "land_m2_kwp": 6.5,  "bess_hours": 4,   "label": "Industrial Process Energy"},
    "ev":          {"op_hours": 16, "pv_wp": 430, "pv_eff": 0.205, "capex_wp": 0.95, "dc_ac": 1.10, "soiling": 0.97, "land_m2_kwp": 9.0,  "bess_hours": 4,   "label": "EV Charging / Mobility Hub"},
    "datacenter":  {"op_hours": 24, "pv_wp": 580, "pv_eff": 0.223, "capex_wp": 0.65, "dc_ac": 1.25, "soiling": 0.97, "land_m2_kwp": 7.0,  "bess_hours": 2,   "label": "Data Center / Tech Campus"},
    "mixed":       {"op_hours": 16, "pv_wp": 545, "pv_eff": 0.210, "capex_wp": 0.80, "dc_ac": 1.20, "soiling": 0.97, "land_m2_kwp": 7.5,  "bess_hours": 3,   "label": "Mixed-use Development"},
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ SP Optimizer")
    st.markdown("---")
    st.success("✅ No API key required")
    st.markdown("""
This app runs entirely on:
- **NASA POWER API** (free)
- **OpenStreetMap** (free)
- **Built-in engineering formulas**

No account needed. No cost. Unlimited use.

---
**Auto-fetched from NASA POWER:**
- Global Horizontal Irradiance (GHI)
- Peak sun hours (PSH)
- Wind speed at 50m
- Temperature & humidity
- Precipitation

22-year climatological average.
    """)

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("SP Optimizer")
st.markdown('<div class="info-box">⚡ Fully free — no API key required. Enter your connected load and location, and the app calculates everything using NASA climate data and built-in engineering models.</div>', unsafe_allow_html=True)

# ── Core inputs ───────────────────────────────────────────────────────────────
st.markdown('<p class="section-header">Core inputs</p>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([3, 1.5, 1])
coord_input     = c1.text_input("📍 Project location", placeholder="Coordinates: 25.2048, 55.2708   or   City: Dubai, UAE")
connected_power = c2.number_input("⚡ Total connected power", min_value=0.0, value=None, placeholder="e.g. 50", format="%.2f")
power_unit      = c3.selectbox("Unit", ["kW", "MW", "GW"])

st.markdown('<p class="section-header">Project type</p>', unsafe_allow_html=True)
project_label = st.selectbox("Project type", list(PROJECT_TYPES.keys()), label_visibility="collapsed")

with st.expander("💰 Financial parameters (optional)"):
    f1, f2, f3, f4 = st.columns(4)
    tariff   = f1.number_input("Grid tariff / PPA (¢/kWh)", min_value=0.0, value=None, placeholder="e.g. 8", format="%.2f", help="Local electricity price or PPA rate. Left blank = auto-estimated from location.")
    wacc     = f2.number_input("WACC / discount rate (%)", min_value=0.0, max_value=30.0, value=None, placeholder="e.g. 7", format="%.1f")
    lifetime = f3.number_input("Project lifetime (years)", min_value=1, max_value=50, value=None, placeholder="e.g. 25", format="%d")
    degradation = f4.number_input("Panel degradation (%/yr)", min_value=0.0, max_value=5.0, value=None, placeholder="e.g. 0.5", format="%.2f")

with st.expander("⚙️ System preferences (optional)"):
    grid_type   = st.radio("Grid connection", ["Grid-connected", "Hybrid + BESS", "Off-grid"], horizontal=True)
    oversizing  = st.slider("System oversizing factor", 1.0, 1.5, 1.15, 0.05, help="Factor applied above minimum required capacity to account for losses and future demand. 1.15 = 15% oversize.")

st.markdown("")
go = st.button("⚡ Calculate system design", use_container_width=True, type="primary")


# ═════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def parse_coordinates(text):
    parts = text.strip().replace(";", ",").split(",")
    if len(parts) == 2:
        try:
            lat, lon = float(parts[0].strip()), float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            pass
    return None

def geocode_city(name):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q": name, "format": "json", "limit": 1},
            headers={"User-Agent": "SPOptimizer/1.0"}, timeout=10)
        d = r.json()
        if d:
            return float(d[0]["lat"]), float(d[0]["lon"])
    except Exception:
        pass
    return None

def reverse_geocode(lat, lon):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "SPOptimizer/1.0"}, timeout=10)
        addr = r.json().get("address", {})
        parts = [addr[k] for k in ["city","town","village","state","country"] if addr.get(k)]
        return ", ".join(parts[:2]) if parts else f"{lat:.3f}, {lon:.3f}"
    except Exception:
        return f"{lat:.4f}, {lon:.4f}"

def fetch_nasa_power(lat, lon):
    params_list = "ALLSKY_SFC_SW_DWN,CLRSKY_SFC_SW_DWN,WS50M,WS10M,T2M,PRECTOTCORR,RH2M"
    url = (f"https://power.larc.nasa.gov/api/temporal/climatology/point"
           f"?parameters={params_list}&community=RE&longitude={lon}&latitude={lat}&format=JSON")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        props = r.json()["properties"]["parameter"]
        ghi_d  = props.get("ALLSKY_SFC_SW_DWN", {}).get("ANN")
        clr    = props.get("CLRSKY_SFC_SW_DWN", {}).get("ANN")
        ws50   = props.get("WS50M",  {}).get("ANN")
        ws10   = props.get("WS10M",  {}).get("ANN")
        temp   = props.get("T2M",    {}).get("ANN")
        precip = props.get("PRECTOTCORR", {}).get("ANN")
        humid  = props.get("RH2M",   {}).get("ANN")
        monthly_ghi = {k: v for k, v in props.get("ALLSKY_SFC_SW_DWN", {}).items() if k != "ANN"}
        return {
            "ghi_daily":    round(ghi_d, 3) if ghi_d else None,
            "ghi_annual":   int(ghi_d * 365) if ghi_d else None,
            "psh":          round(ghi_d, 3) if ghi_d else None,
            "clear_sky":    round(clr, 2) if clr else None,
            "wind_50m":     round(ws50, 2) if ws50 else None,
            "wind_10m":     round(ws10, 2) if ws10 else None,
            "temp":         round(temp, 1) if temp else None,
            "precip":       round(precip, 2) if precip else None,
            "humidity":     round(humid, 1) if humid else None,
            "monthly_ghi":  monthly_ghi,
        }
    except Exception as e:
        return {"error": str(e)}

def to_kw(value, unit):
    return value * {"kW": 1, "MW": 1_000, "GW": 1_000_000}[unit]

def estimate_grid_emission_factor(lat, lon):
    """Rough CO2 emission factor (kg/kWh) based on coordinates."""
    # GCC / Middle East
    if 12 <= lat <= 32 and 32 <= lon <= 65:
        return 0.55
    # Europe
    if 35 <= lat <= 72 and -12 <= lon <= 45:
        return 0.25
    # North America
    if 24 <= lat <= 72 and -140 <= lon <= -52:
        return 0.38
    # East Asia
    if 10 <= lat <= 55 and 100 <= lon <= 145:
        return 0.55
    # South Asia
    if 5 <= lat <= 37 and 65 <= lon <= 100:
        return 0.70
    # Africa
    if -35 <= lat <= 37 and -20 <= lon <= 55:
        return 0.50
    return 0.45  # global average default

def estimate_tariff(lat, lon):
    """Estimate local grid tariff (USD/kWh) based on region."""
    if 12 <= lat <= 32 and 32 <= lon <= 65:
        return 0.08   # GCC
    if 35 <= lat <= 72 and -12 <= lon <= 45:
        return 0.22   # Europe
    if 24 <= lat <= 72 and -140 <= lon <= -52:
        return 0.12   # North America
    if 10 <= lat <= 55 and 100 <= lon <= 145:
        return 0.10   # East Asia
    if 5 <= lat <= 37 and 65 <= lon <= 100:
        return 0.09   # South Asia
    return 0.11

def npv_calc(annual_cashflows, wacc_pct):
    r = wacc_pct / 100
    return sum(cf / (1 + r) ** (i + 1) for i, cf in enumerate(annual_cashflows))

def irr_calc(cashflows):
    """Simple IRR via bisection method."""
    def npv_at_rate(r):
        return sum(cf / (1 + r) ** i for i, cf in enumerate(cashflows))
    lo, hi = -0.99, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv_at_rate(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-6:
            break
    return (lo + hi) / 2 * 100


# ═════════════════════════════════════════════════════════════════════════════
# CORE ENGINEERING CALCULATOR
# ═════════════════════════════════════════════════════════════════════════════

def calculate(connected_kw, ptype, climate, grid_type, oversizing_factor,
              tariff_cents=None, wacc_pct=None, life_yrs=None, degradation_pct=None,
              lat=0, lon=0):

    p = TYPE_PARAMS[ptype]

    # ── Climate values ────────────────────────────────────────────────────────
    psh       = climate.get("psh", 5.0)
    temp      = climate.get("temp", 25.0)
    wind_50m  = climate.get("wind_50m", 5.0)
    ghi_ann   = climate.get("ghi_annual", psh * 365)

    # ── Source recommendation ─────────────────────────────────────────────────
    solar_score = psh / 6.0      # normalised to excellent (6 PSH = score 1.0)
    wind_score  = wind_50m / 8.0  # normalised to excellent (8 m/s = score 1.0)

    if solar_score >= 0.7 and wind_score >= 0.75:
        source     = "Solar PV + Wind Hybrid"
        badge      = "hybrid"
        solar_frac = 0.70
        wind_frac  = 0.30
    elif wind_score > solar_score and wind_score >= 0.75:
        source     = "Onshore Wind"
        badge      = "wind"
        solar_frac = 0.0
        wind_frac  = 1.0
    else:
        source     = "Solar PV"
        badge      = "solar"
        solar_frac = 1.0
        wind_frac  = 0.0

    if grid_type == "Off-grid":
        bess_hours = max(p["bess_hours"], 48)
    elif grid_type == "Hybrid + BESS":
        bess_hours = max(p["bess_hours"], 4)
    else:
        bess_hours = p["bess_hours"]

    # ── Demand & sizing ───────────────────────────────────────────────────────
    daily_demand_kwh = connected_kw * p["op_hours"]      # kWh/day

    # Temperature derating (Pmax coefficient -0.35%/°C above 25°C)
    temp_derating = 1.0 + (temp - 25.0) * (-0.0035)
    temp_derating = max(0.80, min(1.05, temp_derating))

    # Performance ratio
    inv_eff    = 0.975
    wiring_eff = 0.980
    mismatch   = 0.980
    pr = temp_derating * p["soiling"] * inv_eff * wiring_eff * mismatch
    pr = round(pr, 3)

    # Minimum system capacity then oversize
    if psh > 0:
        min_capacity_kwp = daily_demand_kwh / (psh * pr)
    else:
        min_capacity_kwp = connected_kw * 1.5
    system_kwp = min_capacity_kwp * oversizing_factor

    # Split for hybrid
    solar_kwp = system_kwp * solar_frac
    wind_kw   = system_kwp * wind_frac  # rated wind capacity

    # ── Panel count ───────────────────────────────────────────────────────────
    num_panels = math.ceil((solar_kwp * 1000) / p["pv_wp"]) if solar_kwp > 0 else 0
    actual_solar_kwp = (num_panels * p["pv_wp"]) / 1000

    # ── Annual generation ─────────────────────────────────────────────────────
    degradation  = (degradation_pct or 0.5) / 100
    annual_solar = actual_solar_kwp * psh * 365 * pr if actual_solar_kwp > 0 else 0

    # Wind: simplified AEP using Rayleigh distribution approximation
    if wind_kw > 0:
        wind_cf    = min(0.45, max(0.15, (wind_50m / 13) ** 3 * 0.45))
        annual_wind = wind_kw * wind_cf * 8760
    else:
        wind_cf    = 0
        annual_wind = 0

    annual_gen_kwh = annual_solar + annual_wind

    # Self-sufficiency
    annual_demand = daily_demand_kwh * 365
    self_suff     = min(100.0, annual_gen_kwh / annual_demand * 100) if annual_demand > 0 else 100.0

    # Specific yield & capacity factor
    specific_yield = (annual_solar / actual_solar_kwp) if actual_solar_kwp > 0 else 0
    total_cap_kw   = actual_solar_kwp + wind_kw
    cap_factor     = (annual_gen_kwh / (total_cap_kw * 8760) * 100) if total_cap_kw > 0 else 0

    # ── Inverter ──────────────────────────────────────────────────────────────
    inv_capacity_kva = actual_solar_kwp / p["dc_ac"] if actual_solar_kwp > 0 else 0
    inv_units = math.ceil(inv_capacity_kva / 5000) if inv_capacity_kva > 5000 else max(1, math.ceil(inv_capacity_kva / 110))

    # ── BESS ──────────────────────────────────────────────────────────────────
    if bess_hours > 0:
        bess_kwh = connected_kw * (bess_hours / 24) * daily_demand_kwh / max(connected_kw, 1)
        bess_kwh = connected_kw * (bess_hours / p["op_hours"])
        bess_kw  = connected_kw
        bess_capex = bess_kwh * 260   # USD/kWh LFP 2024
    else:
        bess_kwh = bess_kw = bess_capex = 0

    # ── Land area ─────────────────────────────────────────────────────────────
    land_m2  = actual_solar_kwp * p["land_m2_kwp"]
    land_ha  = land_m2 / 10_000

    # ── Financial model ───────────────────────────────────────────────────────
    capex_solar = actual_solar_kwp * 1000 * p["capex_wp"]
    capex_wind  = wind_kw * 1000 * 1.20   # USD/kW for onshore wind
    total_capex = capex_solar + capex_wind + bess_capex

    tariff_usd = (tariff_cents / 100) if tariff_cents else estimate_tariff(lat, lon)
    wacc       = (wacc_pct or 7.0)
    life       = int(life_yrs or 25)

    annual_opex   = total_capex * 0.010         # 1% of CAPEX
    year1_revenue = annual_gen_kwh * tariff_usd
    year1_net     = year1_revenue - annual_opex

    # Build cashflows with degradation
    cashflows = [-total_capex]
    for yr in range(1, life + 1):
        gen_yr  = annual_gen_kwh * ((1 - degradation) ** (yr - 1))
        rev_yr  = gen_yr * tariff_usd
        opex_yr = annual_opex * (1.02 ** (yr - 1))   # 2% opex inflation
        cashflows.append(rev_yr - opex_yr)

    npv_val    = npv_calc(cashflows[1:], wacc) - total_capex
    irr_val    = irr_calc(cashflows)
    payback    = total_capex / year1_net if year1_net > 0 else 99

    # LCOE
    total_gen_lifetime = sum(annual_gen_kwh * ((1 - degradation) ** yr) for yr in range(life))
    total_cost_pv      = total_capex + npv_calc([annual_opex * (1.02 ** yr) for yr in range(life)], wacc)
    lcoe_usd_mwh       = (total_cost_pv / total_gen_lifetime * 1000) if total_gen_lifetime > 0 else 0

    # CAPEX breakdown %
    cb = {}
    if total_capex > 0:
        cb["modules"]      = round(capex_solar * 0.38 / total_capex * 100, 1)
        cb["inverters"]    = round(capex_solar * 0.12 / total_capex * 100, 1)
        cb["mounting"]     = round(capex_solar * 0.18 / total_capex * 100, 1)
        cb["bos_elec"]     = round(capex_solar * 0.15 / total_capex * 100, 1)
        cb["epc"]          = round(capex_solar * 0.10 / total_capex * 100, 1)
        cb["contingency"]  = round(100 - cb["modules"] - cb["inverters"] - cb["mounting"] - cb["bos_elec"] - cb["epc"], 1)

    # ── Sustainability ────────────────────────────────────────────────────────
    emission_factor     = estimate_grid_emission_factor(lat, lon)
    co2_annual          = annual_gen_kwh * emission_factor / 1000   # tonnes
    co2_lifetime        = co2_annual * life
    households          = int(annual_gen_kwh / 4000)                  # avg 4 MWh/yr per household

    # ── Wind specs ────────────────────────────────────────────────────────────
    if wind_kw > 0:
        turbine_kw  = 3000 if wind_kw > 10000 else (1500 if wind_kw > 2000 else 500)
        num_turbines = max(1, math.ceil(wind_kw / turbine_kw))
        hub_height  = 100 if turbine_kw >= 3000 else (80 if turbine_kw >= 1500 else 55)
        rotor_d     = 126 if turbine_kw >= 3000 else (90 if turbine_kw >= 1500 else 54)
    else:
        turbine_kw = num_turbines = hub_height = rotor_d = 0

    # ── Climate assessment ────────────────────────────────────────────────────
    if psh >= 5.5:
        solar_suit = f"Excellent — GHI of {psh:.2f} kWh/m²/day is well above the global solar project threshold of 4.5"
    elif psh >= 4.5:
        solar_suit = f"Good — GHI of {psh:.2f} kWh/m²/day supports viable solar PV with competitive LCOE"
    elif psh >= 3.5:
        solar_suit = f"Moderate — GHI of {psh:.2f} kWh/m²/day is workable but will result in higher LCOE than solar-rich regions"
    else:
        solar_suit = f"Low — GHI of {psh:.2f} kWh/m²/day may favour wind or hybrid over pure solar"

    if wind_50m >= 8.0:
        wind_suit = f"Excellent — {wind_50m} m/s at 50m hub height offers high capacity factors (>35%)"
    elif wind_50m >= 6.5:
        wind_suit = f"Good — {wind_50m} m/s at 50m supports viable onshore wind development"
    elif wind_50m >= 5.0:
        wind_suit = f"Moderate — {wind_50m} m/s is borderline for wind; solar is likely more economic at this site"
    else:
        wind_suit = f"Low — {wind_50m} m/s wind speed makes wind turbines uneconomic at this location"

    temp_diff = temp - 25.0
    if temp_diff > 0:
        temp_note = f"At {temp}°C average, panels operate {temp_diff:.1f}°C above STC. This causes a {abs(temp_diff * 0.35):.1f}% power reduction. TOPCon bifacial modules with low temp coefficient (−0.29%/°C) are recommended to minimise losses."
    else:
        temp_note = f"At {temp}°C average, panels operate near or below STC (25°C), providing a slight efficiency advantage over nameplate ratings."

    return {
        "source": source, "badge": badge,
        "solar_frac": solar_frac, "wind_frac": wind_frac,
        "system_kwp": round(system_kwp, 1),
        "solar_kwp": round(actual_solar_kwp, 1),
        "wind_kw": round(wind_kw, 1),
        "num_panels": num_panels,
        "pv_wp": p["pv_wp"],
        "pv_eff": p["pv_eff"] * 100,
        "pr": round(pr * 100, 1),
        "temp_derating": round((1 - temp_derating) * 100, 2),
        "annual_gen_kwh": round(annual_gen_kwh, 0),
        "annual_gen_mwh": round(annual_gen_kwh / 1000, 1),
        "annual_demand_kwh": round(annual_demand, 0),
        "self_suff": round(self_suff, 1),
        "cap_factor": round(cap_factor, 1),
        "specific_yield": round(specific_yield, 0),
        "land_ha": round(land_ha, 2),
        "land_m2_kwp": p["land_m2_kwp"],
        "dc_ac": p["dc_ac"],
        "inv_kva": round(inv_capacity_kva, 1),
        "inv_units": inv_units,
        "bess_kwh": round(bess_kwh, 1),
        "bess_kw": round(bess_kw, 1),
        "bess_hours": round(bess_kwh / bess_kw, 1) if bess_kw > 0 else 0,
        "bess_capex": round(bess_capex, 0),
        "total_capex": round(total_capex, 0),
        "total_capex_m": round(total_capex / 1_000_000, 2),
        "capex_per_kwp": round(total_capex / system_kwp / 1000, 2) if system_kwp > 0 else 0,
        "annual_opex": round(annual_opex, 0),
        "opex_per_mwh": round(annual_opex / (annual_gen_kwh / 1000), 2) if annual_gen_kwh > 0 else 0,
        "tariff_usd": tariff_usd,
        "year1_revenue": round(year1_revenue, 0),
        "year1_net": round(year1_net, 0),
        "npv": round(npv_val, 0),
        "irr": round(irr_val, 1),
        "payback": round(payback, 1),
        "lcoe": round(lcoe_usd_mwh, 2),
        "wacc": wacc, "life": life,
        "cb": cb,
        "co2_annual": round(co2_annual, 1),
        "co2_lifetime": round(co2_lifetime, 0),
        "households": households,
        "emission_factor": emission_factor,
        "turbine_kw": turbine_kw, "num_turbines": num_turbines,
        "hub_height": hub_height, "rotor_d": rotor_d, "wind_cf": round(wind_cf * 100, 1),
        "solar_suit": solar_suit, "wind_suit": wind_suit, "temp_note": temp_note,
        "op_hours": p["op_hours"],
        "daily_demand": round(daily_demand_kwh, 1),
    }


# ═════════════════════════════════════════════════════════════════════════════
# RESULTS RENDERER
# ═════════════════════════════════════════════════════════════════════════════

def fmt_num(n, decimals=0):
    if n is None:
        return "—"
    if decimals == 0:
        return f"{int(round(n)):,}"
    return f"{round(n, decimals):,.{decimals}f}"

def render(r, climate, location_name, lat, lon, connected_power, power_unit, project_label):
    badge_cls = {"solar":"badge-solar","wind":"badge-wind","hybrid":"badge-hybrid"}.get(r["badge"],"badge-solar")
    st.markdown(f'<span class="badge {badge_cls}">{r["source"]}</span>', unsafe_allow_html=True)

    # Executive summary
    tariff_display = f"{r['tariff_usd']*100:.1f}¢/kWh"
    st.markdown(f"""
Based on NASA POWER climate data for this site (GHI {climate.get('psh','—')} kWh/m²/day, wind {climate.get('wind_50m','—')} m/s at 50m), 
**{r['source']}** is the optimal technology for this {project_label.split()[-1].lower()} project. 
The {fmt_num(r['system_kwp'])} kWp system will generate **{fmt_num(r['annual_gen_mwh'])} MWh/year**, 
covering **{r['self_suff']}%** of the {fmt_num(r['daily_demand'])} kWh/day load. 
At the estimated grid tariff of {tariff_display}, the project achieves a **{r['payback']} year payback** 
with a **{r['irr']}% IRR** over {r['life']} years.
    """)

    # Climate assessment
    st.markdown("**☀️ Solar suitability:** " + r["solar_suit"])
    st.markdown("**💨 Wind suitability:** " + r["wind_suit"])
    st.markdown("**🌡️ Temperature impact:** " + r["temp_note"])

    # KPI metrics
    st.divider()
    k = st.columns(4)
    k[0].metric("Renewable capacity",  f"{fmt_num(r['system_kwp'])} kWp")
    k[1].metric("Annual generation",   f"{fmt_num(r['annual_gen_mwh'])} MWh/yr")
    k[2].metric("Self-sufficiency",    f"{r['self_suff']}%")
    k[3].metric("Capacity factor",     f"{r['cap_factor']}%")
    k = st.columns(4)
    k[0].metric("Total CAPEX",         f"USD {fmt_num(r['total_capex_m'], 2)}M")
    k[1].metric("CAPEX per kWp",       f"${fmt_num(r['capex_per_kwp'], 2)}/Wp")
    k[2].metric("LCOE",                f"${fmt_num(r['lcoe'], 1)}/MWh")
    k[3].metric("Project IRR",         f"{r['irr']}%")
    k = st.columns(4)
    k[0].metric("Simple payback",      f"{r['payback']} years")
    k[1].metric("NPV ({r['life']} yr)",f"USD {fmt_num(r['npv']/1_000_000, 2)}M")
    k[2].metric("CO₂ offset / year",   f"{fmt_num(r['co2_annual'])} tonnes")
    k[3].metric("Land required",       f"{fmt_num(r['land_ha'], 2)} ha")

    # Technical specs
    st.divider()
    st.subheader("Technical specifications")

    col1, col2 = st.columns(2)

    with col1:
        with st.expander("☀️ Solar PV specifications", expanded=True):
            panel_tech = "TOPCon Bifacial N-type" if r["pv_wp"] >= 570 else "Monocrystalline PERC"
            tracker = "Single-axis tracker (SAT)" if r["system_kwp"] > 500 else "Fixed-tilt ground mount"
            tilt = "Tracking (0°–55° E-W)" if "SAT" in tracker else f"{abs(round(lat)):.0f}° fixed tilt"
            rows = [
                ("Module technology",       panel_tech),
                ("Module wattage",          f"{r['pv_wp']} Wp"),
                ("Module efficiency",       f"{r['pv_eff']:.1f}%"),
                ("Total modules",           f"{fmt_num(r['num_panels'])} panels"),
                ("Total solar capacity",    f"{fmt_num(r['solar_kwp'], 1)} kWp"),
                ("Mounting system",         tracker),
                ("Tilt / tracking",         tilt),
                ("Performance ratio (PR)",  f"{r['pr']}%"),
                ("Temp. derating",          f"−{r['temp_derating']}% from STC"),
                ("Specific yield",          f"{fmt_num(r['specific_yield'])} kWh/kWp/yr"),
                ("Land use efficiency",     f"{r['land_m2_kwp']} m²/kWp"),
            ]
            st.markdown("<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a,b in rows) + "</table>", unsafe_allow_html=True)

        if r["bess_kwh"] > 0:
            with st.expander("🔋 Battery storage (BESS)", expanded=True):
                rows = [
                    ("Battery chemistry",     "LFP (Lithium Iron Phosphate)"),
                    ("Total capacity",        f"{fmt_num(r['bess_kwh'], 1)} kWh"),
                    ("Power rating",          f"{fmt_num(r['bess_kw'], 1)} kW"),
                    ("Duration",              f"{r['bess_hours']} hours"),
                    ("Round-trip efficiency", "92–95%"),
                    ("Cycle life",            "4,000–6,000 cycles"),
                    ("Warranty",              "10 years / 70% capacity"),
                    ("BESS CAPEX",            f"USD {fmt_num(r['bess_capex']/1_000_000, 2)}M"),
                ]
                st.markdown("<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a,b in rows) + "</table>", unsafe_allow_html=True)

    with col2:
        with st.expander("⚙️ Inverter & power conversion", expanded=True):
            inv_type = "Central inverter station (1500 Vdc)" if r["system_kwp"] > 1000 else "String inverter (1000 Vdc)"
            rows = [
                ("Inverter type",           inv_type),
                ("Total inverter capacity", f"{fmt_num(r['inv_kva'], 1)} kVA"),
                ("Number of units",         f"{r['inv_units']}"),
                ("DC/AC ratio",             f"{r['dc_ac']}"),
                ("Inverter efficiency",     "98.5%"),
                ("MPPT channels",           "Multi-MPPT per unit"),
            ]
            st.markdown("<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a,b in rows) + "</table>", unsafe_allow_html=True)

        if r["wind_kw"] > 0:
            with st.expander("💨 Wind turbine specifications", expanded=True):
                rows = [
                    ("Turbine class",         f"IEC Class {'I' if r['hub_height'] >= 100 else 'II'}"),
                    ("Rated power per turbine",f"{fmt_num(r['turbine_kw'])} kW"),
                    ("Number of turbines",    f"{r['num_turbines']}"),
                    ("Hub height",            f"{r['hub_height']} m"),
                    ("Rotor diameter",        f"{r['rotor_d']} m"),
                    ("Estimated capacity factor", f"{r['wind_cf']}%"),
                    ("Min. turbine spacing",  f"5–7 rotor diameters"),
                ]
                st.markdown("<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a,b in rows) + "</table>", unsafe_allow_html=True)

        with st.expander("🔌 Grid & balance of system", expanded=True):
            col_v = 33 if r["system_kwp"] < 1000 else (132 if r["system_kwp"] < 50000 else 220)
            rows = [
                ("Internal collection voltage", f"{col_v} kV"),
                ("Grid connection type",    "Grid-connected" if r["bess_hours"] == 0 else "Hybrid"),
                ("Operating hours assumed", f"{r['op_hours']} hrs/day"),
                ("Daily demand served",     f"{fmt_num(r['daily_demand'])} kWh/day"),
                ("Annual demand",           f"{fmt_num(r['annual_demand_kwh']/1000, 1)} MWh/yr"),
                ("Grid export",             "Excess generation exported to grid" if r["self_suff"] < 100 else "Fully self-consumed"),
            ]
            st.markdown("<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a,b in rows) + "</table>", unsafe_allow_html=True)

    # Financial analysis
    st.divider()
    st.subheader("Financial analysis")

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("💰 Capital cost breakdown", expanded=True):
            cb = r["cb"]
            rows = [
                ("Total CAPEX",             f"USD {fmt_num(r['total_capex_m'], 2)}M"),
                ("CAPEX per kWp",           f"${r['capex_per_kwp']:.2f}/Wp"),
                ("  — Modules / turbines",  f"{cb.get('modules',0)}% of CAPEX"),
                ("  — Inverters",           f"{cb.get('inverters',0)}%"),
                ("  — Mounting & civil",    f"{cb.get('mounting',0)}%"),
                ("  — BOS & electrical",    f"{cb.get('bos_elec',0)}%"),
                ("  — EPC overhead",        f"{cb.get('epc',0)}%"),
                ("  — Contingency",         f"{cb.get('contingency',0)}%"),
                ("BESS cost (if any)",      f"USD {fmt_num(r['bess_capex']/1_000_000, 2)}M"),
            ]
            st.markdown("<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a,b in rows) + "</table>", unsafe_allow_html=True)

    with col2:
        with st.expander("📈 Financial returns", expanded=True):
            rows = [
                ("Grid tariff assumed",     f"${r['tariff_usd']*100:.1f}¢/kWh"),
                ("Year-1 revenue",          f"USD {fmt_num(r['year1_revenue']/1_000_000, 2)}M"),
                ("Annual O&M cost",         f"USD {fmt_num(r['annual_opex']/1_000_000, 3)}M/yr"),
                ("O&M per MWh",             f"${r['opex_per_mwh']:.2f}/MWh"),
                ("Year-1 net income",       f"USD {fmt_num(r['year1_net']/1_000_000, 2)}M"),
                ("LCOE",                    f"${r['lcoe']:.1f}/MWh"),
                ("Simple payback",          f"{r['payback']} years"),
                ("Project IRR",             f"{r['irr']}%"),
                (f"NPV ({r['life']} yr, {r['wacc']}% WACC)", f"USD {fmt_num(r['npv']/1_000_000, 2)}M"),
            ]
            st.markdown("<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a,b in rows) + "</table>", unsafe_allow_html=True)

    # Sustainability
    st.divider()
    st.subheader("Sustainability & environmental impact")
    k = st.columns(4)
    k[0].metric("CO₂ offset / year",    f"{fmt_num(r['co2_annual'])} tonnes")
    k[1].metric("Lifetime CO₂ offset",  f"{fmt_num(r['co2_lifetime'])} tonnes")
    k[2].metric("Households powered",   f"{fmt_num(r['households'])}")
    k[3].metric("Grid emission factor", f"{r['emission_factor']} kgCO₂/kWh")
    st.caption(f"Water: Dry-cleaning recommended in arid climates to minimise water consumption. Estimated < 0.05 m³/MWh.")
    st.caption(f"SDG alignment: SDG 7 (Affordable & Clean Energy)  ·  SDG 13 (Climate Action)  ·  SDG 11 (Sustainable Cities)")

    # Risks & next steps
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Key risks")
        risks = [
            f"☀️ **Soiling losses** — desert/arid sites require frequent panel cleaning (every 2–4 weeks) to maintain PR above {r['pr']-3}%",
            f"🌡️ **Temperature derating** — at {climate.get('temp','—')}°C average, high-temperature days may reduce output by up to 8–12% vs nameplate",
            "📋 **Grid curtailment** — utility may limit export during low-demand periods; BESS or load management should be considered",
            "💰 **Tariff risk** — revenue depends on sustained offtake agreement; merchant exposure increases project risk",
            "🏗️ **EPC delivery risk** — supply chain for modules and inverters should be secured 12–18 months before COD",
        ]
        for risk in risks:
            st.markdown(f'<p class="bullet">{risk}</p>', unsafe_allow_html=True)

    with c2:
        st.subheader("Mitigations")
        mits = [
            "Install automated dry-cleaning robots or anti-soiling coating on modules",
            f"Specify modules with temp. coefficient better than −0.30%/°C; prefer TOPCon over PERC in climates above {climate.get('temp',25)}°C",
            "Include grid code compliance study and active power control in inverter spec",
            "Secure long-term PPA or government feed-in tariff before financial close",
            "Place equipment orders with 20% deposit upon EPC contract signature",
        ]
        for m in mits:
            st.markdown(f'<p class="bullet">• {m}</p>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Recommended next steps")
    steps = [
        f"**1.** Commission a **bankable solar resource assessment** (P50/P90) from a certified energy assessor using satellite data for {location_name}",
        f"**2.** Conduct a **grid connection feasibility study** with the local utility — confirm available capacity at {33 if r['system_kwp'] < 1000 else 132} kV",
        f"**3.** Engage an EPC contractor for a **pre-FEED study** to validate land requirements ({fmt_num(r['land_ha'], 1)} ha) and civil conditions",
        f"**4.** Initiate **permitting and environmental impact assessment (EIA)** — typical timeline 6–18 months depending on jurisdiction",
        f"**5.** Develop a **financial model** for lender presentation including P90 generation scenario, debt sizing, and DSCR analysis at {r['wacc']}% WACC",
    ]
    for step in steps:
        st.markdown(f'<p class="bullet">{step}</p>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
if go:
    if not coord_input:
        st.error("Please enter a project location.")
        st.stop()
    if not connected_power:
        st.error("Please enter the total connected power.")
        st.stop()

    with st.status("Running SP Optimizer...", expanded=True) as status:

        # Resolve location
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
                st.error(f"Could not find '{coord_input}'. Try decimal coordinates: 25.2048, 55.2708")
                st.stop()
            lat, lon = result
            location_name = coord_input
        st.write(f"✅ **{location_name}** — {lat:.4f}°N, {lon:.4f}°E")

        # Fetch NASA POWER
        st.write("🛰️ Fetching climate data from NASA POWER API...")
        climate = fetch_nasa_power(lat, lon)
        if "error" in climate:
            status.update(label="NASA API error", state="error")
            st.error(f"NASA POWER error: {climate['error']}. Try again shortly.")
            st.stop()
        st.write(f"✅ GHI: {climate.get('ghi_daily','—')} kWh/m²/day  ·  Wind @50m: {climate.get('wind_50m','—')} m/s  ·  Temp: {climate.get('temp','—')}°C")

        # Run calculations
        st.write("⚙️ Running engineering calculations...")
        ptype = PROJECT_TYPES[project_label]
        connected_kw = to_kw(connected_power, power_unit)

        result = calculate(
            connected_kw=connected_kw,
            ptype=ptype,
            climate=climate,
            grid_type=grid_type,
            oversizing_factor=oversizing,
            tariff_cents=tariff,
            wacc_pct=wacc,
            life_yrs=lifetime,
            degradation_pct=degradation,
            lat=lat,
            lon=lon,
        )
        st.write("✅ Calculations complete")
        status.update(label="Report ready ✅", state="complete", expanded=False)

    # Show climate data
    st.divider()
    st.subheader(f"📍 {location_name}")
    st.caption(f"Lat {lat:.4f}°, Lon {lon:.4f}°  ·  Connected load: {connected_power:,.1f} {power_unit}  ·  {project_label}")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Daily GHI",       f"{climate.get('ghi_daily','—')}", "kWh/m²/day")
    c2.metric("Annual GHI",      f"{climate.get('ghi_annual','—')}", "kWh/m²/yr")
    c3.metric("Peak sun hours",  f"{climate.get('psh','—')}", "hrs/day")
    c4.metric("Wind @ 50m",      f"{climate.get('wind_50m','—')}", "m/s")
    c5.metric("Avg temperature", f"{climate.get('temp','—')}", "°C")
    c6.metric("Avg humidity",    f"{climate.get('humidity','—')}", "%")
    st.markdown('<p class="source-note">NASA POWER Climatology API — 22-year climatological average (2001–2022)</p>', unsafe_allow_html=True)

    st.divider()
    render(result, climate, location_name, lat, lon, connected_power, power_unit, project_label)

    # Download
    full_report = {
        "project": project_label,
        "location": location_name,
        "lat": lat, "lon": lon,
        "connected_power": f"{connected_power} {power_unit}",
        "climate_data": climate,
        "system_results": result,
    }
    st.download_button(
        "⬇ Download full report (JSON)",
        data=json.dumps(full_report, indent=2, default=str),
        file_name="sp_optimizer_report.json",
        mime="application/json",
    )
