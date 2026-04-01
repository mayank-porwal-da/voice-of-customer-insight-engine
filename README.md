# 📊 VoC Insight Engine

AI-powered platform to transform raw customer reviews into actionable product insights and engineering decisions.

![Python](https://img.shields.io/badge/Python-3.13.6-3776ab?style=flat-square)
![Status](https://img.shields.io/badge/Status-Production%20Ready-green?style=flat-square)

![App Demo](Demo%20to%20Dashboard.png)

**[🚀 Try Live Demo](https://voice-of-customer-insight-engine.streamlit.app/)**

## Overview

VoC Insight Engine uses a dual-agent AI architecture to analyze customer feedback at scale. It extracts sentiment, identifies product issues, and generates structured action plans—reducing analysis time from hours to seconds.

## Features

- Automated review analysis (sentiment, flaws, strengths)
- AI-generated engineering action plans
- Multi-product support from single dataset
- Interactive dashboard with trends
- Smart caching for instant reloads
- Flexible API key input (user or `.env`)

## Architecture

```
CSV Upload → Validation → Product Selection → Dashboard
    ↓
AI Pipeline:
├─ Agent 1: Insight Extraction (JSON)
└─ Agent 2: Action Plan Generation (Markdown)
    ↓
Cached Results → UI Display
```

## Quick Start

### Setup
```bash
git clone <repo-url>
cd <project-folder>

python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### Configure API Key
```bash
echo "GEMINI_API_KEY=your_api_key" > .env
```

### Run
```bash
streamlit run app.py
```
Open: `http://localhost:8501`

## Usage

1. Upload CSV with `product_name`, `rating`, `review_text`
2. Select product from dropdown
3. View dashboard analytics
4. Click "Generate AI Insights" for sentiment & action plan
5. Results cached for instant reload on product switch

## Testing
```bash
pytest test_for_app.py -v
```
## Configuration

```bash
GEMINI_API_KEY=your_api_key
```
## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| Backend | Python 3.13.6+ |
| AI Engine | Google Gemini API |
| Data | Pandas, Plotly |

## Performance

- First analysis: ~15–20 seconds
- Cached results: <1 second
- Supports 10,000+ reviews per session

## Use Cases

- Product feedback analysis
- Feature prioritization
- Customer sentiment tracking
- Data-driven product decisions

## Roadmap

- Database integration
- Historical trend analysis
- PDF/PPT report export
- Multi-user support

## Support & Feedback

- 📧 **Issues**: Report bugs via GitHub Issues
- 💬 **Discussions**: Share ideas in Discussions tab
- 🚀 **Live App**: Test features at [Streamlit Cloud](https://voice-of-customer-insight-engine.streamlit.app/)

---