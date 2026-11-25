# AirStats: Analytical SQL Queries

This guide provides **10 analytical SQL queries** designed to run directly on **Snowflake** against the cleaned Silver tables and SCD Type 2 snapshots in `AIRSTATS.DEV`.

Before running these queries, make sure you have executed `dbt build` and selected the right context in your Snowflake Worksheet:

```sql
USE DATABASE AIRSTATS;
USE SCHEMA DEV;
```

---

## 1. Global Airport Distribution by Type

Calculates the total number of airports and percentage share for each airport classification worldwide.

```sql
SELECT
    airport_type,
    COUNT(*) AS total_airports,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM AIRSTATS.DEV.SILVER_AIRPORTS
GROUP BY airport_type
ORDER BY total_airports DESC;
```

---

## 2. Top 10 Countries by Large Airports and Runway Capacity

Identifies countries with the highest number of `large_airport` facilities along with their active runway count, average runway length, and longest runway.

```sql
SELECT
    a.iso_country,
    COUNT(DISTINCT a.airport_ident) AS total_large_airports,
    COUNT(r.runway_id) AS active_runways,
    ROUND(AVG(r.runway_length_ft), 0) AS avg_runway_length_ft,
    MAX(r.runway_length_ft) AS longest_runway_ft
FROM AIRSTATS.DEV.SILVER_AIRPORTS a
LEFT JOIN AIRSTATS.DEV.SILVER_RUNWAYS r
    ON a.airport_ident = r.airport_ident
   AND r.runway_closed = 0
WHERE a.airport_type = 'large_airport'
GROUP BY a.iso_country
ORDER BY total_large_airports DESC
LIMIT 10;
```

---

## 3. Top 15 Longest Active Runways in Indonesia (`ID`)

Lists Indonesia's longest operational runways along with surface type and night-lighting availability.

```sql
SELECT
    a.airport_ident,
    a.airport_name,
    a.airport_type,
    r.runway_length_ft,
    r.runway_width_ft,
    r.runway_surface,
    CASE WHEN r.runway_lighted = 1 THEN 'Yes' ELSE 'No' END AS is_lighted
FROM AIRSTATS.DEV.SILVER_AIRPORTS a
JOIN AIRSTATS.DEV.SILVER_RUNWAYS r
    ON a.airport_ident = r.airport_ident
WHERE a.iso_country = 'ID'
  AND r.runway_closed = 0
ORDER BY r.runway_length_ft DESC NULLS LAST
LIMIT 15;
```

---

## 4. Longest Active Runway per Continent (Window Function)

Uses Snowflake's `QUALIFY` with `ROW_NUMBER()` to find the single longest operational runway on each continent.

```sql
SELECT
    a.continent,
    a.iso_country,
    a.airport_ident,
    a.airport_name,
    r.runway_length_ft,
    r.runway_width_ft,
    r.runway_surface
FROM AIRSTATS.DEV.SILVER_AIRPORTS a
JOIN AIRSTATS.DEV.SILVER_RUNWAYS r
    ON a.airport_ident = r.airport_ident
WHERE a.continent IS NOT NULL
  AND r.runway_closed = 0
  AND r.runway_length_ft IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY a.continent
    ORDER BY r.runway_length_ft DESC, r.runway_width_ft DESC NULLS LAST
) = 1
ORDER BY r.runway_length_ft DESC;
```

---

## 5. Night Lighting Coverage by Airport Type

Measures what percentage of active runways are equipped with lighting across each airport category.

```sql
SELECT
    a.airport_type,
    COUNT(r.runway_id) AS total_active_runways,
    SUM(CASE WHEN r.runway_lighted = 1 THEN 1 ELSE 0 END) AS lighted_runways,
    ROUND(
        100.0 * SUM(CASE WHEN r.runway_lighted = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(r.runway_id), 0),
        2
    ) AS pct_lighted
FROM AIRSTATS.DEV.SILVER_AIRPORTS a
JOIN AIRSTATS.DEV.SILVER_RUNWAYS r
    ON a.airport_ident = r.airport_ident
WHERE r.runway_closed = 0
GROUP BY a.airport_type
ORDER BY total_active_runways DESC;
```

---

## 6. Top 15 Runway Surface Types and Average Dimensions

Analyzes the most common runway surface materials (including `__UNKNOWN__` standardized in the Silver layer) along with average length and width.

```sql
SELECT
    runway_surface,
    COUNT(*) AS total_runways,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_runways,
    ROUND(AVG(runway_length_ft), 0) AS avg_length_ft,
    ROUND(AVG(runway_width_ft), 0) AS avg_width_ft
FROM AIRSTATS.DEV.SILVER_RUNWAYS
GROUP BY runway_surface
ORDER BY total_runways DESC
LIMIT 15;
```

---

## 7. Airport Closure Rate by Continent

Compares operational airports against closed airports per continent to highlight regions with the highest closure ratios.

```sql
SELECT
    COALESCE(continent, 'UNKNOWN') AS continent,
    COUNT(*) AS total_airports,
    SUM(CASE WHEN airport_type = 'closed' THEN 1 ELSE 0 END) AS closed_airports,
    ROUND(
        100.0 * SUM(CASE WHEN airport_type = 'closed' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS closure_rate_pct
FROM AIRSTATS.DEV.SILVER_AIRPORTS
GROUP BY COALESCE(continent, 'UNKNOWN')
ORDER BY closure_rate_pct DESC;
```

---

## 8. Top 10 Most Commented Airports

Joins user comments with airport metadata to identify the airports generating the highest community engagement.

```sql
SELECT
    a.airport_ident,
    a.airport_name,
    a.iso_country,
    a.airport_type,
    COUNT(c.comment_id) AS total_comments,
    COUNT(DISTINCT c.member_nickname) AS unique_commenters,
    MIN(c.comment_timestamp) AS first_comment_at,
    MAX(c.comment_timestamp) AS latest_comment_at
FROM AIRSTATS.DEV.SILVER_AIRPORT_COMMENTS c
JOIN AIRSTATS.DEV.SILVER_AIRPORTS a
    ON c.airport_ident = a.airport_ident
GROUP BY a.airport_ident, a.airport_name, a.iso_country, a.airport_type
ORDER BY total_comments DESC
LIMIT 10;
```

---

## 9. Yearly Community Comment Trend and Anonymous Share

Tracks annual comment volume and the proportion of comments posted by anonymous users (`__UNKNOWN__`).

```sql
SELECT
    DATE_TRUNC('year', comment_timestamp)::DATE AS comment_year,
    COUNT(*) AS total_comments,
    COUNT(DISTINCT airport_ident) AS airports_commented,
    SUM(CASE WHEN member_nickname = '__UNKNOWN__' THEN 1 ELSE 0 END) AS anonymous_comments,
    ROUND(
        100.0 * SUM(CASE WHEN member_nickname = '__UNKNOWN__' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS anonymous_pct
FROM AIRSTATS.DEV.SILVER_AIRPORT_COMMENTS
WHERE comment_timestamp IS NOT NULL
GROUP BY DATE_TRUNC('year', comment_timestamp)::DATE
ORDER BY comment_year DESC;
```

---

## 10. SCD Type 2 Snapshot Audit (Current vs Historical Records)

Inspects `SCD_SILVER_AIRPORTS` to summarize active vs expired historical versions and detect any airports whose attributes have changed over time.

```sql
-- Part A: Summary of current vs historical snapshot rows
SELECT
    CASE WHEN dbt_valid_to IS NULL THEN 'Current' ELSE 'Historical' END AS record_status,
    COUNT(*) AS row_count,
    COUNT(DISTINCT airport_ident) AS unique_airports
FROM AIRSTATS.DEV.SCD_SILVER_AIRPORTS
GROUP BY CASE WHEN dbt_valid_to IS NULL THEN 'Current' ELSE 'Historical' END;

-- Part B: List airports that have more than one historical version
SELECT
    airport_ident,
    airport_name,
    airport_type,
    dbt_valid_from,
    dbt_valid_to
FROM AIRSTATS.DEV.SCD_SILVER_AIRPORTS
WHERE airport_ident IN (
    SELECT airport_ident
    FROM AIRSTATS.DEV.SCD_SILVER_AIRPORTS
    GROUP BY airport_ident
    HAVING COUNT(*) > 1
)
ORDER BY airport_ident, dbt_valid_from;
```
