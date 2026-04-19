# ⚡ SP Optimizer — UAE Edition

A free, fully self-contained renewable energy system design tool built for the UAE market. Enter a connected load and project location — the app fetches live climate data from NASA, sizes the optimal system, and generates a professional PDF report in AED.

**No API key. No subscription. No cost. Unlimited use.**

---

## Live demo

🔗 [sp-optimizer-guhyxh7q5j24qo5xf7brj6.streamlit.app](https://sp-optimizer-guhyxh7q5j24qo5xf7brj6.streamlit.app)

---

## What it does

Two required inputs — **connected load** and **location** — and the app does everything else:

1. Geocodes the location and fetches **22-year climatological averages** from NASA POWER (GHI, PSH, wind speed, temperature, humidity, clearness index)
2. Cross-checks solar yield with **PVGIS EU JRC** (independent yield verification using actual system size)
3. Runs **dual-mode engineering calculations**: size system to cover the load (Mode A) or size system to fit a space constraint (Mode B)
4. Generates a **professional PDF report** with 8+ sections

---

## Features

### 🇦🇪 UAE-specific
- Tariffs auto-filled from **DEWA, SEWA, FEWA, ADDC/AADC** (2024 rates, fils/kWh)
- Grid emission factor from **DEWA Clean Energy Report 2023** (0.341 kgCO₂/kWh)
- Next steps tailored to correct utility portal (Shams Dubai, sewa.gov.ae, FEWA, ADDC)
- UAE Net Zero 2050 and SDG alignment

### 📐 Dual-mode area calculation
- **Mode A — Load-constrained**: sizes system to cover full demand → shows area required
- **Mode B — Area-constrained**: sizes system to fit your space → shows load coverage %
- Full GCR, setback, and land buffer breakdown
- Row spacing calculated from latitude and tilt angle (no shading on winter solstice)

### 📉 IEC 61724 loss tree
Explicit, traceable PR breakdown:
- Temperature derating (NASA monthly temps × module temp coefficient)
- Soiling (user input)
- Inverter efficiency
- DC wiring losses (1.5%)
- AC wiring losses (1.0%)
- Module mismatch / LID (2.0%)
- Availability (1.0%)
- Azimuth derate
- Tracker / mounting gain
- Bifacial / albedo gain

### ⚙️ Inverter sizing engine
Auto-selects inverter type and quantity based on DC capacity:
- ≤30 kWp → Microinverter
- 30–100 kWp → String inverter (15–25 kW units)
- 100–500 kWp → String inverter (50–100 kW units)
- 500–2,000 kWp → Central inverter (500 kW, 1000 Vdc)
- >2,000 kWp → Central inverter station (3.4 MW, 1500 Vdc)

Includes DC/AC ratio (1.25), modules per string from temperature-corrected Voc, and MPPT window check.

### 📊 P50 / P90 yield estimate
Based on ±4% interannual variability (NASA POWER Middle East validation):
- P50 = median expected annual yield
- P90 = conservative estimate (10th percentile)
- Lifetime P50 and P90 over project life
- Clear note that formal bankable P90 requires certified assessor

### 📈 Sensitivity analysis
7 scenarios automatically run:
- Base case
- Tariff +15% / −15%
- Soiling +3% (no cleaning)
- CAPEX +15% (cost overrun)
- High degradation (0.8%/yr)
- P90 yield (−5.1%)

### 🔍 Sanity checks
4 engineering guards with green/amber/red status:
- Specific yield (valid: 1,200–2,200 kWh/kWp/yr)
- Capacity factor (valid: 10–35%)
- Performance ratio (valid: 70–90%)
- CAPEX per Wp (valid: AED 2.0–7.0/Wp)

### 🏆 Bankability score (0–100)
Scores 13 components across 4 categories:
- Climate data quality (NASA + PVGIS + monthly breakdown) — 25 pts
- System design completeness (sanity + inverter + loss tree) — 25 pts
- Financial model quality (IRR/NPV + P50/P90 + sensitivity + DSCR) — 25 pts
- Site information (area + row spacing + tariff) — 25 pts

Grades: A (≥85 bankable), B (≥70 investment-grade), C (≥55 concept), D (<55 incomplete)

### 📅 Monthly solar resource & generation
12-month breakdown from NASA POWER showing GHI, clearness index, temperature, wind, temperature derating, generation (MWh), and capacity factor per month.

### 10 project types
Utility-scale IPP · Commercial & Industrial · Residential/Community · Remote/Off-grid · Municipal/Public · Agri-PV · Industrial Process · EV Charging · Data Center · Mixed-use

### 5 PV module technologies
Monocrystalline PERC 440Wp · TOPCon 580Wp · Bifacial TOPCon 600Wp · HJT 650Wp · CdTe Thin Film 150Wp

### 8 mounting systems
Fixed tilt · Single-axis tracker · Dual-axis tracker · Flat roof ballasted · Pitched roof · Carport · Agri-PV · Floating PV

### ⚡ What can you run daily
Appliance load calculator for Home (15 appliances), Office (15 appliances), and Industrial (15 appliances) contexts — shows how many of each appliance the daily generation can power.

### 📄 Professional PDF report (9 sections)
1. Cover page with bankability score
2. Required site area (area-constrained or load-constrained breakdown)
3. Key performance indicators — 12 KPIs
4. Climate & solar resource data (NASA + PVGIS)
5. Monthly solar resource & generation forecast (all 12 months)
5b. Performance ratio loss tree (IEC 61724)
5c. Electrical design, P50/P90, sensitivity analysis, sanity checks
6. Technical specifications
6b. What can you run daily (all 3 contexts)
7. Risks & mitigations
8. Recommended next steps

---

## Data sources

| Source | What it provides | Cost |
|---|---|---|
| [NASA POWER API](https://power.larc.nasa.gov) | GHI, wind, temperature, humidity, Kt — 22-year avg | Free |
| [PVGIS EU JRC](https://re.jrc.ec.europa.eu/pvg_tools/) | Independent solar yield cross-check | Free |
| [OpenStreetMap / Nominatim](https://nominatim.org) | Geocoding (city name → coordinates) | Free |
| DEWA / SEWA / FEWA / ADDC | UAE electricity tariff rates 2024 | Built-in |

---

## Quick start (local)

**Requirements: Python 3.10+**

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/sp-optimizer.git
cd sp-optimizer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`. No configuration needed — all APIs are public and free.

---

## Deploy to Streamlit Cloud (free)

1. Fork or push this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select your repo → set main file to `app.py`
4. Click **Deploy** ✅

No secrets to configure. The app runs entirely on free public APIs.

---

## Requirements

```
streamlit>=1.32.0      # Web UI framework
requests>=2.31.0       # NASA POWER + PVGIS + OpenStreetMap API calls
reportlab>=4.0.0       # PDF report generation
arabic-reshaper>=3.0.0 # Arabic text shaping for PDF (UAE place names)
python-bidi>=0.4.2     # RTL text rendering for PDF
pandas>=2.0.0          # Monthly table and sensitivity dataframes
```

Standard library only (no numpy needed): `math`, `io`, `json`, `datetime`

---

## How the calculations work

### Energy yield
```
NASA formula:  E = act_kwp × PSH × 365 × PR
PVGIS:         E = PVGIS API yield (fetched with actual system kWp)
Used:          PVGIS when available, NASA as fallback
```

### Performance ratio (IEC 61724 loss tree)
```
PR = (1-temp_loss) × (1-soiling) × inv_eff × (1-dc_wiring)
   × (1-ac_wiring) × (1-mismatch) × (1-availability)
   × (1-azimuth_derate) × tracker_boost × (1+bifacial_gain)
```

### Area calculation (dual mode)
```
Mode A (Load → Area):
  min_kwp   = daily_demand / (PSH × PR)
  sys_kwp   = min_kwp × oversizing
  panel_m2  = num_panels × (Wp/1000/eff)
  array_m2  = panel_m2 / GCR
  site_m2   = array_m2 / ((1-setback%) / land_buffer)

Mode B (Area → System):
  usable_m2  = avail_m2 × (1-setback%)
  array_m2   = usable_m2 / land_buffer
  panel_m2   = array_m2 × GCR
  num_panels = floor(panel_m2 / m2_per_panel)
  act_kwp    = num_panels × Wp / 1000
```

### Row spacing (no shading)
```
solar_elevation = arcsin(sin(lat) × sin(dec) + cos(lat) × cos(dec))
panel_height    = sin(tilt) × panel_length
row_spacing     = panel_height / tan(solar_elevation) + panel_length × cos(tilt)
GCR             = panel_length / row_spacing
```

### Wind capacity factor (Rayleigh distribution)
```
v_hub    = v50 × (100/50)^0.14          # wind shear extrapolation to 100m
c_ray    = v_hub / 0.8862               # Rayleigh scale parameter
CF       = ∫[cut-in to rated] P(v) × f(v) dv + P(above rated)
           (12-segment numerical integration)
```

### Financial model
```
Cashflows:  CF_yr = gen × (1-degr)^(yr-1) × tariff - opex × 1.025^(yr-1)
IRR:        bisection on cashflow series (300 iterations, 1e-7 tolerance)
NPV:        discounted at WACC over project lifetime
LCOE:       PV(all costs) / PV(all generation) × 1000  [AED/MWh]
DSCR:       year-1 net cashflow / annual debt service
P90:        P50 × (1 - 1.28 × σ),  σ = 4% (NASA Middle East validation)
```

---

## Project structure

```
sp-optimizer/
├── app.py              # Main Streamlit application (~2,500 lines)
├── requirements.txt    # Python dependencies (6 packages)
├── README.md           # This file
└── .gitignore
```

---

## Known limitations

- **PVGIS coverage**: PVGIS EU JRC covers most of the world but may be unavailable for some offshore or remote coordinates. NASA POWER is used as fallback.
- **Wind assessment**: Wind capacity factor is calculated from Rayleigh distribution — a simplified model. For wind-dominant or hybrid projects, a dedicated wind resource assessment with anemometer data is required.
- **This is pre-feasibility, not detailed design**: Inverter sizing, string configuration, and layout calculations are engineering estimates. A licensed EPC contractor must complete detailed design before procurement.
- **Formal bankable P90**: The P50/P90 estimate uses published NASA POWER interannual variability (±4% for Middle East). A bankable P90 for project finance requires a certified energy assessor using 10+ years of site-specific data.
- **Tariff accuracy**: UAE utility tariffs are embedded as of 2024. Verify current slab rates directly with your utility before financial close.

---

## Built with

- [Streamlit](https://streamlit.io) — web interface
- [ReportLab](https://www.reportlab.com) — PDF generation
- [NASA POWER](https://power.larc.nasa.gov) — climate data
- [PVGIS](https://re.jrc.ec.europa.eu) — solar yield verification
- [OpenStreetMap / Nominatim](https://nominatim.org) — geocoding
