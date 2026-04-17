# ⚡ SP Optimizer — UAE Edition

A free, fully self-contained renewable energy system design tool built for the UAE market. Enter a connected load and project location — the app fetches live climate data from NASA and calculates a complete technical, financial, and environmental specification with a professional PDF report.

**No API key required. No cost. Unlimited use.**

---

## What it does

SP Optimizer takes two required inputs — **connected load** and **location** — and automatically:

1. Fetches 22-year climatological averages from **NASA POWER API** (GHI, wind speed, temperature, humidity, clearness index)
2. Cross-checks solar yield with **PVGIS EU JRC** (independent yield verification)
3. Runs engineering calculations to size the optimal renewable system
4. Generates a **professional PDF report** covering area, technical specs, financials, sustainability, and next steps

---

## Features

### 🇦🇪 UAE-specific
- Tariffs auto-filled from **DEWA, SEWA, FEWA, ADDC/AADC** by emirate and sector (residential / commercial / industrial) in fils/kWh
- Grid emission factor from **DEWA Clean Energy Report 2023** (0.341 kgCO₂/kWh)
- UAE Net Zero 2050 and SDG alignment
- Next steps tailored to the correct utility portal (Shams Dubai, sewa.gov.ae, etc.)

### 📐 Site area calculation
Full breakdown of required implementation area:
- Panel active area (m²)
- Array footprint using Ground Cover Ratio (GCR)
- Total site area including setbacks, access roads, and land buffer
- m²/kWp ratio for quick land assessment
- Feasibility check if you enter an available area

### 📅 Monthly solar resource & generation
12-month breakdown from NASA POWER data showing:
- Monthly GHI (kWh/m²/day and total)
- Clearness index (Kt)
- Average and maximum temperature
- Wind speed at 50m
- Temperature derating per month
- Monthly generation (MWh)
- Monthly capacity factor (%)
- Annual totals and peak/lowest month highlights

### ⚙️ System design customisation
- 5 PV module technologies (PERC, TOPCon, Bifacial TOPCon, HJT, CdTe)
- 8 mounting systems (fixed tilt, SAT, DAT, flat roof, pitched roof, carport, agri-PV, floating)
- 4 inverter types (string, central, large central, microinverter)
- Oversizing factor, tilt angle, azimuth, soiling loss, ground albedo
- BESS chemistry and duration override
- Debt/equity split, interest rate, WACC, project lifetime, degradation rate
- Carbon price in AED/tonne
- Net metering toggle
- Local content requirement

### 10 project types
Utility-scale IPP · Commercial & Industrial · Residential/Community · Remote/Off-grid · Municipal/Public · Agri-PV · Industrial Process · EV Charging · Data Center · Mixed-use Development

### 📄 Professional PDF report (8 sections)
1. Cover page with project summary
2. Required site area — highlighted hero card + detailed breakdown table
3. Key performance indicators — 12 KPIs in a grid
4. Climate & solar resource data (NASA POWER + PVGIS)
5. Monthly solar resource & generation forecast (all 12 months)
6. Technical specifications (PV, BESS, inverter)
7. Financial analysis in AED (CAPEX breakdown, IRR, NPV, LCOE, DSCR)
8. Sustainability metrics, risks & mitigations, next steps

---

## Data sources

| Source | What it provides | Cost |
|---|---|---|
| [NASA POWER API](https://power.larc.nasa.gov) | GHI, wind, temperature, humidity — 22-year avg | Free |
| [PVGIS EU JRC](https://re.jrc.ec.europa.eu/pvg_tools/) | Independent solar yield cross-check | Free |
| [OpenStreetMap / Nominatim](https://nominatim.org) | Geocoding and reverse geocoding | Free |
| DEWA / SEWA / FEWA / ADDC | UAE electricity tariff rates 2024 | Built-in |

---

## Quick start (local)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/sp-optimizer.git
cd sp-optimizer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

No secrets or API keys needed — just run it.

---

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo, set main file to `app.py`
4. Click **Deploy** ✅

No secrets to configure — the app runs entirely on free public APIs.

---

## Requirements

```
streamlit>=1.32.0
requests>=2.31.0
reportlab>=4.0.0
arabic-reshaper>=3.0.0
python-bidi>=0.4.2
pandas>=2.0.0
```

All free and open-source. `arabic-reshaper` and `python-bidi` handle correct rendering of Arabic place names in the PDF report.

---

## Project structure

```
sp-optimizer/
├── app.py              # Main Streamlit application (~1,400 lines)
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .gitignore
```

---

## How the calculations work

| Calculation | Method |
|---|---|
| System capacity (kWp) | Daily demand ÷ (PSH × Performance Ratio) × oversizing |
| Performance ratio | Temp derating × soiling × inverter efficiency × wiring × azimuth × tracker boost |
| Temperature derating | NASA monthly temp × module temp coefficient (-0.29%/°C for TOPCon) |
| Annual generation | System kWp × PSH × 365 × PR (overridden by PVGIS if available) |
| Monthly generation | System kWp × monthly GHI × monthly PR |
| LCOE | Discounted lifetime costs ÷ discounted lifetime generation |
| IRR | Bisection method on 25-year cashflow series |
| NPV | Discounted cashflow with 2.5% O&M inflation |
| CO₂ offset | Generation × 0.341 kgCO₂/kWh (DEWA 2023 emission factor) |
| Area required | Panel area ÷ GCR × land buffer ÷ (1 − setback%) |

---

## Built with

- [Streamlit](https://streamlit.io) — web interface
- [ReportLab](https://www.reportlab.com) — PDF generation
- [NASA POWER](https://power.larc.nasa.gov) — climate data
- [PVGIS](https://re.jrc.ec.europa.eu) — solar yield verification
