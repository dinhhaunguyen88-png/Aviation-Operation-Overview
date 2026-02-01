# Aviation Operations Dashboard (CMS)

Dashboard quản lý vận hành hàng không tích hợp dữ liệu phi hành đoàn (Crew) và chuyến bay từ hệ thống AIMS thông qua SOAP Web Service, với đầy đủ tính năng dự phòng và giám sát an toàn bay.

---

## 📋 Mục Lục

- [Yêu cầu Hệ thống & Mạng](#1-yêu-cầu-hệ-thống--mạng-prerequisites)
- [Cài đặt & Cấu hình](#2-cài-đặt--cấu-hình-installation)
- [Kết nối AIMS (Stable Connection)](#3-kết-nối-aims-stable-connection)
- [Xử lý Sự cố (Troubleshooting)](#4-xử-lý-sự-cố-troubleshooting)
- [Chế độ Dự phòng (CSV Fallback)](#5-chế-độ-dự-phòng-csv-fallback)
- [Quy trình Vận hành](#6-quy-trình-vận-hành)

---

## 1. Yêu cầu Hệ thống & Mạng (Prerequisites)

Để đảm bảo kết nối ổn định tới AIMS Web Service, môi trường triển khai cần đáp ứng:

### 1.1 Yêu cầu Mạng (Network)
- **IP Whitelisting:** Server IP phải được whitelist trên Firewall của AIMS Server.
- **VPN:** Nếu server nằm trong mạng nội bộ, yêu cầu VPN kết nối tới mạng AIMS.
- **Port:** Mở port `80` (HTTP) hoặc `443` (HTTPS) tới AIMS Server.
- **SSL/TLS:** Nếu AIMS dùng HTTPS, cần cài đặt Root CA Certificate trên server chạy Dashboard.

### 1.2 Yêu cầu Phần mềm
- **Python:** 3.10 trở lên.
- **Database:** PostgreSQL (Supabase).
- **Thư viện:** `zeep`, `flask`, `requests` (xem `requirements.txt`).

---

## 2. Cài đặt & Cấu hình (Installation)

### Bước 1: Clone & Install
```bash
git clone <repo-url>
cd aviation_operations_dashboard
pip install -r requirements.txt
```

### Bước 2: Cấu hình Môi trường (.env)
Tạo file `.env` và điền thông tin chính xác. **Lưu ý:** Username/Password của AIMS Web Service khác với tài khoản login AIMS Client.

```env
# AIMS Web Service (Check AIMS Option 7.1)
AIMS_WSDL_URL=http://aims.company.com/wtouch/AIMSWebService.exe/wsdl/IAIMSWebService
AIMS_WS_USERNAME=api_user_ws
AIMS_WS_PASSWORD=secure_password_123

# Database & App
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-key
FLASK_ENV=production
```

### Bước 3: Khởi tạo Database
```bash
python scripts/init_db.py
```

---

## 3. Kết nối AIMS (Stable Connection)

Để đảm bảo kết nối ổn định và tránh lỗi, hãy tuân thủ quy trình sau:

### 3.1 Kiểm tra WSDL Endpoint
Trước khi chạy Dashboard, hãy kiểm tra WSDL có truy cập được không:
```bash
# Thử curl tới WSDL URL (bỏ đuôi ?singlewsdl nếu cần)
curl -I http://aims.company.com/wtouch/AIMSWebService.exe/wsdl/IAIMSWebService
```
*Nếu trả về `200 OK`, kết nối mạng ổn định.*

### 3.2 Chạy Script Kiểm tra Kết nối
Sử dụng script `test_aims_connection.py` để verify toàn bộ quy trình auth và fetch data:

```bash
python scripts/test_aims_connection.py
```

**Kết quả mong đợi:**
```text
[OK] Connected to AIMS Web Service
[OK] Authentication successful
[OK] GetCrewList returned 150 records
```

### 3.3 Cơ chế Ổn định (Stability Mechanism)
Dashboard đã tích hợp sẵn:
- **Auto-Retry:** Tự động thử lại 3 lần nếu kết nối timeout.
- **Timeout Handling:** Set timeout 30s cho mỗi request.
- **Error Logging:** Ghi log chi tiết lỗi kết nối vào `app.log`.

---

## 4. Xử lý Sự cố (Troubleshooting)

Bảng mã lỗi thường gặp và cách khắc phục:

| Lỗi (Error) | Nguyên nhân | Cách khắc phục |
|-------------|-------------|----------------|
| `Connection timed out` | Firewall chặn hoặc sai IP | Kiểm tra VPN, whitelist IP, ping tới AIMS Server. |
| `Authentication failed` | Sai Username/Password | Reset mật khẩu trong AIMS Option 7.1. |
| `404 Not Found` (WSDL) | Sai URL Endpoint | Kiểm tra lại URL trong `.env`. Thử truy cập bằng trình duyệt. |
| `Certificate Verify Failed` | Thiếu SSL Cert | Thêm `session.verify = False` (chỉ dev) hoặc cài Cert đúng. |
| `Zero records returned` | Sai tham số lọc ngày | Kiểm tra múi giờ (UTC vs Local) và khoảng thời gian query. |

---

## 5. Chế độ Dự phòng (CSV Fallback)

Khi AIMS bảo trì hoặc mất kết nối, làm theo các bước sau để vận hành Dashboard bằng file CSV:

### Bước 1: Xuất báo cáo từ AIMS Client
Login vào AIMS Client và xuất các báo cáo sau ra định dạng CSV:
1. **Crew Hours:** Report `RolCrTotReport` (Total 28 days/12 months).
2. **Flights:** Report `DayRepReport` (Chuyến bay trong ngày).
3. **Roster:** Report `CrewRoster` (Lịch bay chi tiết).

### Bước 2: Upload lên Dashboard
1. Truy cập: `http://localhost:5000/data-etl`
2. Chọn tab **Manual Upload**.
3. Chọn file CSV tương ứng và bấm **Upload**.

### Bước 3: Chuyển nguồn dữ liệu
Dashboard sẽ tự động nhận diện dữ liệu mới nhất. Bạn cũng có thể ép buộc sử dụng chế độ CSV:
```bash
# API Switch manual
POST /api/config/datasource
{ "source": "CSV" }
```

---

## 6. Quy trình Vận hành

### Hàng ngày (Daily)
1. Kiểm tra Health Check: `https://dashboard-url/health`
2. Xem log sync AIMS: Đảm bảo job chạy mỗi 5 phút (Success).
3. Kiểm tra cảnh báo FTL: Review các Crew có cảnh báo Đỏ/Vàng.

### Hàng tuần (Weekly)
1. Review log lỗi: `app.log` hoặc Supabase log.
2. Backup dữ liệu quan trọng (nếu cần).
3. Update qualifications (Sync full).

---

## Tài liệu Tham khảo
Xem chi tiết trong thư mục `docs/`:
- `docs/API_SOAP_WebService.md`: Chi tiết đặc tả API.
- `docs/TÀI_LIỆU_ĐẶC_TẢ_KỸ_THUẬT_UPDATE.md`: Tài liệu kỹ thuật tổng thể.
