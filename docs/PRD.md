# Product Requirements Document (PRD)
## Aviation Operations Dashboard - AIMS Integration

**Version:** 1.0  
**Ngày:** 30/01/2026  
**Tác giả:** Crew Management Team

---

## 1. Tổng Quan Sản Phẩm

### 1.1 Vision
Xây dựng Dashboard quản lý vận hành hàng không tích hợp dữ liệu real-time từ AIMS (Airline Information Management System) thông qua SOAP Web Service, cung cấp cái nhìn toàn diện về crew scheduling, flight operations và fleet status.

### 1.2 Business Objectives
| Mục tiêu | Chỉ số đo lường | Target |
|----------|-----------------|--------|
| Giảm thời gian tra cứu crew | Thời gian trung bình | < 5 giây |
| Tăng độ chính xác scheduling | Tỷ lệ conflict giảm | -30% |
| Cải thiện compliance monitoring | Automated alerts | 100% FTL violations |

---

## 2. User Personas

### 2.1 Operations Manager
- **Vai trò:** Giám sát tổng thể hoạt động bay hàng ngày
- **Nhu cầu:** Dashboard tổng quan, alerts realtime, báo cáo nhanh
- **Pain points:** Dữ liệu phân tán, mất thời gian tổng hợp

### 2.2 Crew Scheduler
- **Vai trò:** Lập lịch và điều phối phi hành đoàn
- **Nhu cầu:** Crew availability, qualification check, FTL monitoring
- **Pain points:** Manual tracking, thiếu visibility về crew status

### 2.3 Flight Dispatcher
- **Vai trò:** Quản lý flight operations
- **Nhu cầu:** Flight details, delays tracking, aircraft status
- **Pain points:** Chậm cập nhật thông tin thay đổi

---

## 3. User Stories

### Epic 1: Dashboard Overview
| ID | User Story | Acceptance Criteria | Priority |
|----|------------|---------------------|----------|
| US-001 | Như Operations Manager, tôi muốn xem tổng quan số crew đang hoạt động theo ngày | Hiển thị số crew by position (PIC, FO, CC) | Must |
| US-002 | Như Operations Manager, tôi muốn xem số chuyến bay theo thời gian thực | Cập nhật mỗi 5 phút từ AIMS | Must |
| US-003 | Như Crew Scheduler, tôi muốn filter crew theo base và aircraft type | Filter dropdown hoạt động chính xác | Must |

### Epic 2: Crew Management
| ID | User Story | Acceptance Criteria | Priority |
|----|------------|---------------------|----------|
| US-010 | Như Scheduler, tôi muốn xem chi tiết roster của một crew member | Hiển thị toàn bộ duties trong period | Must |
| US-011 | Như Scheduler, tôi muốn biết crew nào đang SBY/SL/CSL | Status được highlight rõ ràng | Must |
| US-012 | Như Manager, tôi muốn track check-in/check-out của crew | Log thời gian check-in/out | Should |

### Epic 3: Flight Operations
| ID | User Story | Acceptance Criteria | Priority |
|----|------------|---------------------|----------|
| US-020 | Như Dispatcher, tôi muốn xem danh sách flights theo ngày | List flights với STD/STA, ETD/ETA | Must |
| US-021 | Như Dispatcher, tôi muốn theo dõi delays | Delay code và thời gian hiển thị | Must |
| US-022 | Như Manager, tôi muốn xem flight hour limits của crew | Cảnh báo khi tiến gần 28-day/12-month limit | Must |

### Epic 4: Safety Compliance
| ID | User Story | Acceptance Criteria | Priority |
|----|------------|---------------------|----------|
| US-030 | Như Safety Officer, tôi muốn monitor FDP violations | Alert khi FDP > maximum allowed | Must |
| US-031 | Như Manager, tôi muốn track crew qualifications expiry | Warning 30 ngày trước expiry | Should |

---

## 4. Feature Requirements

### 4.1 Dashboard Views
```
┌─────────────────────────────────────────────────────────┐
│  Aviation Operations Dashboard                          │
├─────────────────────────────────────────────────────────┤
│  [Date Picker] [Base Filter] [Aircraft Filter] [Refresh]│
├─────────────┬───────────────┬───────────────┬──────────┤
│ Total Crew  │ Active Flights│ A/C Utilization│ Alerts  │
│    127      │      45       │   8.5 hrs/day  │   3 ⚠️   │
├─────────────┴───────────────┴───────────────┴──────────┤
│  Crew Status Table                                      │
│  ┌──────┬──────────┬────────┬────────────────────┐     │
│  │ ID   │ Name     │ Status │ Current Assignment │     │
│  ├──────┼──────────┼────────┼────────────────────┤     │
│  │ 1001 │ Nguyen A │ FLY    │ VN123 SGN-HAN     │     │
│  └──────┴──────────┴────────┴────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Data Integration Features
- **Real-time sync:** Polling AIMS API mỗi 5 phút
- **Fallback mode:** Hỗ trợ CSV upload khi AIMS không khả dụng
- **Data source toggle:** Chuyển đổi giữa AIMS/CSV
- **Historical data:** Lưu trữ 60 ngày cho trending analysis

### 4.3 Alert System
| Alert Type | Trigger Condition | Notification |
|------------|-------------------|--------------|
| FTL Warning | 28-day hours > 85% limit | Dashboard + Email |
| Qualification Expiry | < 30 days to expire | Dashboard |
| Crew Not Checked-in | 60 mins before STD | Dashboard alert |
| Flight Delay | Delay > 30 mins | Dashboard highlight |

---

## 5. Non-Functional Requirements

### 5.1 Performance
- Dashboard load time: < 3 seconds
- API response time: < 2 seconds
- Concurrent users: 50+

### 5.2 Security
- AIMS credentials encrypted at rest
- HTTPS for all communications
- Role-based access control (RBAC)

### 5.3 Availability
- Uptime target: 99.5%
- Graceful degradation khi AIMS offline

---

## 6. Success Metrics

| KPI | Baseline | Target | Measurement |
|-----|----------|--------|-------------|
| Time to find crew info | 2-3 mins | < 10 secs | User testing |
| Manual data entry reduction | - | -80% | Process audit |
| FTL violation detection | 70% | 100% | Compliance reports |
| User satisfaction | - | > 4.0/5.0 | Survey |

---

## 7. Out of Scope (Version 1.0)
- Mobile application
- Crew self-service portal
- Automated crew pairing optimization
- Integration với hệ thống Payroll

---

## 8. Timeline & Milestones

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Core Dashboard | 4 weeks | Basic views, AIMS connection |
| Phase 2: Crew Features | 3 weeks | Roster view, FTL tracking |
| Phase 3: Flight Ops | 3 weeks | Flight monitoring, delays |
| Phase 4: Alerts & Reports | 2 weeks | Alert system, export features |

---

## 9. Stakeholders

| Role | Name | Responsibility |
|------|------|----------------|
| Product Owner | Operations Director | Requirements approval |
| Tech Lead | IT Manager | Technical decisions |
| End Users | Ops team | Testing & feedback |

---

## Appendix A: Glossary
- **AIMS:** Airline Information Management System
- **FTL:** Flight Time Limitations
- **FDP:** Flight Duty Period
- **PIC:** Pilot in Command
- **FO:** First Officer
- **SBY:** Standby
- **SL:** Sick Leave
- **CSL:** Call Sick
