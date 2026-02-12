# Phase 03: UI Real-Time Dashboard
Status: ✅ Complete
Dependencies: Phase 02 (Backend API)

## Objective
Wire up `aircraft_swap.html` template từ static mockup sang dynamic data. Giữ nguyên Dark Mode design đã có.

## UI Components (Existing → Wire Up)

### 1. KPI Summary Cards (4 cards)
- Total Swaps → `GET /api/swap/summary`
- Impacted Flights → `GET /api/swap/summary`
- Avg Swap Time → `GET /api/swap/summary`
- Recovery Rate → `GET /api/swap/summary`
- Trend indicator (↑/↓) so với previous period

### 2. Swap Reasons Breakdown (Horizontal Bar)
- Dùng data từ `GET /api/swap/reasons`
- Dynamic width bars thay vì hardcoded %
- Color-coded by category

### 3. Top Impacted Tail Numbers (Ranked List)
- Dùng data từ `GET /api/swap/top-tails`
- Severity badge: Critical (red), High (orange), Normal (green)
- Show aircraft type next to registration

### 4. Swap Event Log (Data Table)
- Dùng data từ `GET /api/swap/events`
- Columns: Event ID, Flight, Original A/C, Swapped A/C, Reason, Impact, Status
- Pagination controls
- Filter button (by category)
- Color-coded reason badges & status badges

### 5. Period Selector (24h / 7d / 30d)
- Toggle buttons affect all API calls
- Active state highlight

### 6. Export Button
- Export swap events to CSV

## Implementation Steps
- [ ] 1. Tạo `static/js/aircraft_swap.js` - Main JS controller
- [ ] 2. Wire KPI cards to API data with loading states
- [ ] 3. Wire reasons breakdown with dynamic bar widths
- [ ] 4. Wire top tails ranked list
- [ ] 5. Wire swap event log table with pagination
- [ ] 6. Implement period selector (24h/7d/30d)
- [ ] 7. Implement filter by category
- [ ] 8. Add auto-refresh (60 seconds)
- [ ] 9. Add CSV export functionality
- [ ] 10. Update `aircraft_swap.html` template (remove hardcoded data)

## Files to Create/Modify
- `static/js/aircraft_swap.js` - [NEW] Dashboard controller
- `templates/aircraft_swap.html` - [MODIFY] Remove hardcoded, add dynamic bindings

## Test Criteria
- [ ] Dashboard loads without errors
- [ ] KPI cards show real data
- [ ] Period selector updates all sections
- [ ] Swap log table paginates correctly
- [ ] Export CSV downloads file
- [ ] Auto-refresh works every 60s
- [ ] Dark mode theming consistent

---
Next Phase: [Phase 04 - Testing](phase-04-testing.md)
