# Phase 01: Data Ingestion & Swap Detection Logic
Status: ⬜ Pending
Dependencies: None (foundation exists)

## Objective
Xây dựng logic phát hiện Aircraft Swap bằng cách so sánh `aircraft_reg` hiện tại với bản ghi gốc, kết hợp dữ liệu từ `FlightScheduleModificationLog` (Method #23).

## AIMS Data Sources

### Primary: FlightDetailsForPeriod (Method #20)
- Đã có: `get_flights_range()` → trả về `aircraft_reg`, `aircraft_type` per flight
- Dữ liệu flight hiện tại (actual registration)

### Secondary: FlightScheduleModificationLog (Method #23)
- Đã có: `fetch_flight_mod_log()` → nhưng chỉ extract `status_desc`
- **CẦN ENHANCE**: Extract thêm field-level changes (old_value → new_value)
- Dùng để phát hiện khi `aircraft_reg` thay đổi

## Swap Detection Strategy

```
Strategy: "Snapshot Comparison"
─────────────────────────────────
1. Lần sync đầu tiên (T0): Lưu flights với aircraft_reg → bảng aims_flights
2. Lần sync tiếp theo (T1): So sánh aircraft_reg mới vs cũ
3. Nếu khác → Ghi nhận swap vào bảng aircraft_swaps
4. Bổ sung: Check aims_flight_mod_log cho reason context
```

## Implementation Steps

### Database
- [ ] 1. Tạo bảng `aircraft_swaps` trong Supabase
  ```sql
  CREATE TABLE aircraft_swaps (
      id SERIAL PRIMARY KEY,
      swap_event_id VARCHAR(20) UNIQUE NOT NULL,
      flight_date DATE NOT NULL,
      flight_number VARCHAR(20) NOT NULL,
      departure VARCHAR(10),
      arrival VARCHAR(10),
      original_reg VARCHAR(20) NOT NULL,
      swapped_reg VARCHAR(20) NOT NULL,
      original_ac_type VARCHAR(20),
      swapped_ac_type VARCHAR(20),
      swap_reason VARCHAR(100),
      swap_category VARCHAR(50),
      delay_minutes INT DEFAULT 0,
      recovery_status VARCHAR(50) DEFAULT 'PENDING',
      detected_at TIMESTAMPTZ DEFAULT NOW(),
      mod_log_ref TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
  );
  ```
- [ ] 2. Tạo bảng `aircraft_swap_snapshots` để lưu first-seen registration
  ```sql
  CREATE TABLE aircraft_swap_snapshots (
      id SERIAL PRIMARY KEY,
      flight_date DATE NOT NULL,
      flight_number VARCHAR(20) NOT NULL,
      departure VARCHAR(10) NOT NULL,
      first_seen_reg VARCHAR(20) NOT NULL,
      first_seen_ac_type VARCHAR(20),
      first_seen_at TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE(flight_date, flight_number, departure)
  );
  ```

### SOAP Client Enhancement
- [ ] 3. Enhance `fetch_flight_mod_log()` trong `aims_soap_client.py` để extract thêm fields:
  - `FltsSchedModLog_OldValue` / `FltsSchedModLog_NewValue`
  - `FltsSchedModLog_FieldChanged`
  - `FltsSchedModLog_ModifiedBy`
  - `FltsSchedModLog_ModifiedAt`

### ETL Manager
- [ ] 4. Tạo hàm `_detect_swaps()` trong `aims_etl_manager.py`
  - Compare current `aircraft_reg` vs `aircraft_swap_snapshots.first_seen_reg`
  - If different → INSERT vào `aircraft_swaps`
- [ ] 5. Tạo hàm `_update_snapshots()` trong `aims_etl_manager.py`
  - First sync of the day → save all flight registrations as snapshots
- [ ] 6. Tạo hàm `_enrich_swap_reasons()` 
  - Cross-reference `aims_flight_mod_log` logs to extract swap reason
  - Classify reason: Maintenance, Weather, Crew, Operational, AOG

### Swap Reason Classification
- [ ] 7. Logic phân loại reason từ `status_description`:
  ```python
  SWAP_CATEGORIES = {
      "MAINTENANCE": ["MEL", "AOG", "MAINT", "TECH", "DEFECT"],
      "WEATHER": ["WX", "WEATHER", "WIND", "FOG", "STORM"],
      "CREW": ["CREW", "SICK", "FTL", "PILOT", "FA"],
      "OPERATIONAL": ["DELAY", "SCHEDULE", "ROUTE", "OPS"],
  }
  ```

## Files to Create/Modify
- `scripts/db/create_swap_tables.sql` - [NEW] SQL schema
- `aims_soap_client.py` - [MODIFY] Enhance fetch_flight_mod_log()
- `aims_etl_manager.py` - [MODIFY] Add _detect_swaps(), _update_snapshots()
- `swap_detector.py` - [NEW] Standalone swap detection module

## Test Criteria
- [ ] Bảng `aircraft_swaps` và `aircraft_swap_snapshots` được tạo thành công
- [ ] `fetch_flight_mod_log()` trả về thêm field-level changes
- [ ] Swap detection logic phát hiện đúng khi reg thay đổi
- [ ] Reason classification hoạt động chính xác

---
Next Phase: [Phase 02 - Backend API](phase-02-backend-api.md)
