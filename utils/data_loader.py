"""
data_loader.py
---------------
Centralized, cached loading of all CSV data sources plus small
helper functions (e.g. TextBlob sentiment scoring) shared across
the dashboard.
"""

import os

import pandas as pd
import streamlit as st
from textblob import TextBlob

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@st.cache_data
def load_leads():
    df = pd.read_csv(os.path.join(DATA_DIR, "leads.csv"), parse_dates=["created_date"])
    return df


@st.cache_data
def load_opportunities():
    df = pd.read_csv(
        os.path.join(DATA_DIR, "opportunities.csv"),
        parse_dates=["created_date", "expected_close_date", "actual_close_date"],
    )
    return df


@st.cache_data
def load_activities():
    df = pd.read_csv(os.path.join(DATA_DIR, "activities.csv"), parse_dates=["due_date"])
    return df


@st.cache_data
def load_cases():
    df = pd.read_csv(os.path.join(DATA_DIR, "cases.csv"), parse_dates=["created_date"])
    df["sentiment_polarity"] = df["notes"].apply(lambda t: TextBlob(str(t)).sentiment.polarity)
    df["sentiment_label"] = df["sentiment_polarity"].apply(label_sentiment)
    return df


@st.cache_data
def load_products():
    df = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    return df


def label_sentiment(polarity: float) -> str:
    if polarity > 0.15:
        return "Positive"
    elif polarity < -0.15:
        return "Negative"
    return "Neutral"


def data_files_exist() -> bool:
    required = ["leads.csv", "opportunities.csv", "activities.csv", "cases.csv", "products.csv"]
    return all(os.path.exists(os.path.join(DATA_DIR, f)) for f in required)
