"""
CARMS Data Platform — Streamlit Dashboard (Normalized + Multi‑Tabs)
Uses all relational API endpoints:
- /programs/
- /disciplines/, /disciplines/{id}/programs
- /schools/, /schools/{id}/programs
- /sites/, /sites/{id}/programs
- /streams/, /programs/{stream_id}
"""

import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px

API_URL = os.getenv("API_URL", "http://localhost:8000")
# Browser-reachable URL (not the internal API_URL, which only resolves
# container-to-container) for the QA search page.
QA_UI_URL = os.getenv("QA_UI_URL", "http://localhost:8000/ui/")


# ---------------------------------------------------------
# Generic API fetcher
# ---------------------------------------------------------
def fetch_json(endpoint: str):
    url = f"{API_URL.rstrip('/')}{endpoint}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API request failed: {e}")
        return []


# ---------------------------------------------------------
# TAB 1 — OVERVIEW (Global statistics)
# ---------------------------------------------------------
def show_overview():
    st.subheader("Global Overview — Programs")

    programs = fetch_json("/programs/")
    if not programs:
        st.warning("No program data available.")
        return

    streams = fetch_json("/streams/")
    if not streams:
        st.warning("No streams found.")
        return
        

    df = pd.DataFrame(programs)
    df_stream = pd.DataFrame(streams)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Programs", len(df))
    col2.metric("Disciplines", df["discipline_name"].nunique())
    col3.metric("Schools", df["school_name"].nunique())
    col4.metric("Streams", df_stream["program_stream"].nunique())

    st.divider()

    # Programs by discipline
    colA, colB = st.columns(2)

    with colA:
        st.subheader("Programs by Discipline")
        by_disc = df.groupby("discipline_name").size().reset_index(name="count")
        fig = px.bar(by_disc, x="count", y="discipline_name", orientation="h")
        st.plotly_chart(fig, use_container_width=True)

    with colB:
        st.subheader("Programs by School")
        by_school = df.groupby("school_name").size().reset_index(name="count")
        fig = px.bar(by_school, x="count", y="school_name", orientation="h")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Programs by Stream name")
    by_stream = df.groupby("program_stream_name").size().reset_index(name="count")
    fig = px.bar(by_stream, x="program_stream_name", y="count")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw Program Data"):
        st.dataframe(df, use_container_width=True)


# ---------------------------------------------------------
# TAB 2 — DISCIPLINES
# ---------------------------------------------------------
def show_disciplines():
    st.subheader("Disciplines")

    disciplines = fetch_json("/disciplines/")
    if not disciplines:
        st.warning("No disciplines found.")
        return

    df = pd.DataFrame(disciplines)
    st.dataframe(df, use_container_width=True)

    selected = st.selectbox("Select a discipline", df["discipline_name"])
    disc_id = df.loc[df["discipline_name"] == selected, "discipline_id"].iloc[0]

    programs = fetch_json(f"/disciplines/{disc_id}/programs")
    st.write(f"Programs for **{selected}**")
    st.dataframe(pd.DataFrame(programs), use_container_width=True)


# ---------------------------------------------------------
# TAB 3 — SCHOOLS
# ---------------------------------------------------------
def show_schools():
    st.subheader("Schools")

    schools = fetch_json("/schools/")
    if not schools:
        st.warning("No schools found.")
        return

    df = pd.DataFrame(schools)
    st.dataframe(df, use_container_width=True)

    selected = st.selectbox("Select a school", df["school_name"])
    school_id = df.loc[df["school_name"] == selected, "school_id"].iloc[0]

    programs = fetch_json(f"/schools/{school_id}/programs")
    st.write(f"Programs offered by **{selected}**")
    st.dataframe(pd.DataFrame(programs), use_container_width=True)


# ---------------------------------------------------------
# TAB 4 — SITES
# ---------------------------------------------------------
def show_sites():
    st.subheader("Training Sites")

    sites = fetch_json("/sites/")
    if not sites:
        st.warning("No sites found.")
        return

    df = pd.DataFrame(sites)
    st.dataframe(df, use_container_width=True)

    selected = st.selectbox("Select a site", df["site_name"])
    site_id = df.loc[df["site_name"] == selected, "site_id"].iloc[0]

    programs = fetch_json(f"/sites/{site_id}/programs")
    st.write(f"Programs at **{selected}**")
    st.dataframe(pd.DataFrame(programs), use_container_width=True)


# ---------------------------------------------------------
# TAB 5 — STREAMS
# ---------------------------------------------------------
def show_streams():
    st.subheader("Program Streams")

    streams = fetch_json("/streams/")
    if not streams:
        st.warning("No streams found.")
        return

    df = pd.DataFrame(streams)
    st.dataframe(df, use_container_width=True)
        

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    st.set_page_config(page_title="CARMS Dashboard", layout="wide")

    title_col, link_col = st.columns([5, 1])
    with title_col:
        st.title("CARMS Residency Programs — Dashboard")
        st.caption(f"API: {API_URL}")
    with link_col:
        st.link_button("Ask a question →", QA_UI_URL, use_container_width=True)

    tabs = st.tabs(["Overview", "Disciplines", "Schools", "Sites", "Streams"])

    with tabs[0]:
        show_overview()

    with tabs[1]:
        show_disciplines()

    with tabs[2]:
        show_schools()

    with tabs[3]:
        show_sites()

    with tabs[4]:
        show_streams()


if __name__ == "__main__":
    main()