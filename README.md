# ⚡ Renewable Energy Project Advisor

An AI-powered Streamlit app that takes project parameters as input and generates a full technical and financial specification — covering all major project types and energy sources.

## Features
- 10 project types: Utility-scale IPP, C&I, Residential, Off-grid, Municipal, Agri-PV, Industrial, EV, Data Center, Mixed-use
- All energy sources: Solar PV, Wind, Hybrid, BESS, Hydro, Green Hydrogen
- Full technical specs: module technology, inverter topology, BESS sizing, grid infra
- Financial analysis: CAPEX breakdown, LCOE, IRR, NPV, payback, DSCR
- Sustainability: CO₂ offset, SDG alignment, biodiversity risk
- Export full report as JSON

## Quick start (local)

```bash
git clone https://github.com/YOUR_USERNAME/renewable-energy-advisor.git
cd renewable-energy-advisor
pip install -r requirements.txt
# Add your key to .streamlit/secrets.toml
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push repo to GitHub
2. Go to share.streamlit.io → New app → select repo → app.py
3. Advanced settings → Secrets → add:
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
4. Deploy ✅

## Get an API key
Sign up at console.anthropic.com
