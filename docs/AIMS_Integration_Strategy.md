# Hướng Dẫn Tích Hợp Chi Tiết Dữ Liệu AIMS (API Strategy)

Tài liệu này hướng dẫn chi tiết cách khai thác toàn bộ dữ liệu từ AIMS Web Services để hiển thị đầy đủ các chỉ số Chuyến bay (Flight) và Phi hành đoàn (Crew), dựa trên cấu trúc WSDL hiện tại của hệ thống.

## 1. Hiện Trạng & Vấn Đề
Qua quá trình debug, chúng ta đã xác định được:
- **Đã kết nối thành công:** `GetCrewList` (Lấy danh sách phi hành đoàn cơ bản).
- **Bị chặn quyền (Invalid Credentials):** `CrewMemberRosterDetailsForPeriod` (Lịch bay) và `FlightDetailsForPeriod` (Thông tin chuyến bay chi tiết).
- **Phương thức không tồn tại:** `FetchDayFlights`, `FetchFlightsFrTo` (Cần thay thế bằng `FlightDetails*`).

## 2. Chiến Lược Lấy Dữ Liệu Chi Tiết

Để có "đầy đủ các chỉ số", chúng ta cần kích hoạt và sử dụng các nhóm hàm sau:

### A. Nhóm Chỉ Số Phi Hành Đoàn (Crew Metrics)
Để tính toán FTL (Flight Time Limitations), Block Hours, Duty Time, bạn cần 3 dòng dữ liệu chính:

1.  **Thông Tin Cơ Bản (Đã OK):**
    - **API:** `GetCrewList`
    - **Dữ liệu:** Crew ID, Name, Rank, Base, Contact.
    - **Trạng thái:** ✅ Đang hoạt động.

2.  **Lịch Bay & Nhiệm Vụ (Roster):**
    - **API:** `CrewMemberRosterDetailsForPeriod`
    - **Mục đích:** Biết crew làm gì vào ngày nào (Bay, Off, Training, Standby).
    - **Dữ liệu trả về (Dự kiến):**
        - `DutyCode`: Mã nhiệm vụ (FLT, OFF, SBY...)
        - `Dep/Arr`: Sân bay đi/đến.
        - `Std/Sta`: Giờ dự kiến.
        - `AcType/AcReg`: Loại máy bay.
    - **Hành động cần làm:** Yêu cầu IT/AIMS Admin cấp quyền cho hàm này.

3.  **Giờ Bay Thực Tế (Actuals):**
    - **API:** `FlightDetailsForPeriod` (Lọc theo Crew) hoặc phân tích từ `CrewMemberRosterDetailsForPeriod` (nếu có actuals).
    - **Mục đích:** Tính giờ bay thực tế (Block Time) để cảnh báo FTL (28 days, 12 months).
    - **Dữ liệu:** `BlockOff`, `BlockOn`, `TakeOff`, `Landing`.

### B. Nhóm Chỉ Số Chuyến Bay (Flight Metrics)
Để hiển thị bảng theo dõi chuyến bay (Live Ops):

1.  **Danh Sách Chuyến Bay (Schedule & Actuals):**
    - **API:** `FlightDetailsForPeriod`
    - **Tham số:** `FromDD/MM/YYYY` đến `ToDD/MM/YYYY`.
    - **Dữ liệu chi tiết trả về:**
        - `FltNo`, `Date`
        - `Dep`, `Arr` (Station)
        - `STD`, `STA` (Scheduled Times)
        - `ETD`, `ETA` (Estimated Times)
        - `ATD`, `ATA` (Actual Times)
        - `BlockTime`, `FlightTime`
        - `DelayCodes`, `DelayMinutes` (Để phân tích On-Time Performance - OTP)
        - `PaxFigures` (Số lượng khách - nếu có quyền)

## 3. Hướng Dẫn Yêu Cầu Quyền (Permission Request)
Hiện tại User API đang dùng (`vietjet_api` hoặc tương tự) **chỉ có quyền** `GetCrewList`. Bạn cần gửi email cho bộ phận quản trị AIMS (AIMS Administrator) với nội dung sau:

> "Please grant execution permissions within AIMS User Administration (Option 7.1) for the following Web Service methods for our API user:
> 1. `CrewMemberRosterDetailsForPeriod` (For fetching crew schedules)
> 2. `FlightDetailsForPeriod` (For fetching flight actuals and delay codes)
>
> We are currently receiving 'Invalid credentials' errors when calling these specific methods, while `GetCrewList` works fine."

## 4. Kế Hoạch Cập Nhật Code (Sau khi có quyền)

Tôi sẽ tạo các kết nối API mới trong `aims_soap_client.py` tương ứng với các hàm đã tìm thấy trong WSDL:

### 4.1 Cập nhật `get_flight_details`
Thay thế phương thức cũ bằng cấu trúc tham số đúng của `FlightDetailsForPeriod`:

```python
def get_flight_details(self, start_date, end_date):
    # Cấu trúc đã verify từ WSDL
    response = self.client.service.FlightDetailsForPeriod(
        UN=self.username, PSW=self.password,
        FromDD=..., FromMMonth=..., FromYYYY=..., 
        FromHH="00", FromMMin="00",
        ToDD=..., ToMMonth=..., ToYYYY=..., 
        ToHH="23", ToMMin="59"
    )
    return response.FlightList # Hoặc trường tương ứng
```

### 4.2 Cấu Trúc Database Mở Rộng
Để lưu "Full Info", chúng ta cần mở rộng bảng `flights` trong Supabase (`scripts/supabase_schema.sql`):

```sql
ALTER TABLE flights ADD COLUMN IF NOT EXISTS std timestamp with time zone;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS sta timestamp with time zone;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS etd timestamp with time zone;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS eta timestamp with time zone;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS off_block timestamp with time zone; -- Block Off
ALTER TABLE flights ADD COLUMN IF NOT EXISTS on_block timestamp with time zone;  -- Block On
ALTER TABLE flights ADD COLUMN IF NOT EXISTS delay_code_1 text;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS delay_time_1 integer; -- Minutes
ALTER TABLE flights ADD COLUMN IF NOT EXISTS pax_total integer;
```

## 5. Tổng Kết
Để có đầy đủ thông tin:
1.  **Ngay lập tức:** Gửi yêu cầu mở quyền API cho 2 hàm `CrewMemberRosterDetailsForPeriod` và `FlightDetailsForPeriod`.
2.  **Sau khi có quyền:** Báo lại cho tôi, tôi sẽ chạy lại script `manual_sync.py` để lấy dữ liệu.
3.  **Mở rộng:** Nếu cần thông tin chi tiết hơn nữa (như qualifications, training), chúng ta sẽ kết nối thêm `FetchCrewQuals`.
