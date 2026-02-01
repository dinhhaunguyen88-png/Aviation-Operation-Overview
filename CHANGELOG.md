# Changelog

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
