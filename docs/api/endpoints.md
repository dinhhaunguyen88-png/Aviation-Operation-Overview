# API Documentation

Ngày cập nhật: 2026-02-04
Base URL: `http://localhost:5000`

---

## 👨‍✈️ Crew & FTL

### GET /api/crew/top-stats
Lấy danh sách top phi hành đoàn theo giờ bay (FTL) trong khoảng thời gian xác định. API này sử dụng cơ chế dồn dữ liệu (bulk aggregation) và caching để đảm bảo hiệu năng.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| days | number | 28 | Khoảng thời gian nhìn lại (về phía quá khứ) tính từ hôm nay. |
| limit | number | 20 | Số lượng bản ghi tối đa trả về. |
| threshold | number | 100.0 | Ngưỡng cảnh báo giờ bay (dùng để xác định `warning_level`). |

**Caching:**
- **TTL**: 15 phút (900 giây).
- **Key Prefix**: `ftl_top`.
- Hiệu năng: Giảm thời gian phản hồi từ ~3 giây xuống ~0.01 giây khi hit cache.

**Response (200):**
```json
{
  "success": true,
  "timestamp": "2026-02-04T16:40:00.000000",
  "data": [
    {
      "crew_id": "7066",
      "crew_name": "BEDE NIKOLAI LASMARIAS JA",
      "position": "CP",
      "hours_28_day": 23.73,
      "warning_level": "NORMAL"
    },
    ...
  ]
}
```

**Implementation Detail:**
- Thực hiện join giữa bảng `aims_leg_members` và `aims_flights` trên database.
- Tự động fallback đồng bộ từng chuyến bay nếu API Bulk của AIMS không có dữ liệu.
