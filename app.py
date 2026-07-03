"""
Sales Dashboard
================
A Streamlit + Plotly sales dashboard covering 12 core sales metrics:
Leads by Source, Pipeline, Sales Cycle, Closed Opportunities,
New Business vs Upsell, Win/Loss Rate, Product Gaps, Open Opportunities,
Open Activities, Open Cases (with TextBlob sentiment), Opportunities
Past Due, and Sales by Closed Date.

Run with:
    streamlit run app.py
"""

import datetime as dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import (
    load_leads, load_opportunities, load_activities,
    load_cases, load_products, data_files_exist,
)

# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.section-title {
    font-size: 1.35rem;
    font-weight: 700;
    margin-top: 1.6rem;
    margin-bottom: 0.4rem;
    border-left: 5px solid #4C6FFF;
    padding-left: 10px;
}
.section-desc {
    color: #666;
    font-size: 0.9rem;
    margin-bottom: 0.8rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Guard: make sure synthetic data has been generated
# ----------------------------------------------------------------------
if not data_files_exist():
    st.error(
        "No data found. Please run `python data/generate_data.py` from the "
        "project root first, then restart the app."
    )
    st.stop()

leads_df = load_leads()
opps_df = load_opportunities()
act_df = load_activities()
cases_df = load_cases()
products_df = load_products()

TODAY = pd.Timestamp(dt.date.today())

# ----------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------
st.sidebar.title("📊 Sales Dashboard")
st.sidebar.caption("Filter data across the whole dashboard")

owners = ["All"] + sorted(opps_df["owner"].unique().tolist())
selected_owner = st.sidebar.selectbox("Sales Owner", owners)

min_date = min(opps_df["created_date"].min(), leads_df["created_date"].min()).date()
max_date = TODAY.date()
date_range = st.sidebar.date_input(
    "Created Date Range", value=(min_date, max_date),
    min_value=min_date, max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date
start_ts, end_ts = pd.Timestamp(start_date), pd.Timestamp(end_date)

# Apply filters
def filt_owner(df, col="owner"):
    if selected_owner != "All" and col in df.columns:
        return df[df[col] == selected_owner]
    return df

opps_f = filt_owner(opps_df)
opps_f = opps_f[(opps_f["created_date"] >= start_ts) & (opps_f["created_date"] <= end_ts)]

leads_f = leads_df[(leads_df["created_date"] >= start_ts) & (leads_df["created_date"] <= end_ts)]

act_f = filt_owner(act_df)

st.sidebar.markdown("---")
st.sidebar.metric("Opportunities in view", len(opps_f))
st.sidebar.metric("Leads in view", len(leads_f))
st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit, Plotly & TextBlob")

# ----------------------------------------------------------------------
# Header + Top KPIs
# ----------------------------------------------------------------------
st.title("Sales Performance Dashboard")
st.caption(f"Data as of {TODAY.date()} • Owner: {selected_owner} • "
           f"Range: {start_date} → {end_date}")

closed_won = opps_f[opps_f["is_won"]]
closed_lost = opps_f[opps_f["is_closed"] & (~opps_f["is_won"])]
open_opps = opps_f[~opps_f["is_closed"]]

total_revenue = closed_won["amount"].sum()
win_rate = (len(closed_won) / max(1, len(closed_won) + len(closed_lost))) * 100
open_pipeline_value = open_opps["amount"].sum()
past_due_count = int(opps_f["past_due"].sum())

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("💰 Closed Revenue", f"${total_revenue:,.0f}")
k2.metric("🏆 Win Rate", f"{win_rate:.1f}%")
k3.metric("📈 Open Pipeline Value", f"${open_pipeline_value:,.0f}")
k4.metric("🧭 Open Opportunities", f"{len(open_opps)}")
k5.metric("⏰ Past Due", f"{past_due_count}",
          delta=None if past_due_count == 0 else "Needs attention",
          delta_color="inverse")

st.markdown("---")

# ========================================================================
# 1. LEADS BY SOURCE
# ========================================================================
st.markdown('<div class="section-title">1. Leads by Source</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Understand where customers come from so you '
    'know which leads to prioritize and whether to diversify sourcing.</div>',
    unsafe_allow_html=True,
)
c1, c2 = st.columns([1.3, 1])
with c1:
    src_counts = leads_f["lead_source"].value_counts().reset_index()
    src_counts.columns = ["lead_source", "count"]
    fig = px.bar(
        src_counts.sort_values("count"), x="count", y="lead_source",
        orientation="h", text="count", color="count",
        color_continuous_scale="Blues",
        labels={"count": "Number of Leads", "lead_source": "Source"},
    )
    fig.update_layout(coloraxis_showscale=False, height=380)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    conv = leads_f.groupby("lead_source")["converted"].mean().reset_index()
    conv["converted"] = (conv["converted"] * 100).round(1)
    fig2 = px.pie(
        leads_f, names="lead_source", title="Lead Source Mix", hole=0.45,
    )
    fig2.update_layout(height=380, showlegend=True)
    st.plotly_chart(fig2, use_container_width=True)

# ========================================================================
# 2. PIPELINE
# ========================================================================
st.markdown('<div class="section-title">2. Pipeline</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">See what stage each open opportunity is in '
    'to tailor conversations — teach vs. pitch.</div>',
    unsafe_allow_html=True,
)
stage_order = ["Prospecting", "Qualification", "Needs Analysis",
               "Proposal/Quote", "Negotiation", "Closed Won", "Closed Lost"]
stage_counts = opps_f["stage"].value_counts().reindex(stage_order).fillna(0)
funnel_df = stage_counts.reset_index()
funnel_df.columns = ["stage", "count"]
funnel_stages = funnel_df[~funnel_df["stage"].isin(["Closed Won", "Closed Lost"])]

fig = go.Figure(go.Funnel(
    y=funnel_stages["stage"], x=funnel_stages["count"],
    textinfo="value+percent initial",
    marker={"color": ["#8ecae6", "#73bfe6", "#5aa8db", "#4a90d9", "#3b6fd6"]},
))
fig.update_layout(height=420, margin=dict(t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# ========================================================================
# 3. SALES CYCLE
# ========================================================================
st.markdown('<div class="section-title">3. Sales Cycle</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Average number of days to win a deal — compare '
    'this to each open opportunity\'s current age to spot stalled deals.</div>',
    unsafe_allow_html=True,
)
won_cycle = closed_won.copy()
won_cycle["cycle_days"] = (won_cycle["actual_close_date"] - won_cycle["created_date"]).dt.days
avg_cycle = won_cycle["cycle_days"].mean() if len(won_cycle) else 0

open_opps_age = open_opps.copy()
open_opps_age["age_days"] = (TODAY - open_opps_age["created_date"]).dt.days
stalled = open_opps_age[open_opps_age["age_days"] > (avg_cycle if avg_cycle else 9999)]

c1, c2, c3 = st.columns(3)
c1.metric("Avg Sales Cycle (Closed Won)", f"{avg_cycle:.0f} days")
c2.metric("Avg Open Opportunity Age", f"{open_opps_age['age_days'].mean():.0f} days" if len(open_opps_age) else "—")
c3.metric("Opportunities Exceeding Avg Cycle", f"{len(stalled)}")

fig = px.histogram(
    won_cycle, x="cycle_days", nbins=25,
    labels={"cycle_days": "Days to Close (Won Deals)"},
    color_discrete_sequence=["#4C6FFF"],
)
fig.add_vline(x=avg_cycle, line_dash="dash", line_color="red",
              annotation_text=f"Avg = {avg_cycle:.0f}d")
fig.update_layout(height=350)
st.plotly_chart(fig, use_container_width=True)

# ========================================================================
# 4. CLOSED OPPORTUNITIES
# ========================================================================
st.markdown('<div class="section-title">4. Closed Opportunities</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Quickly see how much revenue your sales have '
    'generated — key for revenue-based quotas and commission tracking.</div>',
    unsafe_allow_html=True,
)
closed_all = opps_f[opps_f["is_closed"]].copy()
closed_all["close_month"] = closed_all["actual_close_date"].dt.to_period("M").astype(str)
monthly_rev = closed_all[closed_all["is_won"]].groupby("close_month")["amount"].sum().reset_index()

c1, c2 = st.columns([1, 1.4])
with c1:
    st.metric("Total Closed Won Revenue", f"${total_revenue:,.0f}")
    st.metric("Total Closed Won Deals", f"{len(closed_won)}")
    st.metric("Avg Deal Size (Won)", f"${closed_won['amount'].mean():,.0f}" if len(closed_won) else "—")
with c2:
    fig = px.bar(
        monthly_rev, x="close_month", y="amount",
        labels={"close_month": "Month", "amount": "Revenue ($)"},
        color_discrete_sequence=["#2a9d8f"],
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

# ========================================================================
# 5. NEW BUSINESS VS UPSELL
# ========================================================================
st.markdown('<div class="section-title">5. New Business vs. Upsell</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Balance acquiring new customers with growing '
    'existing accounts — upselling is typically far cheaper than new sales.</div>',
    unsafe_allow_html=True,
)
type_rev = closed_won.groupby("type")["amount"].sum().reset_index()
type_count = closed_won.groupby("type").size().reset_index(name="deals")

c1, c2 = st.columns(2)
with c1:
    fig = px.pie(type_rev, names="type", values="amount", hole=0.45,
                 title="Closed Won Revenue Split",
                 color_discrete_sequence=["#4C6FFF", "#F4A261"])
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    closed_all["close_month"] = closed_all["actual_close_date"].dt.to_period("M").astype(str)
    trend = closed_all[closed_all["is_won"]].groupby(["close_month", "type"])["amount"].sum().reset_index()
    fig2 = px.bar(
        trend, x="close_month", y="amount", color="type", barmode="stack",
        labels={"close_month": "Month", "amount": "Revenue ($)"},
        color_discrete_sequence=["#4C6FFF", "#F4A261"],
    )
    fig2.update_layout(height=350)
    st.plotly_chart(fig2, use_container_width=True)

# ========================================================================
# 6. WIN / LOSS RATE
# ========================================================================
st.markdown('<div class="section-title">6. Win/Loss Rate</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">The percent of proposed/quoted opportunities '
    'you won. Track this against industry benchmarks.</div>',
    unsafe_allow_html=True,
)
c1, c2 = st.columns([1, 1.5])
with c1:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=win_rate,
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#4C6FFF"},
            "steps": [
                {"range": [0, 30], "color": "#f8d7da"},
                {"range": [30, 60], "color": "#fff3cd"},
                {"range": [60, 100], "color": "#d4edda"},
            ],
        },
        title={"text": "Win Rate"},
    ))
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    wl_by_owner = opps_f[opps_f["is_closed"]].groupby(["owner", "is_won"]).size().reset_index(name="count")
    wl_by_owner["Result"] = wl_by_owner["is_won"].map({True: "Won", False: "Lost"})
    fig2 = px.bar(
        wl_by_owner, x="owner", y="count", color="Result", barmode="group",
        labels={"owner": "Owner", "count": "Deals"},
        color_discrete_map={"Won": "#2a9d8f", "Lost": "#e76f51"},
    )
    fig2.update_layout(height=320, xaxis_tickangle=-30)
    st.plotly_chart(fig2, use_container_width=True)

# ========================================================================
# 7. PRODUCT GAPS
# ========================================================================
st.markdown('<div class="section-title">7. Product Gaps</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Compare actual product sales vs. predicted/'
    'idealized targets to see where more product research is needed.</div>',
    unsafe_allow_html=True,
)
products_df["gap"] = products_df["actual_sales"] - products_df["predicted_sales"]
products_df["gap_pct"] = (products_df["gap"] / products_df["predicted_sales"] * 100).round(1)

fig = go.Figure()
fig.add_trace(go.Bar(x=products_df["product"], y=products_df["predicted_sales"],
                      name="Predicted", marker_color="#adb5bd"))
fig.add_trace(go.Bar(x=products_df["product"], y=products_df["actual_sales"],
                      name="Actual", marker_color="#4C6FFF"))
fig.update_layout(barmode="group", height=380,
                   yaxis_title="Sales ($)")
st.plotly_chart(fig, use_container_width=True)

gap_display = products_df[["product", "predicted_sales", "actual_sales", "gap", "gap_pct"]].copy()
gap_display.columns = ["Product", "Predicted ($)", "Actual ($)", "Gap ($)", "Gap (%)"]
def _highlight_negative(v):
    return "color: #e76f51; font-weight:600;" if isinstance(v, (int, float)) and v < 0 else ""

try:
    # pandas >= 2.1 uses Styler.map
    styled_gap = gap_display.style.map(_highlight_negative, subset=["Gap ($)", "Gap (%)"])
except AttributeError:
    # older pandas fallback
    styled_gap = gap_display.style.applymap(_highlight_negative, subset=["Gap ($)", "Gap (%)"])

st.dataframe(styled_gap, use_container_width=True, hide_index=True)

# ========================================================================
# 8. OPEN OPPORTUNITIES
# ========================================================================
st.markdown('<div class="section-title">8. Open Opportunities</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Your bread and butter — track, delegate, and '
    'grow the pipeline of opportunities still in play.</div>',
    unsafe_allow_html=True,
)
c1, c2 = st.columns([1, 2])
with c1:
    st.metric("Total Open Opportunities", len(open_opps))
    st.metric("Open Pipeline Value", f"${open_pipeline_value:,.0f}")
    owner_load = open_opps.groupby("owner").size().sort_values(ascending=False)
    if len(owner_load):
        st.caption(f"⚠️ Highest load: **{owner_load.index[0]}** with **{owner_load.iloc[0]}** open opps")
with c2:
    by_owner_stage = open_opps.groupby(["owner", "stage"]).size().reset_index(name="count")
    fig = px.bar(
        by_owner_stage, x="owner", y="count", color="stage", barmode="stack",
        labels={"owner": "Owner", "count": "Open Opportunities"},
    )
    fig.update_layout(height=350, xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

with st.expander("View open opportunities table"):
    st.dataframe(
        open_opps[["opp_id", "account_name", "owner", "product", "stage",
                   "amount", "created_date", "expected_close_date"]]
        .sort_values("expected_close_date"),
        use_container_width=True, hide_index=True,
    )

# ========================================================================
# 9. OPEN ACTIVITIES
# ========================================================================
st.markdown('<div class="section-title">9. Open Activities (Calls, Demos, Visits)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Your to-do list. Good to have open activities, '
    'but too many may mean it\'s time to reprioritize your schedule.</div>',
    unsafe_allow_html=True,
)
open_act = act_f[act_f["status"] == "Open"]
c1, c2 = st.columns([1, 2])
with c1:
    st.metric("Total Open Activities", len(open_act))
    overdue_act = open_act[open_act["due_date"] < TODAY]
    st.metric("Overdue Activities", len(overdue_act), delta_color="inverse")
with c2:
    act_by_type = open_act["type"].value_counts().reset_index()
    act_by_type.columns = ["type", "count"]
    fig = px.bar(act_by_type, x="type", y="count", color="type",
                 labels={"type": "Activity Type", "count": "Open Count"})
    fig.update_layout(height=320, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with st.expander("View open activities table"):
    st.dataframe(
        open_act.sort_values("due_date"),
        use_container_width=True, hide_index=True,
    )

# ========================================================================
# 10. OPEN CASES (with TextBlob sentiment analysis)
# ========================================================================
st.markdown('<div class="section-title">10. Open Cases</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Cases are opened when a customer initiates '
    'contact — treat them as time-sensitive. Sentiment (via TextBlob NLP) '
    'flags which cases may need urgent attention.</div>',
    unsafe_allow_html=True,
)
open_cases = cases_df[cases_df["status"] == "Open"]

c1, c2, c3 = st.columns(3)
c1.metric("Total Open Cases", len(open_cases))
neg_cases = open_cases[open_cases["sentiment_label"] == "Negative"]
c2.metric("Negative Sentiment Cases", len(neg_cases), delta_color="inverse")
crit_cases = open_cases[open_cases["priority"].isin(["High", "Critical"])]
c3.metric("High/Critical Priority Open", len(crit_cases), delta_color="inverse")

c1, c2 = st.columns([1, 1.4])
with c1:
    sent_counts = open_cases["sentiment_label"].value_counts().reset_index()
    sent_counts.columns = ["sentiment", "count"]
    fig = px.pie(
        sent_counts, names="sentiment", values="count", hole=0.5,
        color="sentiment",
        color_discrete_map={"Positive": "#2a9d8f", "Neutral": "#adb5bd", "Negative": "#e76f51"},
    )
    fig.update_layout(height=320, title="Case Sentiment (TextBlob)")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    pri_sent = open_cases.groupby(["priority", "sentiment_label"]).size().reset_index(name="count")
    fig2 = px.bar(
        pri_sent, x="priority", y="count", color="sentiment_label", barmode="stack",
        category_orders={"priority": ["Low", "Medium", "High", "Critical"]},
        color_discrete_map={"Positive": "#2a9d8f", "Neutral": "#adb5bd", "Negative": "#e76f51"},
        labels={"priority": "Priority", "count": "Open Cases", "sentiment_label": "Sentiment"},
    )
    fig2.update_layout(height=320)
    st.plotly_chart(fig2, use_container_width=True)

with st.expander("View open cases with sentiment scores"):
    st.dataframe(
        open_cases[["case_id", "account_name", "subject", "priority",
                    "sentiment_label", "sentiment_polarity", "created_date"]]
        .sort_values("sentiment_polarity"),
        use_container_width=True, hide_index=True,
    )

# ========================================================================
# 11. OPPORTUNITIES PAST DUE
# ========================================================================
st.markdown('<div class="section-title">11. Opportunities Past Due</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Open opportunities whose expected close date '
    'has already passed. Keep this number to a minimum.</div>',
    unsafe_allow_html=True,
)
past_due_df = opps_f[opps_f["past_due"]].copy()
past_due_df["days_overdue"] = (TODAY - past_due_df["expected_close_date"]).dt.days

c1, c2 = st.columns([1, 2])
with c1:
    st.metric("Opportunities Past Due", len(past_due_df))
    st.metric("Value at Risk", f"${past_due_df['amount'].sum():,.0f}")
with c2:
    if len(past_due_df):
        by_owner_pd = past_due_df.groupby("owner").size().reset_index(name="count")
        fig = px.bar(by_owner_pd.sort_values("count"), x="count", y="owner",
                     orientation="h", color_discrete_sequence=["#e76f51"],
                     labels={"count": "Past Due Opportunities", "owner": "Owner"})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No past due opportunities in the current filter. 🎉")

if len(past_due_df):
    with st.expander("View past due opportunities table"):
        st.dataframe(
            past_due_df[["opp_id", "account_name", "owner", "stage", "amount",
                         "expected_close_date", "days_overdue"]]
            .sort_values("days_overdue", ascending=False),
            use_container_width=True, hide_index=True,
        )

# ========================================================================
# 12. SALES BY CLOSED DATE
# ========================================================================
st.markdown('<div class="section-title">12. Sales by Closed Date</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">Timing matters as much as deal value — use '
    'this to forecast, spot trends, and gauge conversion timelines.</div>',
    unsafe_allow_html=True,
)
won_by_date = closed_won.copy()
won_by_date["close_date"] = won_by_date["actual_close_date"]
daily_rev = won_by_date.groupby("close_date")["amount"].sum().reset_index()
daily_rev = daily_rev.sort_values("close_date")
daily_rev["cumulative"] = daily_rev["amount"].cumsum()

fig = go.Figure()
fig.add_trace(go.Bar(x=daily_rev["close_date"], y=daily_rev["amount"],
                      name="Daily Revenue", marker_color="#4C6FFF"))
fig.add_trace(go.Scatter(x=daily_rev["close_date"], y=daily_rev["cumulative"],
                          name="Cumulative Revenue", yaxis="y2",
                          line=dict(color="#e76f51", width=3)))
fig.update_layout(
    height=400,
    yaxis=dict(title="Daily Revenue ($)"),
    yaxis2=dict(title="Cumulative Revenue ($)", overlaying="y", side="right"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Sales Dashboard • Streamlit + Plotly + TextBlob • Synthetic demo data")
