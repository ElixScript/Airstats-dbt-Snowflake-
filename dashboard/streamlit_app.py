import altair as alt
import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="AirStats Aviation Analytics", page_icon="✈️", layout="wide")
session = get_active_session()

st.title("✈️ AirStats: Global Aviation Analytics Dashboard")
st.caption("Powered by dbt Core + Snowflake (AIRSTATS.DEV)")

# --- Sidebar Filters ---
st.sidebar.header("Filters")

continents_df = session.sql("""
    SELECT DISTINCT COALESCE(continent, 'UNKNOWN') AS continent
    FROM AIRSTATS.DEV.SILVER_AIRPORTS
    ORDER BY 1
""").to_pandas()

types_df = session.sql("""
    SELECT DISTINCT airport_type
    FROM AIRSTATS.DEV.SILVER_AIRPORTS
    ORDER BY 1
""").to_pandas()

selected_continents = st.sidebar.multiselect(
    "Continent",
    options=continents_df["CONTINENT"].tolist(),
    default=continents_df["CONTINENT"].tolist()
)

selected_types = st.sidebar.multiselect(
    "Airport Type",
    options=types_df["AIRPORT_TYPE"].tolist(),
    default=["large_airport", "medium_airport", "small_airport"]
)

if not selected_continents or not selected_types:
    st.warning("Select at least 1 Continent and 1 Airport Type in the sidebar.")
    st.stop()

cont_filter = ", ".join([f"'{c}'" for c in selected_continents])
type_filter = ", ".join([f"'{t}'" for t in selected_types])

where_clause = f"""
    COALESCE(a.continent, 'UNKNOWN') IN ({cont_filter})
    AND a.airport_type IN ({type_filter})
"""

# --- KPI Metrics ---
kpi = session.sql(f"""
    SELECT
        COUNT(DISTINCT a.airport_ident) AS total_airports,
        COUNT(DISTINCT CASE WHEN r.runway_closed = 0 THEN r.runway_id END) AS active_runways,
        ROUND(AVG(CASE WHEN r.runway_closed = 0 THEN r.runway_length_ft END), 0) AS avg_runway_ft,
        COUNT(DISTINCT c.comment_id) AS total_comments
    FROM AIRSTATS.DEV.SILVER_AIRPORTS a
    LEFT JOIN AIRSTATS.DEV.SILVER_RUNWAYS r ON a.airport_ident = r.airport_ident
    LEFT JOIN AIRSTATS.DEV.SILVER_AIRPORT_COMMENTS c ON a.airport_ident = c.airport_ident
    WHERE {where_clause}
""").to_pandas().iloc[0]

col1, col2, col3, col4 = st.columns(4)

def kpi_card(col, title, value, bg_color, border_color):
    col.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            border: 1px solid {border_color};
            border-left: 5px solid {border_color};
            border-radius: 8px;
            padding: 16px 20px;
            height: 110px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="font-size: 0.9rem; opacity: 0.85; margin-bottom: 6px;">{title}</div>
            <div style="font-size: 1.8rem; font-weight: 700; line-height: 1.2;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

kpi_card(col1, "Total Airports", f"{int(kpi['TOTAL_AIRPORTS']):,}", "rgba(41, 181, 232, 0.12)", "#29B5E8")
kpi_card(col2, "Active Runways", f"{int(kpi['ACTIVE_RUNWAYS']):,}", "rgba(16, 185, 129, 0.12)", "#10B981")
kpi_card(col3, "Avg Runway Length (ft)", f"{int(kpi['AVG_RUNWAY_FT'] or 0):,}", "rgba(99, 102, 241, 0.12)", "#6366F1")
kpi_card(col4, "Community Comments", f"{int(kpi['TOTAL_COMMENTS']):,}", "rgba(245, 158, 11, 0.12)", "#F59E0B")

st.divider()

# --- Row 1: Charts ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("Airports by Type")
    type_counts = session.sql(f"""
        SELECT a.airport_type, COUNT(*) AS total
        FROM AIRSTATS.DEV.SILVER_AIRPORTS a
        WHERE {where_clause}
        GROUP BY a.airport_type
        ORDER BY total DESC
    """).to_pandas()
    type_chart = (
        alt.Chart(type_counts)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("AIRPORT_TYPE:N", sort="-y", title="Airport Type"),
            y=alt.Y("TOTAL:Q", title="Airports"),
            color=alt.Color("AIRPORT_TYPE:N", legend=None, scale=alt.Scale(scheme="tableau10")),
            tooltip=["AIRPORT_TYPE:N", alt.Tooltip("TOTAL:Q", format=",")],
        )
        .properties(height=320)
    )
    st.altair_chart(type_chart, use_container_width=True)

with c2:
    st.subheader("Top 10 Countries by Airport Count")
    top_countries = session.sql(f"""
        SELECT a.iso_country, COUNT(*) AS total
        FROM AIRSTATS.DEV.SILVER_AIRPORTS a
        WHERE {where_clause} AND a.iso_country IS NOT NULL
        GROUP BY a.iso_country
        ORDER BY total DESC
        LIMIT 10
    """).to_pandas()
    country_chart = (
        alt.Chart(top_countries)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("ISO_COUNTRY:N", sort="-y", title="Country"),
            y=alt.Y("TOTAL:Q", title="Airports"),
            color=alt.Color("ISO_COUNTRY:N", legend=None, scale=alt.Scale(scheme="tableau10")),
            tooltip=["ISO_COUNTRY:N", alt.Tooltip("TOTAL:Q", format=",")],
        )
        .properties(height=320)
    )
    st.altair_chart(country_chart, use_container_width=True)

# --- Row 2: Map & Yearly Comments ---
c3, c4 = st.columns(2)

with c3:
    st.subheader("Airport Geographic Distribution (Sample up to 5,000)")
    map_df = session.sql(f"""
        SELECT
            a.airport_lat AS lat,
            a.airport_long AS lon
        FROM AIRSTATS.DEV.SILVER_AIRPORTS a
        WHERE {where_clause}
          AND a.airport_lat BETWEEN -90 AND 90
          AND a.airport_long BETWEEN -180 AND 180
        LIMIT 5000
    """).to_pandas()
    map_df.columns = ["lat", "lon"]
    st.map(map_df)

with c4:
    st.subheader("Yearly Community Comments Trend")
    comments_trend = session.sql(f"""
        SELECT
            YEAR(c.comment_timestamp) AS comment_year,
            COUNT(*) AS total_comments
        FROM AIRSTATS.DEV.SILVER_AIRPORT_COMMENTS c
        JOIN AIRSTATS.DEV.SILVER_AIRPORTS a ON c.airport_ident = a.airport_ident
        WHERE {where_clause} AND c.comment_timestamp IS NOT NULL
        GROUP BY YEAR(c.comment_timestamp)
        ORDER BY comment_year
    """).to_pandas()
    if not comments_trend.empty:
        st.line_chart(comments_trend.set_index("COMMENT_YEAR"), color="#10B981")
    else:
        st.info("No comment data available for this filter.")

# --- Row 3: Top Longest Runways Table ---
st.subheader("Top 15 Longest Active Runways")
top_runways = session.sql(f"""
    SELECT
        a.airport_ident,
        a.airport_name,
        a.iso_country,
        a.airport_type,
        r.runway_length_ft,
        r.runway_width_ft,
        r.runway_surface,
        r.runway_lighted
    FROM AIRSTATS.DEV.SILVER_AIRPORTS a
    JOIN AIRSTATS.DEV.SILVER_RUNWAYS r ON a.airport_ident = r.airport_ident
    WHERE {where_clause}
      AND r.runway_closed = 0
      AND r.runway_length_ft IS NOT NULL
    ORDER BY r.runway_length_ft DESC
    LIMIT 15
""").to_pandas()
st.dataframe(top_runways, use_container_width=True)
