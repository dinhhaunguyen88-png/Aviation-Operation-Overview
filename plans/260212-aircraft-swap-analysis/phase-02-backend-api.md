# Phase 02: Backend API Endpoints
Status: ⬜ Pending
Dependencies: Phase 01 (Database + Detection Logic)

## Objective
Xây dựng REST API endpoints trong `api_server.py` để cung cấp dữ liệu swap cho dashboard.

## API Endpoints

### GET `/api/swap/summary`
KPI tổng hợp cho dashboard header.
```json
{
  "total_swaps": 42,
  "impacted_flights": 117,
  "avg_swap_time_hours": 3.2,
  "recovery_rate": 94.2,
  "trend_vs_last_period": 8.2
}
```

### GET `/api/swap/events`
Danh sách swap events, hỗ trợ filter và pagination.
```
Params: ?period=7d|24h|30d&page=1&per_page=10&category=MAINTENANCE
```
```json
{
  "events": [
    {
      "swap_event_id": "SW-0024",
      "flight_date": "2026-02-12",
      "flight_number": "VN102",
      "departure": "SGN",
      "arrival": "HAN",
      "original_reg": "VN-A888",
      "swapped_reg": "VN-A899",
      "swap_reason": "Maintenance",
      "delay_minutes": -45,
      "recovery_status": "Recovered"
    }
  ],
  "total": 42,
  "page": 1
}
```

### GET `/api/swap/reasons`
Breakdown by category cho bar chart.
```json
{
  "reasons": [
    {"category": "Maintenance", "count": 19, "percentage": 45},
    {"category": "Weather", "count": 11, "percentage": 25},
    {"category": "Crew", "count": 8, "percentage": 18},
    {"category": "Operational", "count": 5, "percentage": 12}
  ]
}
```

### GET `/api/swap/top-tails`
Top impacted tail numbers.
```json
{
  "tails": [
    {"reg": "VN-A888", "ac_type": "A350-900", "swap_count": 12, "severity": "Critical"},
    {"reg": "VN-A391", "ac_type": "B787-10", "swap_count": 8, "severity": "High"},
    {"reg": "VN-A672", "ac_type": "A321neo", "swap_count": 6, "severity": "Normal"}
  ]
}
```

### GET `/api/swap/trend`
Swap trend over time cho timeline chart.
```json
{
  "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  "datasets": { "swaps": [5, 8, 3, 7, 6, 4, 9] }
}
```

## Implementation Steps
- [ ] 1. Add route `/aircraft-swap` → render template `aircraft_swap.html`
- [ ] 2. Implement `GET /api/swap/summary` with caching (5min TTL)
- [ ] 3. Implement `GET /api/swap/events` with pagination
- [ ] 4. Implement `GET /api/swap/reasons` aggregation query
- [ ] 5. Implement `GET /api/swap/top-tails` aggregation query
- [ ] 6. Implement `GET /api/swap/trend` timeline query
- [ ] 7. Add `@require_api_key` decorator to all swap endpoints
- [ ] 8. Add `ErrorExplanation` handling in AIMS calls
- [ ] 9. Integrate swap sync into background scheduler (`sync_aims_data`)

## Files to Create/Modify
- `api_server.py` - [MODIFY] Add 5 new endpoints + route
- `data_processor.py` - [MODIFY] Add swap aggregation functions

## Test Criteria
- [ ] All endpoints return valid JSON with correct structure
- [ ] Period filter (24h, 7d, 30d) works correctly
- [ ] Pagination works for swap events
- [ ] API key authentication applied to all endpoints
- [ ] Caching works (5min TTL for summary)

---
Next Phase: [Phase 03 - Frontend Dashboard](phase-03-frontend-ui.md)
