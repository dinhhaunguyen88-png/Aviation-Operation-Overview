# SPECS: Dashboard Operations Consolidation

## 1. Executive Summary
Hợp nhất toàn bộ thông tin vận hành quan trọng vào một màn hình duy nhất. Dashboard mới sẽ tập trung vào sự linh hoạt của phi hành đoàn (Crew) và tình trạng các chuyến bay đang diễn ra (Flights).

## 2. User Roles
- **Operations Manager**: Theo dõi toàn bộ bức tranh vận hành.
- **Crew Coordinator**: Điều phối phi hành đoàn dự phòng dựa trên lịch bay thực tế.

## 3. UI/UX Changes
- **Header**: Giữ nguyên.
- **KPI Row**: Mở rộng từ 4 thẻ lên 7 thẻ:
    1. **Total Crew**: Tổng số nhân sự đang trực.
    2. **Standby**: Nhân sự dự phòng sẵn sàng.
    3. **Sick Leave**: Nhân sự nghỉ ốm (Cảnh báo).
    4. **Total Flights**: Tổng số chuyến bay trong ngày.
    5. **Active AC**: Số tàu bay đang hoạt động.
    6. **Block Hours**: Tổng số giờ bay tích lũy.
    7. **Utilization**: Hiệu suất sử dụng tàu bay.
- **Main Section**: 
    - Loại bỏ Panel "Crew List".
    - Mở rộng "Active Flights" để chiếm không gian diện tích lớn hơn.
- **Filtering**: Bảng chuyến bay chỉ hiển thị các chuyến có `STD` trong khoảng `Giờ hiện tại - 1h` đến `Giờ hiện tại + 1h`.

## 4. Technical Architecture
- **Frontend**: Vanilla JS (`dashboard.js`) + CSS Grid/Flexbox.
- **Backend API**: Sử dụng các endpoint hiện có:
    - `/api/dashboard/summary`: Trả về toàn bộ 7 chỉ số KPI.
    - `/api/flights`: Lấy danh sách chuyến bay để lọc ở Frontend.

## 5. Logic Flow
1. Trang dashboard load.
2. Gọi đồng thời dữ liệu Summary và Flights.
3. JS tính toán thời gian hiện tại.
4. Filter danh sách Flights dựa trên logic +/- 1 giờ.
5. Render dữ liệu lên UI.

## 6. Build Checklist
- [ ] Xóa `operations_overview.html`.
- [ ] Cập nhật `sidebar.html` (Xóa link redundant).
- [ ] Sửa `crew_dashboard.html` (Layout KPI & Table).
- [ ] Sửa `dashboard.js` (Fetch Summary logic & Flight Filter logic).
