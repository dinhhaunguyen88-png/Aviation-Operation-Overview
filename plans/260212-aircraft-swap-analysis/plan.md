# Plan: Aircraft Swap Analysis
Created: 2026-02-12
Status: 🟡 In Progress

## Overview
Xây dựng hệ thống phát hiện và phân tích Aircraft Swap (thay đổi tàu bay) bằng dữ liệu từ AIMS Web Services. Dashboard Dark Mode hiển thị real-time swap events, KPIs, và analytics.

## Tech Stack
- Backend: Python Flask (existing) + Zeep SOAP Client (existing)
- Frontend: HTML/CSS/JS Vanilla (existing pattern)
- Database: PostgreSQL/Supabase (existing)
- Charts: Chart.js (existing)

## Phases

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 01 | Data Ingestion & Swap Detection | ✅ Complete | 100% |
| 02 | Backend API Endpoints | ✅ Complete | 100% |
| 03 | UI Real-Time Dashboard | ✅ Complete | 100% |
| 04 | Testing & Verification | ✅ Complete | 100% |

## Existing Assets (Reuse)
- `aims_soap_client.py` → `get_flights_range()`, `fetch_flight_mod_log()`
- `aims_etl_manager.py` → `_sync_flights()`, `_sync_flight_mod_log()`
- `schema_aims_full.sql` → `aims_flights`, `aims_flight_mod_log`, `aims_flight_schedule_changes`
- `templates/aircraft_swap.html` → Static mockup (to be wired up)

## Quick Commands
- Start Phase 1: `/code phase-01`
- Check progress: `/next`
- Save context: `/save-brain`
