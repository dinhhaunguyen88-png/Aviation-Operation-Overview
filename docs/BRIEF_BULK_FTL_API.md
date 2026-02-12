# 💡 BRIEF: AIMS Bulk FTL Reports API

**Ngày tạo:** 2026-02-04
**Vấn đề:** N+1 Problem khi tính 28-day flight hours (phải loop từng crew để fetch AIMS/DB).
**Giải pháp:** Sử dụng Database Aggregation (GROUP BY) trên các bảng AIMS mới và áp dụng Caching.

---

## 1. VẤN ĐỀ CẦN GIẢI QUYẾT
- Hiện tại Dashboard phải loop từng Crew để tính giờ bay, gây chậm trễ (latency cao) và tải nặng cho DB/API.
- Việc tính toán này lặp đi lặp lại không cần thiết khi dữ liệu không thay đổi liên tục.

## 2. GIẢI PHÁP ĐỀ XUẤT
- Tạo một Endpoint mới: `GET /api/crew/top-stats`
- **Logic Backend**:
    - Thực hiện JOIN bảng `aims_leg_members` và `aims_flights`.
    - Tính `SUM(block_time_minutes)` theo `crew_id`.
    - Lọc dữ liệu trong vòng 28 ngày qua.
    - Sắp xếp và lấy Top 20.
- **Caching**: Lưu kết quả vào memory/cache trong 15 phút.

## 3. CẤU TRÚC DỮ LIỆU (Query SQL Dự kiến)
```sql
SELECT 
    l.crew_id,
    MAX(l.crew_name) as crew_name,
    MAX(l.position) as position,
    ROUND(SUM(f.block_time_minutes)::numeric / 60, 2) as total_hours
FROM aims_leg_members l
JOIN aims_flights f ON 
    l.flight_date::date = f.flight_date::date 
    AND l.flight_number = f.flight_number 
    AND l.departure = f.departure
WHERE l.flight_date::date >= CURRENT_DATE - INTERVAL '28 days'
GROUP BY l.crew_id
ORDER BY total_hours DESC
LIMIT 20;
```

## 4. TÍNH NĂNG (Features)

### 🚀 MVP (Bắt buộc có):
- [ ] Endpoint `/api/crew/top-stats?days=28&limit=20`.
- [ ] Logic cache 15 phút.
- [ ] Trả về schema đúng format Dashboard.

### 🎁 Phase 2 (Làm sau):
- [ ] Thêm filter theo `position` (CP, FO, FA...).
- [ ] Tích hợp cảnh báo (Threshold 100h) trực tiếp vào Response.

---

## 5. ƯỚC TÍNH SƠ BỘ
- **Độ phức tạp:** Thấp (Dễ thực hiện vì đã có schema chuẩn).
- **Rủi ro:** Cần đảm bảo `aims_flights` và `aims_leg_members` được sync đầy đủ (đã có ETL Manager lo phần này).

## 6. BƯỚC TIẾP THEO
→ Chạy `/plan` để triển khai Endpoint và tích hợp logic Cache.
