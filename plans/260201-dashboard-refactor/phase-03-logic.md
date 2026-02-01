# Phase 03: Logic & Filtering
Status: ⬜ Pending

## Objective
Implement the +/- 1-hour flight filter and populate the new KPIs.

## Requirements
- Flight list filtered by `STD` relative to `now`.
- All 7 KPIs reflecting real data from `api_server.py`.

## Implementation Steps
1. [ ] Update `loadDashboardSummary()` in `dashboard.js` to map the new flight KPIs.
2. [ ] Implement `filterFlightsByTime()` function in `dashboard.js`.
3. [ ] Update `loadFlights()` to use the new filter before rendering.
4. [ ] Remove `loadCrewList()` code and event listeners to keep the codebase clean.

## Files to Create/Modify
- `static/js/dashboard.js` - Modify

## Test Criteria
- Only flights within +/- 1 hour of the current system time are shown.
- All 7 KPI values match the API output.
- No console errors from removed crew list functions.
