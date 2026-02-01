# Phase 02: UI Layout Update
Status: ⬜ Pending

## Objective
Redesign the main dashboard to include all 7 KPIs and remove the Crew List table.

## Requirements
- 7 KPI cards in the header row.
- No Crew List panel.
- Expanded Flight Table panel.

## Implementation Steps
1. [ ] Update `templates/crew_dashboard.html` to add 3 new KPI cards (Total Flights, Active AC, Utilization).
2. [ ] Adjust CSS grid for 7-column or multi-row KPI display.
3. [ ] Remove the Crew List `<section>` from `templates/crew_dashboard.html`.
4. [ ] Adjust the layout of the remaining panels (Flights, FTL, Standby) for better space utilization.

## Files to Create/Modify
- `templates/crew_dashboard.html` - Modify
- `static/css/dashboard.css` - Modify (if needed for layout)

## Test Criteria
- 7 KPIs are visible and styled correctly.
- Dashboard feels balanced without the Crew List.
