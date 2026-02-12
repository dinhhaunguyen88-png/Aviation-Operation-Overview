# Changelog

## [2026-02-12] - v1.4: Aircraft Swap Analysis

### Added
- **Aircraft Swap Analysis Feature**: End-to-end swap detection, classification, and dashboard visualization.
- **`swap_detector.py`** (418 lines): Core module with `detect_swaps()`, `classify_swap_reason()`, `calculate_swap_kpis()`, `get_reason_breakdown()`, `get_top_impacted_tails()`.
- **5 New API Endpoints**: `/api/swap/summary`, `/api/swap/events`, `/api/swap/reasons`, `/api/swap/top-tails`, `/api/swap/trend`. All secured with `@require_api_key`, cached 5min.
- **Frontend Dashboard**: `aircraft_swap.js` (320 lines) + updated `aircraft_swap.html`. KPI cards, reasons breakdown, top tails, event log with pagination, period selector, category filter, CSV export, auto-refresh 60s.
- **DB Schema**: `swap_events` + `swap_snapshots` tables (`scripts/db/create_swap_tables.sql`).
- **Test Suite**: `tests/test_swap.py` (45 pytest tests) + `tests/test_swap_quick.py` (21 validation tests). Total: 66 swap-specific tests, all passing.
- **Background Sync Integration**: Swap detection integrated into `sync_aims_data` scheduler job.

## [2026-02-12] - Supabase Pagination & FTL Smart Fallback

### Fixed
- **Supabase 1000-Row Limit**: Added `fetch_all_rows()` utility in `data_processor.py` — loops with `.range()` to paginate all large queries.
- **FTL Summary Capped at 1000**: `/api/ftl/summary` now uses `fetch_all_rows()` to return complete crew dataset (3299+ rows).
- **FTL CSV Export Incomplete**: `/api/ftl/export-csv` was missing crew beyond first batch. Fixed with same pagination utility.
- **FTL Display Showing Zeros**: Implemented `get_best_ftl_date()` smart fallback — picks latest date with >5 non-zero records, skipping broken sync data.

### Added
- **`fetch_all_rows()` Utility**: Reusable Supabase pagination helper. Applied to `/api/crew`, `/api/ftl/summary`, `/api/ftl/export-csv`.

## [2026-02-12] - FTL Crew List Major Fix

### Fixed
- **FTL Sort Showing All Zeros**: Supabase REST 1000-row limit caused only random 1000/3299 crew to load. Rewrote with **FTL-First strategy** — query `crew_flight_hours` directly (sorted + paginated in DB).
- **Base Filter Broken**: Trailing spaces in DB (`'SGN  '`) caused exact-match failure. Changed `eq()` → `ilike()`.
- **Position Filter Error**: `crew_members` table has no `position` column. Removed filter from UI + API.
- **SGN Base + Hours Sort**: Cross-table filter hit `in_()` URL length limit. Implemented **over-fetch + Python filter** (batch 200, join, filter, accumulate).

### Added
- **CXR Base Option**: Added to FTL list dropdown (235 crew).
- **Smart FTL Date Fallback**: `get_best_ftl_date()` picks latest date with actual non-zero data, avoiding broken sync zeros.
- **FTL Data Cleanup**: Script to remove fake crew (C001-C005) and 995 zero-value records.

### Changed
- **Dual Query Strategy**: `/api/crew` now uses FTL-First (sort by hours) or Crew-First (sort by name/id) depending on sort field.
- **FTL List UI**: Removed POS column header, adjusted colspan for empty states.

## [2026-02-11] - Cloudflare Tunnel Access & FTL List

### Added
- **FTL List Page**: New `/ftl-list` page with searchable, paginated crew FTL table. Filter by base, rank. CSV export via `/api/ftl/export-csv`.
- **Cloudflare Tunnel**: External dashboard access via `cloudflared.exe` tunnel with `X-API-Key` authentication.

### Fixed
- **Tunnel Data Access**: Frontend was not sending `X-API-Key` header to protected API endpoints, causing empty dashboard via tunnel.
- **Total Flight Completed KPI v4.3**: Date-aware logic — future dates show 0, past dates show all, today shows real-time.
- **Aircraft Status Logic**: Fixed incorrect status calculation for flights on non-today dates.
- **Test Suite (9 failures → 0)**: Added `X-API-Key` header to `test_api.py`, updated function signatures in `test_sync_logic.py`. 128/128 pass.

### Changed
- **Brain Knowledge Update**: Full `brain.json` refresh with 22 API endpoints, 8 frontend pages, infrastructure config.
- **Scripts Cleanup**: Reorganized `scripts/` — moved 12 essential files to `scripts/db/` and `scripts/sync/`, deleted 71 one-off debug scripts + 8 root temp files.

## [2026-02-10] - v1.3: 7-Day Window & Local Time Architecture

### Added
- **7-Day Data Window**: Expanded dashboard visibility to a rolling window from D-2 to D+4. Added `/api/data-window` endpoint.
- **Date Navigation UI**: Added ◀, ▶, and Today buttons to the dashboard header for seamless date switching.
- **Local Time Architecture v2.0**: Backend `data_processor.py` now pre-calculates local station times for all event fields (STD, STA, ETD, ETA, TKOF, TDWN, ATD, ATA) based on departure/arrival airport timezones.
- **v4.0.0 Project Knowledge**: Upgraded `.brain/brain.json` and session tracking to AWF v4.0 standard.

### Changed
- **Operational Focus Layout**: Reordered columns to a more logical sequence: `ATD -> TKof -> TDwn -> ATA`.
- **Version Indicator**: Updated sidebar footer to `v1.3` to verify deployment and avoid context confusion.

### Fixed
- **Stale Template Render**: Resolved issue where dashboard changes weren't applying by terminating stale backend processes on port 5000.
- **UTC Display**: All times in "Operational Focus" now correctly show Local Station Time instead of UTC.

## [2026-02-10] - Total Flights KPI Fix (filter_operational_flights v3.3)

### Fixed
- **Total Flights KPI Overcounting**: Reduced from +16 (536 vs 520 CSV ground truth) to +6 (526 vs 520). 521 of 520 CSV flights now matched correctly.
- **Phantom Flight Detection**: Implemented `prev_date_keys` heuristic to distinguish legitimate daily recurring flights from AIMS UTC-window artifacts.
- **filter_operational_flights v3.3**: Rule 1 includes same-date flights unless phantom (local STD next calendar day ≥04:00 AND no prev-date copy). Rule 2 excludes all prev-date flights. Rule 3 includes next-date flights with local STD <04:00.

### Analysis Scripts Added
- `compare_csv_system.py` - Compares DayRepReport CSV with system API output
- `analyze_phantoms.py` - Deep analysis of phantom flight root causes
- `deep_compare.py` - DB presence comparison across dates for phantom vs legitimate flights

## [2026-02-09] - Flight Time Display Fix

### Fixed
- **Local Time Conversion**: Flights in Aircraft Operating Today section now display local station time instead of UTC.

## [2026-02-04] - Bulk FTL API & AIMS Sync Reliability

### Added
- **Bulk FTL API**: New endpoint `GET /api/crew/top-stats` for efficient 28-day flight hour calculation.
- **API Caching**: 15-minute TTL caching for FTL stats, improving response time significantlly (3.2s -> 0.01s).
- **AIMS Fallback Sync**: Implemented automated fallback to individual flight syncs when AIMS Bulk API fails.
- **Documentation**: New `docs/api/endpoints.md` for API specifications.

### Changed
- **AIMS Soap Client**: Refactored `get_leg_members` with deep unwrap logic to handle complex AIMS response nesting.
- **Robust Extraction**: Added multi-attribute extraction helper to handle varying AIMS field names (`id`, `crew_id`, `cid` etc.).

### Fixed
- **Sync Failures**: Resolved persistent issue of zero records being synced for leg members by correcting SOAP response attribute paths.

## [2026-02-01] - KPI Refinement & Dashboard Stabilization

### Added
- **KPI: A/C Type Hour**: Detailed breakdown of block hours (e.g., A321: 400h).
- **KPI: Total Flight Completed**: Success metric replacing "Sick Leave", counting flights with ATA/On-Block.
- **Operations Day**: Logic to filter metrics from 04:00 to 03:59 next day.

### Changed
- **OTP Logic**: Now calculates percentage based only on Completed Flights `(OnTime / Completed)`.
- **Dashboard Layout**: Reorganized KPIs into a balanced 4x2 grid.
- **Pulse Chart**: Improved time parsing to handle `HH:MM:SS` and display accurate hourly operational pulse.
- **Crew Chart**: Added logic to infer status from `crew_data` when `standby_summary` is missing.

### Fixed
- **Data Parsing**: Added fallback logic for `block_hours` (calculated from On/Off blocks) and `completion` (fallback to Gate Arrival) to resolve 0-value issues.
