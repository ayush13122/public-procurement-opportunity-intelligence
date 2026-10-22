"""Streamlit app: Historical Assam Procurement Market Explorer.

Run from project root:
    python -m streamlit run app/market_explorer.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.market_explorer_data import filter_market_data, get_filter_options, load_market_data, summarize_market  # noqa: E402


st.set_page_config(
    page_title="Public Procurement Market Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Public Procurement Market Explorer")
st.caption("Historical Assam procurement records · 2016–17 to 2021–22 source dataset")
st.info(
    "This first version explores historical records only. Niche assignments are provisional, "
    "and historical tender values do not indicate current availability, profit, eligibility, or win probability. "
    "The currency/unit for the source amount has not been independently verified, so values are shown without a currency symbol."
)

@st.cache_data(show_spinner="Loading and validating procurement records...")
def load_data(root: str) -> pd.DataFrame:
    return load_market_data(Path(root))

try:
    data = load_data(str(PROJECT_ROOT))
except Exception as exc:  # Show actionable error instead of opaque traceback in app.
    st.error("Dashboard data load failed. Check the input paths and regenerate missing reports.")
    st.code(str(exc))
    st.markdown(
        "Expected files:\n"
        "- `data/processed/assam_procurement_cleaned.csv`\n"
        "- `reports/assam_record_niche_assignments.csv`"
    )
    st.stop()

options = get_filter_options(data)
value_series = data["tender_value_numeric"].dropna()
positive_values = value_series[value_series > 0]
value_min = float(positive_values.min()) if not positive_values.empty else 0.0
value_max = float(positive_values.max()) if not positive_values.empty else 0.0

with st.sidebar:
    st.header("Market filters")
    selected_categories = st.multiselect("Procurement type", options["categories"], default=options["categories"])
    selected_niches = st.multiselect("Business niche (provisional)", options["niches"], default=options["niches"])
    selected_years = st.multiselect("Fiscal year", options["fiscal_years"], default=options["fiscal_years"])
    selected_stages = st.multiselect("Tender stage", options["stages"], default=options["stages"])
    buyer_search = st.text_input("Search buyer / department", placeholder="e.g. Public Works")
    title_search = st.text_input("Search tender title", placeholder="e.g. road, computer, medicine")
    show_review = st.checkbox("Include records needing niche review", value=True)
    use_value_filter = st.checkbox("Filter by reported tender value", value=False)
    minimum_value = None
    maximum_value = None
    if use_value_filter:
        left, right = st.columns(2)
        with left:
            minimum_value = st.number_input("Minimum", min_value=0.0, value=max(0.0, value_min), step=100000.0)
        with right:
            maximum_value = st.number_input("Maximum", min_value=0.0, value=max(value_min, value_max), step=100000.0)
        if minimum_value > maximum_value:
            st.warning("Minimum value is above maximum. No records will match the value filter.")
            minimum_value, maximum_value = maximum_value + 1, maximum_value

filtered = filter_market_data(
    data,
    categories=selected_categories,
    niches=selected_niches,
    fiscal_years=selected_years,
    stages=selected_stages,
    buyer_search=buyer_search,
    title_search=title_search,
    include_review_required=show_review,
    min_value=minimum_value,
    max_value=maximum_value,
)

summary = summarize_market(filtered)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Matching records", f"{summary['records']:,}")
k2.metric("Buyer organizations", f"{summary['buyers']:,}")
k3.metric("Positive reported values", f"{summary['positive_value_records']:,}")
k4.metric("Zero reported values", f"{summary['zero_value_records']:,}")
k5.metric("Needs niche review", f"{summary['review_required_records']:,}")
if summary["median_positive_value"] is not None:
    st.caption(
        "Median positive reported tender value in the filtered view: "
        f"{summary['median_positive_value']:,.2f} (source units not independently verified). "
        f"Missing value records in this view: {summary['missing_value_records']:,}."
    )
else:
    st.caption(f"No positive reported tender values in this selection. Missing values: {summary['missing_value_records']:,}.")

if filtered.empty:
    st.warning("No records match the selected filters. Try widening the filter selections.")
    st.stop()

left_chart, right_chart = st.columns(2)
with left_chart:
    st.subheader("Records by procurement type")
    category_counts = (
        filtered.groupby("tender/mainProcurementCategory", dropna=False)
        .size().reset_index(name="records")
        .sort_values("records", ascending=False)
    )
    fig = px.bar(category_counts, x="tender/mainProcurementCategory", y="records", text="records")
    fig.update_layout(xaxis_title="Original broad category", yaxis_title="Tender records", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
with right_chart:
    st.subheader("Top provisional business niches")
    niche_counts = (
        filtered.groupby("suggested_analytical_niche", dropna=False)
        .size().reset_index(name="records")
        .sort_values("records", ascending=False).head(12)
    )
    fig = px.bar(niche_counts.sort_values("records"), x="records", y="suggested_analytical_niche", orientation="h", text="records")
    fig.update_layout(xaxis_title="Tender records", yaxis_title="Provisional niche", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

left_chart, right_chart = st.columns(2)
with left_chart:
    st.subheader("Historical records by fiscal year")
    year_counts = filtered.groupby("fiscal_year", dropna=False).size().reset_index(name="records")
    # Fiscal labels are ordered chronologically by their leading year where possible.
    year_counts["_sort_year"] = pd.to_numeric(year_counts["fiscal_year"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce")
    year_counts = year_counts.sort_values(["_sort_year", "fiscal_year"], na_position="last")
    fig = px.line(year_counts, x="fiscal_year", y="records", markers=True)
    fig.update_layout(xaxis_title="Fiscal year in source", yaxis_title="Tender records")
    st.plotly_chart(fig, use_container_width=True)
with right_chart:
    st.subheader("Top buyer organizations")
    buyer_counts = (
        filtered.groupby("buyer/name", dropna=False).size().reset_index(name="records")
        .sort_values("records", ascending=False).head(12)
    )
    fig = px.bar(buyer_counts.sort_values("records"), x="records", y="buyer/name", orientation="h", text="records")
    fig.update_layout(xaxis_title="Tender records", yaxis_title="Buyer / department", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Tender records")
display_columns = [
    ("ocid", "OCID"),
    ("tender/id", "Tender ID"),
    ("tender/title", "Tender title"),
    ("tender/mainProcurementCategory", "Procurement type"),
    ("tenderclassification/description", "Original classification"),
    ("suggested_analytical_niche", "Provisional niche"),
    ("buyer/name", "Buyer / department"),
    ("fiscal_year", "Fiscal year"),
    ("publication_date_parsed", "Publication date"),
    ("tender/stage", "Recorded stage"),
    ("tender_value_numeric", "Reported tender value"),
    ("tenderers_numeric", "Tenderers (if recorded)"),
    ("mapping_method", "Mapping method"),
    ("manual_review_required", "Needs niche review?"),
]
renames = {original: label for original, label in display_columns if original in filtered.columns}
view = filtered[list(renames)].rename(columns=renames).copy()
if "Publication date" in view.columns:
    view["Publication date"] = pd.to_datetime(view["Publication date"], errors="coerce").dt.strftime("%Y-%m-%d")
st.dataframe(view, use_container_width=True, hide_index=True, height=420)

csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="Download filtered records as CSV",
    data=csv_bytes,
    file_name="filtered_historical_procurement_records.csv",
    mime="text/csv",
)
st.caption(
    "Data provenance: Assam public procurement historical dataset (2016–17 to 2021–22 export). "
    "Provisional niche is a rule-based candidate, not verified ground truth. "
    "Historical records are not current open tenders. Review tender documents and official sources before any real bid decision."
)
