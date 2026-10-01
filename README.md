# Bank Complaint Operations Intelligence

[![CI](https://github.com/asif-vm/bank-complaint-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/asif-vm/bank-complaint-intelligence/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An analyst portfolio project that turns consumer complaints into an operations scorecard for identifying response-risk products, recurring issues and underperforming companies.

## Why recruiters should care

The project demonstrates SQL, governed KPI definitions, data validation, root-cause analysis and stakeholder-facing dashboarding. `timely_response_pct` uses the CFPB's published timely-response field; it does not invent resolution-duration data.

## Stack and data

- Python/pandas for cleaning and validation
- DuckDB and SQL for analytical marts
- Streamlit and Plotly for the live dashboard
- GitHub Actions and pytest for CI
- Official, free [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/)

## Run

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
python -m src.pipeline
streamlit run app.py
pytest -q
```

Use `python -m src.pipeline --real` to download the large official extract. The default deterministic dataset lets reviewers run the complete project immediately.

## Architecture

1. Ingest the official extract or generate schema-compatible demo records.
2. Normalize fields and reject duplicate IDs or critical nulls.
3. Create complaint facts and monthly/company SQL marts in DuckDB.
4. Calculate explicitly documented response and dispute KPIs.
5. Serve filters, trends, root causes and company scorecards in Streamlit.

## Resume bullets (replace demo values after the full-data run)

- Engineered a Python and DuckDB pipeline for **[N]+ banking complaints**, enforcing uniqueness and critical-field quality checks before analytics.
- Modelled monthly product and company scorecards in SQL, measuring timely-response and dispute rates across **[N] products and [N] institutions**.
- Delivered an interactive operations dashboard that surfaces complaint trends and top root causes, reducing a defined review workflow from **[before] to [after]**.

## Interview questions

1. **Why is timely response not the same as resolution time?** CFPB provides a timely-response indicator but not a consistent closure timestamp, so the metric is presented as a compliance proxy.
2. **How do you prevent misleading comparisons?** Apply minimum-volume thresholds and show complaint count beside every rate.
3. **Why DuckDB?** It gives reproducible analytical SQL over local files without paid infrastructure and can later be replaced by a warehouse.
