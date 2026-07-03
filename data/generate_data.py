"""
generate_data.py
-----------------
Generates realistic synthetic CRM/sales data so the dashboard has
something meaningful to display out of the box.

Run this once before starting the app:
    python data/generate_data.py

It creates 5 CSV files inside the data/ folder:
    leads.csv
    opportunities.csv
    activities.csv
    cases.csv
    products.csv
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
random.seed(42)
np.random.seed(42)
Faker.seed(42)

TODAY = datetime.today()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------
# Reference lists
# ---------------------------------------------------------------------
LEAD_SOURCES = [
    "Website Demo Signup", "Referral", "Conference", "Cold Call",
    "LinkedIn Ads", "Webinar", "Partner", "Organic Search"
]

STAGES = [
    "Prospecting", "Qualification", "Needs Analysis",
    "Proposal/Quote", "Negotiation", "Closed Won", "Closed Lost"
]

OPEN_STAGES = ["Prospecting", "Qualification", "Needs Analysis",
               "Proposal/Quote", "Negotiation"]

OPP_TYPES = ["New Business", "Upsell"]

PRODUCTS = ["CloudSuite Pro", "Analytics+", "SecureVault", "TeamSync",
            "DataPipe", "InsightAI"]

ACTIVITY_TYPES = ["Call", "Demo", "Visit", "Email Follow-up"]
ACTIVITY_STATUS = ["Open", "Completed"]

CASE_PRIORITIES = ["Low", "Medium", "High", "Critical"]

POSITIVE_NOTES = [
    "Customer is thrilled with the new dashboard feature.",
    "Great feedback, they love how easy the product is to use.",
    "Very happy with support response time, excellent service.",
    "Customer praised the onboarding experience as smooth and helpful.",
]
NEUTRAL_NOTES = [
    "Customer asked a question about invoice cycle dates.",
    "Requesting clarification on the renewal process.",
    "Wants to know if a feature is on the roadmap.",
    "General question about API rate limits.",
]
NEGATIVE_NOTES = [
    "Customer is frustrated with slow load times on reports.",
    "Unhappy about a billing error that was not resolved quickly.",
    "Complained the integration keeps failing and it's a terrible experience.",
    "Very disappointed with the delay in fixing a critical bug.",
]

# ---------------------------------------------------------------------
# 1. Leads
# ---------------------------------------------------------------------
def gen_leads(n=400):
    rows = []
    for i in range(n):
        created = TODAY - timedelta(days=random.randint(0, 365))
        source = random.choices(
            LEAD_SOURCES,
            weights=[22, 18, 12, 8, 14, 10, 9, 7]
        )[0]
        converted = random.random() < 0.35
        rows.append({
            "lead_id": f"L-{1000+i}",
            "lead_name": fake.name(),
            "company": fake.company(),
            "lead_source": source,
            "created_date": created.date(),
            "status": "Converted" if converted else random.choice(
                ["New", "Contacted", "Nurturing", "Disqualified"]),
            "converted": converted,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# 2. Opportunities (drives Pipeline, Sales Cycle, Closed Opps,
#    New Business vs Upsell, Win/Loss, Open Opps, Past Due, Sales by
#    Closed Date)
# ---------------------------------------------------------------------
def gen_opportunities(n=250):
    rows = []
    owners = [fake.name() for _ in range(8)]
    for i in range(n):
        created = TODAY - timedelta(days=random.randint(10, 400))
        expected_cycle = random.randint(20, 90)
        expected_close = created + timedelta(days=expected_cycle)

        stage = random.choices(
            STAGES,
            weights=[10, 12, 10, 10, 8, 35, 15]
        )[0]

        is_closed = stage in ("Closed Won", "Closed Lost")
        is_won = stage == "Closed Won"

        actual_close_date = None
        if is_closed:
            actual_close_date = created + timedelta(
                days=random.randint(15, expected_cycle + 40))
            if actual_close_date > TODAY:
                actual_close_date = TODAY - timedelta(days=random.randint(0, 5))

        amount = round(np.random.lognormal(mean=9.2, sigma=0.6), 2)
        amount = min(amount, 250000)

        rows.append({
            "opp_id": f"OPP-{2000+i}",
            "account_name": fake.company(),
            "owner": random.choice(owners),
            "product": random.choice(PRODUCTS),
            "type": random.choices(OPP_TYPES, weights=[65, 35])[0],
            "stage": stage,
            "amount": amount,
            "created_date": created.date(),
            "expected_close_date": expected_close.date(),
            "actual_close_date": actual_close_date.date() if actual_close_date else None,
            "is_closed": is_closed,
            "is_won": is_won,
        })
    df = pd.DataFrame(rows)

    # Past due = open opportunity whose expected close date has passed
    df["expected_close_date"] = pd.to_datetime(df["expected_close_date"])
    df["past_due"] = (~df["is_closed"]) & (df["expected_close_date"] < TODAY)
    return df


# ---------------------------------------------------------------------
# 3. Activities (Open Activities)
# ---------------------------------------------------------------------
def gen_activities(opps_df, n=300):
    rows = []
    owners = opps_df["owner"].unique().tolist()
    for i in range(n):
        due = TODAY + timedelta(days=random.randint(-15, 20))
        status = "Open" if due >= TODAY - timedelta(days=2) and random.random() < 0.55 else "Completed"
        rows.append({
            "activity_id": f"ACT-{3000+i}",
            "type": random.choice(ACTIVITY_TYPES),
            "related_opp": random.choice(opps_df["opp_id"].tolist()),
            "owner": random.choice(owners),
            "due_date": due.date(),
            "status": status,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# 4. Cases (Open Cases) — includes free-text notes for TextBlob sentiment
# ---------------------------------------------------------------------
def gen_cases(n=120):
    rows = []
    for i in range(n):
        created = TODAY - timedelta(days=random.randint(0, 60))
        bucket = random.choices(["pos", "neu", "neg"], weights=[35, 35, 30])[0]
        note = random.choice(
            POSITIVE_NOTES if bucket == "pos"
            else NEUTRAL_NOTES if bucket == "neu"
            else NEGATIVE_NOTES
        )
        status = random.choices(["Open", "Closed"], weights=[40, 60])[0]
        rows.append({
            "case_id": f"CASE-{4000+i}",
            "account_name": fake.company(),
            "subject": note[:40] + "...",
            "notes": note,
            "priority": random.choice(CASE_PRIORITIES),
            "status": status,
            "created_date": created.date(),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# 5. Products (Product Gaps: predicted vs actual sales)
# ---------------------------------------------------------------------
def gen_products():
    rows = []
    for p in PRODUCTS:
        predicted = random.randint(80000, 220000)
        variance = np.random.normal(0, 0.22)
        actual = max(5000, predicted * (1 + variance))
        rows.append({
            "product": p,
            "predicted_sales": round(predicted, 2),
            "actual_sales": round(actual, 2),
        })
    return pd.DataFrame(rows)


def main():
    leads = gen_leads()
    opportunities = gen_opportunities()
    activities = gen_activities(opportunities)
    cases = gen_cases()
    products = gen_products()

    leads.to_csv(os.path.join(BASE_DIR, "leads.csv"), index=False)
    opportunities.to_csv(os.path.join(BASE_DIR, "opportunities.csv"), index=False)
    activities.to_csv(os.path.join(BASE_DIR, "activities.csv"), index=False)
    cases.to_csv(os.path.join(BASE_DIR, "cases.csv"), index=False)
    products.to_csv(os.path.join(BASE_DIR, "products.csv"), index=False)

    print("✅ Synthetic data generated in:", BASE_DIR)
    print(f"   leads.csv          -> {len(leads)} rows")
    print(f"   opportunities.csv  -> {len(opportunities)} rows")
    print(f"   activities.csv     -> {len(activities)} rows")
    print(f"   cases.csv          -> {len(cases)} rows")
    print(f"   products.csv       -> {len(products)} rows")


if __name__ == "__main__":
    main()
