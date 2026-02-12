# 🗺️ Aviation Operation Dashboard - Rebuild Roadmap

**Goal:** Rebuild the dashboard with a robust, "Schema-First" architecture to eliminate logic errors, sync failures, and data discrepancies.

## 🛑 Problem Analysis (Why we are rebuilding)
1.  **Logic "Spaghetti":** `data_processor.py` mixes data fetching, filtering, and business logic, making it hard to debug (e.g., the Filter Paradox).
2.  **Unreliable Sync:** The current monolithic sync job hangs on large datasets and handles timezones inconsistently (Server vs Local).
3.  **Data Quality:** "No Crew = No Flight" logic hidden in dashboard rendering rather than the data layer.

## 🏗️ Proposed Architecture: Clean ETL

We will move from **"Fetch & Process on the Fly"** to **"Store, Then Query"**.

```mermaid
graph LR
    A[AIMS SOAP API] -->|Extract| B(Airflow / Cron Scripts)
    B -->|Transform & Validate| C[Supabase DB (Strict Schema)]
    C -->|Query| D[API Service (Fast Read)]
    D -->|JSON| E[Frontend Dashboard]
```

---

## 📅 Phased Implementation Plan

### Phase 1: Foundation & Schema (Week 1)
**Focus:** Define the "Truth" structure in the database.
-   [ ] **Finalize Schema:** Use `schema_aims_full.sql` as the strict source of truth.
-   [ ] **Timezone Master:** Create a `reference_timezones` table (no more hardcoded dicts in python).
-   [ ] **Strict Typing:** All Times in UTC in DB, converted ONLY at the frontend or explicit API layer.

### Phase 2: Reliable Ingestion (The "Pump") (Week 2)
**Focus:** Get data in reliably, without hanging.
-   [ ] **Atomic Sync Scripts:** Break `run_full_sync.py` into small, independent scripts:
    -   `sync_flights_today.py`
    -   `sync_crew_roster.py`
    -   `sync_ref_data.py`
-   [ ] **Job Runner:** Use a proper runner (e.g., GitHub Actions, or a dedicated robust Scheduler) instead of `apscheduler` inside Flask.
-   [ ] **Validation Layer:** Script fails *loudly* if data is missing, rather than failing silently.

### Phase 3: Core Logic Refactor (Week 3)
**Focus:** Correct calculations at the DB level.
-   [ ] **SQL Views for Metrics:** Move logic from Python to SQL Views.
    -   `view_dashboard_summary`: Calculates Total Flights, Crew Counts in SQL.
    -   `view_aircraft_status`: Derives First/Last flight times.
-   [ ] **"Golden Dataset"**: A single Source-of-Truth table for dashboard display, updated by the sync jobs.

### Phase 4: Frontend & API (Week 4)
**Focus:** Dumb API, Smart UI.
-   [ ] **Lightweight API:** `api_server.py` simply queries the SQL Views (SELECT * FROM view...).
-   [ ] **Frontend Refresh:** Reconnect UI to new endpoints.

## 🚀 Next Immediately Steps
1.  **Review this Roadmap.**
2.  **Initialize Phase 1:** Run `/init` to set up the new structure.
