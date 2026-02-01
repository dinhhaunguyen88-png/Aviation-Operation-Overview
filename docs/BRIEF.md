# Dashboard Refactor Brief: Operations Consolidation

## Summary
Refactor the aviation dashboard to consolidate all critical operational metrics into a single view. This involves moving flight-centric KPIs from the "Operations Overview" to the main "Dashboard", removing the detailed crew list table, and implementing a real-time flight filter (+/- 1 hour from current time).

## Proposed Changes

### 1. Dashboard UI (`templates/crew_dashboard.html`)
- **KPI Row Expansion**: Merge current crew KPIs with flight KPIs.
  - New KPI set: Total Crew, Standby, Sick Leave, Total Flights, Active Aircraft, Total Block Hours, Aircraft Utilization.
- **Crew List Removal**: Remove the `<section class="panel table-panel">` containing the Crew List table.
- **Flight Table Refinement**: Rename "Today's Flights" to "Operational Focus" or "Active Flights" and ensure it displays the filtered set.

### 2. Frontend Logic (`static/js/dashboard.js`)
- **Filtering Logic**: 
  - Implement a new filter function in `loadFlights()` that only shows flights where `STD` (Scheduled Time Departure) is within **+/- 1 hour** of the current time.
  - Update `loadDashboardSummary()` to handle the additional KPIs: `total_flights`, `total_aircraft`, `aircraft_utilization`.
- **Cleanup**: Remove `loadCrewList()` and its associated event listeners (e.g., crew search).

### 3. Navigation cleanup
- **Sidebar**: Remove the link to `/operations-overview`.
- **Redundancy**: Delete `templates/operations_overview.html`.

## Rationale
- **Focus**: The dashboard should prioritize immediate operational awareness (flights happening now) over general lists.
- **Performance**: Reducing the amount of data rendered (removing the long crew list) improves dashboard responsiveness.
- **Clarity**: Consolidating KPIs prevents users from switching between pages to see the full operational picture.

## Verification
- Verify that the Dashboard loads correctly without the Crew List.
- Verify that only flights within the current 2-hour window are displayed.
- Verify that all 7 KPIs update correctly.
