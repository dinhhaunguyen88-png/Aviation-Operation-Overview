# Aviation Operations Dashboard
## AIMS SOAP Web Service Integration

Dashboard quản lý vận hành hàng không tích hợp dữ liệu phi hành đoàn (Crew) và chuyến bay từ hệ thống AIMS thông qua SOAP Web Service.

---

## 📋 Mục Lục

- [Phase 1: Foundation Setup](#phase-1-foundation-setup)
- [Phase 2: Data Integration](#phase-2-data-integration)
- [Phase 3: Core Features](#phase-3-core-features)
- [Phase 4: Advanced Features](#phase-4-advanced-features)
- [Phase 5: Testing & Deployment](#phase-5-testing--deployment)

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python Flask |
| Database | Supabase (PostgreSQL) |
| Frontend | HTML/CSS/JavaScript |
| API Integration | AIMS SOAP/WSDL (zeep) |
| Hosting | Render/Vercel |

---

## Phase 1: Foundation Setup
**Objective:** Thiết lập project structure và kết nối cơ sở dữ liệu.

### Prerequisites
```bash
# Python 3.10+
python --version

# Node.js 18+ (optional for frontend tooling)
node --version
```

### Step 1.1: Clone Repository
```bash
git clone <repository-url>
cd aviation_operations_dashboard
```

### Step 1.2: Install Dependencies
```bash
pip install -r requirements.txt
```

**Required packages:**
```
flask>=2.3.0
supabase>=2.0.0
zeep>=4.2.1
python-dotenv>=1.0.0
pdfplumber>=0.10.0
apscheduler>=3.10.0
```

### Step 1.3: Environment Configuration
```bash
# Tạo file .env từ template
cp .env.example .env
```

**Configure .env:**
```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-key

# AIMS API
AIMS_WSDL_URL=http://aims.company.com/wtouch/AIMSWebService.exe/wsdl/IAIMSWebService
AIMS_WS_USERNAME=api_user
AIMS_WS_PASSWORD=api_password

# App
FLASK_ENV=development
FLASK_DEBUG=1
```

### Step 1.4: Database Setup
```bash
# Run database migrations
python scripts/init_db.py
```

**Supabase Tables:**
- `crew_members` - Thông tin phi hành đoàn
- `crew_qualifications` - Chứng chỉ/bằng cấp
- `crew_roster` - Lịch bay
- `standby_records` - Crew standby (SBY/SL/CSL)
- `flights` - Thông tin chuyến bay
- `crew_flight_hours` - Flight time tracking

### Step 1.5: Verify Setup
```bash
python -c "from supabase import create_client; print('Supabase OK')"
python -c "from zeep import Client; print('SOAP OK')"
```

### ✅ Phase 1 Completion Criteria
- [ ] Repository cloned
- [ ] Dependencies installed
- [ ] .env configured
- [ ] Database tables created
- [ ] Connection tests pass

---

## Phase 2: Data Integration
**Objective:** Kết nối AIMS SOAP API và thiết lập ETL pipeline.

### Step 2.1: AIMS SOAP Client Setup
```python
# aims_soap_client.py
from zeep import Client
from zeep.transports import Transport
from requests import Session

class AIMSSoapClient:
    def __init__(self, wsdl_url, username, password):
        session = Session()
        transport = Transport(session=session, timeout=30)
        self.client = Client(wsdl_url, transport=transport)
        self.un = username
        self.psw = password
```

### Step 2.2: Core API Methods

| Method | Purpose | Priority |
|--------|---------|----------|
| `GetCrewList` | Lấy danh sách crew | ⭐ High |
| `CrewMemberRosterDetailsForPeriod` | Chi tiết roster | ⭐ High |
| `FetchDayFlights` | Flights trong ngày | ⭐ High |
| `FetchCrewQuals` | Qualifications | Medium |
| `CrewCheckIn/Out` | Check-in status | Medium |

### Step 2.3: Test AIMS Connection
```bash
python scripts/test_aims_connection.py
```

**Expected output:**
```
Connecting to AIMS...
✓ WSDL loaded successfully
✓ Authentication OK
✓ GetCrewList returned 127 records
```

### Step 2.4: CSV Fallback Setup
```python
# data_processor.py
def load_from_csv(file_type, file_path):
    """Fallback khi AIMS không khả dụng"""
    if file_type == 'crew_hours':
        return parse_rol_cr_tot_report(file_path)
    elif file_type == 'flights':
        return parse_day_rep_report(file_path)
```

### Step 2.5: Data Sync Scheduler
```python
# APScheduler configuration
scheduler.add_job(sync_crew_data, 'interval', minutes=5)
scheduler.add_job(sync_flight_data, 'interval', minutes=5)
scheduler.add_job(calculate_ftl_hours, 'interval', minutes=15)
```

### ✅ Phase 2 Completion Criteria
- [ ] AIMS SOAP client created
- [ ] GetCrewList returns data
- [ ] FetchDayFlights returns data
- [ ] CSV fallback working
- [ ] Scheduler configured

---

## Phase 3: Core Features
**Objective:** Xây dựng Dashboard UI và các tính năng chính.

### Step 3.1: Flask API Endpoints
```python
# api_server.py
@app.route('/api/dashboard/summary')
def get_dashboard_summary():
    """KPI cards data"""
    
@app.route('/api/crew')
def get_crew_list():
    """Crew list with filters"""
    
@app.route('/api/flights')
def get_flights():
    """Flight list by date"""
    
@app.route('/api/standby')
def get_standby():
    """SBY/SL/CSL crew"""
```

### Step 3.2: Dashboard Components

| Component | Description | Data Source |
|-----------|-------------|-------------|
| KPI Cards | Total crew, flights, utilization | `/api/dashboard/summary` |
| Crew Table | Crew list with status | `/api/crew` |
| Flight Table | Today's flights | `/api/flights` |
| Standby Panel | SBY/SL/CSL counts | `/api/standby` |
| Date Filter | Filter all data by date | Query param |

### Step 3.3: Run Development Server
```bash
python api_server.py
```

Access: `http://localhost:5000`

### Step 3.4: FTL Monitoring Logic
```python
def calculate_ftl_hours(crew_id):
    """
    Calculate flight time limits:
    - 28-day rolling: max 100 hours
    - 12-month rolling: max 1000 hours
    """
    hours_28d = sum_flight_hours(crew_id, days=28)
    hours_12m = sum_flight_hours(crew_id, months=12)
    
    if hours_28d > 95:  # 95% of limit
        return 'CRITICAL'
    elif hours_28d > 85:
        return 'WARNING'
    return 'NORMAL'
```

### ✅ Phase 3 Completion Criteria
- [ ] API endpoints working
- [ ] Dashboard renders data
- [ ] Date filter functional
- [ ] FTL calculations correct
- [ ] Data source toggle (AIMS/CSV)

---

## Phase 4: Advanced Features
**Objective:** Alert system, reporting, và optimizations.

### Step 4.1: Alert System
```python
ALERT_RULES = {
    'FTL_WARNING': {
        'condition': 'hours_28d > 85',
        'severity': 'warning'
    },
    'FTL_CRITICAL': {
        'condition': 'hours_28d > 95',
        'severity': 'critical'
    },
    'QUAL_EXPIRY': {
        'condition': 'days_to_expiry < 30',
        'severity': 'warning'
    }
}
```

### Step 4.2: Crew Detail View
```
GET /api/crew/{id}
GET /api/crew/{id}/roster?from=2026-01-01&to=2026-01-31
GET /api/crew/{id}/flight-hours
```

### Step 4.3: Performance Optimization
```python
# Caching với LRU
@lru_cache(maxsize=100)
def get_cached_summary(date_str, cache_key):
    return calculate_summary(date_str)

# Pagination
@app.route('/api/crew')
def get_crew():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
```

### Step 4.4: Export Features
```python
@app.route('/api/export/crew')
def export_crew_csv():
    """Export crew list as CSV"""

@app.route('/api/export/ftl-report')
def export_ftl_report():
    """Export FTL status report"""
```

### ✅ Phase 4 Completion Criteria
- [ ] Alert system active
- [ ] Crew detail view working
- [ ] Caching implemented
- [ ] Export functions working
- [ ] Performance benchmarks met (<3s load)

---

## Phase 5: Testing & Deployment
**Objective:** Testing, security hardening, và production deployment.

### Step 5.1: Run Tests
```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/integration/

# AIMS API tests (requires connection)
pytest tests/test_aims_client.py -v
```

### Step 5.2: Security Checklist
- [ ] Credentials encrypted in environment
- [ ] HTTPS enabled
- [ ] CORS configured
- [ ] Rate limiting applied
- [ ] Input validation on all endpoints

### Step 5.3: Production Configuration
```env
# Production .env
FLASK_ENV=production
FLASK_DEBUG=0
SUPABASE_URL=https://prod.supabase.co
SUPABASE_KEY=prod-service-key
AIMS_WSDL_URL=https://aims-prod.company.com/...
```

### Step 5.4: Deploy to Render
```bash
# Ensure render.yaml exists
# Push to GitHub - auto-deploy triggers
git push origin main
```

**render.yaml:**
```yaml
services:
  - type: web
    name: aviation-dashboard
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn api_server:app
    envVars:
      - key: FLASK_ENV
        value: production
```

### Step 5.5: Post-Deployment Verification
```bash
# Health check
curl https://your-app.onrender.com/health

# API test
curl https://your-app.onrender.com/api/dashboard/summary
```

### ✅ Phase 5 Completion Criteria
- [ ] All tests passing
- [ ] Security checklist complete
- [ ] Production deployed
- [ ] Health checks passing
- [ ] Monitoring configured

---

## 📁 Project Structure

```
aviation_operations_dashboard/
├── api_server.py           # Flask main application
├── aims_soap_client.py     # AIMS SOAP integration
├── data_processor.py       # Data transformation logic
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── templates/
│   └── crew_dashboard.html # Dashboard UI
├── static/
│   ├── css/
│   └── js/
├── scripts/
│   ├── init_db.py          # Database setup
│   ├── test_aims_connection.py
│   └── sync_data.py
├── tests/
│   ├── test_api.py
│   ├── test_aims_client.py
│   └── test_data_processor.py
├── docs/
│   ├── PRD.md
│   ├── BRD.md
│   ├── Technical_Specification.md
│   ├── Data_Workflow.md
│   └── API_SOAP_WebService.md
└── README.md
```

---

## 🚀 Quick Start (AI Execution Mode)

Để AI thực thi từng phase:

```
/execute-phase 1  # Foundation Setup
/execute-phase 2  # Data Integration
/execute-phase 3  # Core Features
/execute-phase 4  # Advanced Features
/execute-phase 5  # Testing & Deployment
```

Hoặc:
```
@phase1  # Chỉ chạy Phase 1
@phase2  # Chỉ chạy Phase 2
...
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [PRD.md](docs/PRD.md) | Product Requirements |
| [BRD.md](docs/BRD.md) | Business Requirements |
| [Technical_Specification.md](docs/Technical_Specification.md) | Technical Design |
| [Data_Workflow.md](docs/Data_Workflow.md) | ETL Pipeline |
| [API_SOAP_WebService.md](docs/API_SOAP_WebService.md) | AIMS API Reference |

---

## 📞 Support

- **AIMS API Issues:** Check `docs/API_SOAP_WebService.md` troubleshooting section
- **Database Issues:** Verify Supabase connection and table schema
- **Deployment Issues:** Review Render logs

---

## License

MIT License - See LICENSE file.
