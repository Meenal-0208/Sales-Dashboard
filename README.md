# 📊 Sales Dashboard (Streamlit + Plotly + TextBlob)

A complete, ready-to-run sales dashboard covering 12 core sales metrics:

1. Leads by Source
2. Pipeline
3. Sales Cycle
4. Closed Opportunities
5. New Business vs. Upsell
6. Win/Loss Rate
7. Product Gaps
8. Open Opportunities
9. Open Activities (calls, demos, visits)
10. Open Cases (with **TextBlob** sentiment analysis on case notes)
11. Opportunities Past Due
12. Sales by Closed Date

The dashboard ships with a synthetic-data generator, so it works immediately —
no external CRM connection required. Swap the CSVs in `data/` with your real
export any time (see **Using Your Own Data** below).

---
## 🌐 Live Demo

**Try the live application here:**

https://sales-dashboard-cq7qxyfck5hgc9nsty8mak.streamlit.app/

## 📁 Project Structure

```
sales_dashboard/
├── app.py                      # Main Streamlit app (all 12 dashboard sections)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── data/
│   ├── generate_data.py        # Synthetic data generator (run once)
│   ├── leads.csv                # generated
│   ├── opportunities.csv        # generated
│   ├── activities.csv           # generated
│   ├── cases.csv                 # generated
│   └── products.csv             # generated
└── utils/
    ├── __init__.py
    └── data_loader.py           # Cached CSV loaders + TextBlob sentiment helper
```

---

## ✅ Prerequisites

- Python 3.9+
- VS Code (with the Python extension) — or any terminal

Check your Python version:
```bash
python --version
```

---

## 🚀 Step-by-Step Setup (VS Code)

### 1. Unzip and open the project
Unzip `sales_dashboard.zip` and open the folder in VS Code:
```bash
File → Open Folder → sales_dashboard
```

### 2. Create a virtual environment (recommended)
Open a terminal in VS Code (`` Ctrl+` `` / `` Cmd+` ``):
```bash
python -m venv venv
```
Activate it:
- **Windows (PowerShell)**: `venv\Scripts\Activate.ps1`
- **Windows (cmd)**: `venv\Scripts\activate.bat`
- **macOS / Linux**: `source venv/bin/activate`

Make sure VS Code is using this interpreter: `Ctrl+Shift+P` → **Python: Select Interpreter** → choose the `venv` one.

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download TextBlob's NLP corpora (one-time, needed for sentiment analysis)
```bash
python -m textblob.download_corpora
```

### 5. Generate the synthetic sales data
```bash
python data/generate_data.py
```
This creates `leads.csv`, `opportunities.csv`, `activities.csv`, `cases.csv`,
and `products.csv` inside `data/`.

### 6. Run the dashboard
```bash
streamlit run app.py
```

### 7. View it in your browser
Streamlit will print a local URL, typically:
```
Local URL: http://localhost:8501
```
It should also open automatically in your default browser. If not, copy/paste
that URL into your browser.

To stop the app, go back to the terminal and press `Ctrl+C`.

---

## 🔄 Using Your Own Data

Replace the generated CSVs in `data/` with your own exports, keeping these
column names (rename/add a mapping step in `utils/data_loader.py` if your
CRM export differs):

| File                 | Required columns |
|----------------------|-------------------|
| `leads.csv`          | `lead_id, lead_name, company, lead_source, created_date, status, converted` |
| `opportunities.csv`  | `opp_id, account_name, owner, product, type, stage, amount, created_date, expected_close_date, actual_close_date, is_closed, is_won` |
| `activities.csv`     | `activity_id, type, related_opp, owner, due_date, status` |
| `cases.csv`          | `case_id, account_name, subject, notes, priority, status, created_date` |
| `products.csv`       | `product, predicted_sales, actual_sales` |

`stage` should use one of: `Prospecting, Qualification, Needs Analysis,
Proposal/Quote, Negotiation, Closed Won, Closed Lost`.

`type` should be one of: `New Business, Upsell`.

Once your CSVs are in place, just re-run `streamlit run app.py` (no need to
run `generate_data.py` again — that script only creates the *demo* data).

---

## 🛠 Tech Stack

- **Streamlit** – dashboard UI framework
- **Plotly** – interactive charts (funnels, gauges, bars, pies, time series)
- **Pandas / NumPy** – data wrangling
- **TextBlob** – NLP sentiment scoring on open-case notes (flags negative-sentiment
  cases that may need urgent attention)
- **Faker** – realistic synthetic names/companies for demo data

---

## 💡 Customization Tips

- **Colors/branding**: edit the `CUSTOM_CSS` block at the top of `app.py`.
- **Filters**: the sidebar currently filters by Owner and Created Date — add
  more `st.sidebar` widgets and matching filter logic near the top of `app.py`.
- **New metrics**: each of the 12 sections is a self-contained block in
  `app.py` — copy a section as a template for additional KPIs.
- **Refresh cached data**: Streamlit caches CSV loads with `@st.cache_data`.
  After changing a CSV, click the "⋮" menu → **Clear cache**, or just restart
  the app.
