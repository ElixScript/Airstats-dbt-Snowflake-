# AirStats dbt Project

This directory contains the core **dbt** project for the AirStats global aviation analytics pipeline on Snowflake.

For full architecture details, setup instructions, and data model documentation, see the root [README.md](../README.md) and [DATASETS.md](../DATASETS.md).

## Quick Reference Commands

Run these commands from inside the `airstats/` directory:

```bash
# Install dbt packages (metaplane/dbt_expectations)
dbt deps

# Verify Snowflake connection and configuration
dbt debug

# Run models, snapshots, and tests in dependency order
dbt build

# Run specific layers or models
dbt run --select silver
dbt run --select silver_airport_comments
dbt snapshot
dbt test

# Generate and view dbt documentation
dbt docs generate && dbt docs serve
```
