# Aircraft Swap Analysis - Ideas & Vision

## 📋 Mô tả
Hệ thống phân tích và theo dõi sự thay đổi tàu bay (Aircraft Swap) trong lịch bay, sử dụng dữ liệu thực tế từ AIMS Web Services. Dashboard Dark Mode hiển thị real-time swap events, reasons breakdown, và top impacted tail numbers.

## 🎯 Mục tiêu
- Phát hiện khi tàu bay được thay đổi so với kế hoạch ban đầu (FlightReg hiện tại ≠ FlightReg ban đầu)
- Theo dõi lý do swap từ AIMS Modification Log
- Tính toán KPIs: Total Swaps, Swap Rate, Recovery Rate, Avg Swap Time
- Hiển thị Swap Event Log và Top Impacted Tail Numbers

## 🔑 AIMS Methods Cần Dùng
| Method | # | Vai trò |
|--------|---|---------|
| FetchFlightsFrTo | #20 | Lấy FlightReg + FlightAcType hiện tại |
| FetchFlightDetails | #21 | Chi tiết chuyến bay cụ thể |
| FetchFlightChanges | #22 | Lịch sử thay đổi (previous_aircraft_reg) |
| FetchFlightModLog | #23 | Modification log (field_changed = aircraft_reg) |

## 🏗️ 3 Phase Execution
1. **Phase 1**: Data Ingestion & Swap Detection Logic
2. **Phase 2**: Backend Integration (FastAPI/Flask + SOAP Client)
3. **Phase 3**: UI Real-Time Dashboard

## Status: 🚧 Initialized
Đang trong giai đoạn lên kế hoạch. Workspace đã sẵn sàng.

---
*Created: 2026-02-12*
