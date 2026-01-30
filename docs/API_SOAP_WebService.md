# AIMS SOAP Web Service API Documentation
## Aviation Operations Dashboard Integration Guide

**Version:** 1.0  
**Ngày:** 30/01/2026  
**Source:** AIMS IT Guide Section 4

---

## 1. Tổng Quan

### 1.1 Giới Thiệu
AIMS Web Services là bộ API cho phép truy xuất và cập nhật dữ liệu AIMS từ các ứng dụng bên ngoài thông qua giao thức **SOAP 1.1** và **WSDL**.

### 1.2 Thông Tin Kết Nối

| Parameter | Value |
|-----------|-------|
| Protocol | SOAP 1.1 |
| Format | XML/WSDL |
| Endpoint | `http://{FQDN}/wtouch/AIMSWebService.exe/wsdl/IAIMSWebService` |
| Authentication | Username + Password (via AIMS Option 7.1) |

### 1.3 Yêu Cầu Kỹ Thuật
- Programming tools hỗ trợ SOAP/WSDL: .NET, Java, Delphi, Python (zeep)
- SSL/TLS cho production environment
- Timeout handling (recommended: 30 seconds)

---

## 2. Authentication

### 2.1 Thiết Lập Credentials
Credentials được cấu hình qua **AIMS Option 7.1** (Web Services button) và lưu trong database AIMS.

### 2.2 Sử Dụng Trong API Call
```xml
<!-- Mỗi request đều yêu cầu UN và PSW -->
<UN>your_username</UN>
<PSW>your_password</PSW>
```

> [!CAUTION]
> Không có credentials được thiết lập → Web Services sẽ không hoạt động.

---

## 3. Crew Related Methods

### 3.1 FetchLegMembers (Method #1)
**Mô tả:** Lấy danh sách crew đang vận hành một chuyến bay cụ thể.

**Request:**
```xml
<FetchLegMembers>
    <UN>username</UN>
    <PSW>password</PSW>
    <DD>30</DD>      <!-- Day -->
    <MM>01</MM>      <!-- Month -->
    <YY>2026</YY>    <!-- Year -->
    <Flight>VN123</Flight>
    <Dep>SGN</Dep>   <!-- Departure station -->
</FetchLegMembers>
```

**Response Type:** `TAIMSGetLegMembers`

| Field | Type | Description |
|-------|------|-------------|
| FlightDD | WideString | Flight day |
| FlightMM | WideString | Flight month |
| FlightYY | WideString | Flight year |
| FlightCarrier | WideString | Carrier code |
| FlightNo | Integer | Flight number |
| FlightLegCD | WideString | Leg code suffix |
| FlightDesc | WideString | Flight description |
| FlightDep | WideString | Departure station |
| Fcount | Integer | Number of crew members |
| Flist | Array of TAIMSLegMembersItm | Crew member list |

---

### 3.2 FetchDayMembers (Method #2)
**Mô tả:** Lấy danh sách crew hoạt động trong một ngày cụ thể.

**Request:**
```xml
<FetchDayMembers>
    <UN>username</UN>
    <PSW>password</PSW>
    <DD>30</DD>
    <MM>01</MM>
    <YY>2026</YY>
</FetchDayMembers>
```

---

### 3.3 GetCrewList (Method #12) ⭐
**Mô tả:** Lấy thông tin cơ bản của crew (ID, Name, Address, Qualifications) cho một nhóm crew trong khoảng thời gian.

**Request:**
```xml
<GetCrewList>
    <UN>username</UN>
    <PSW>password</PSW>
    <ID>0</ID>              <!-- 0 = all crew -->
    <PrimaryQualify>true</PrimaryQualify>
    <FmDD>01</FmDD>
    <FmMM>01</FmMM>
    <FmYY>2026</FmYY>
    <ToDD>31</ToDD>
    <ToMM>01</ToMM>
    <ToYY>2026</ToYY>
    <BaseStr>SGN</BaseStr>    <!-- Optional: filter by base -->
    <ACStr>A320</ACStr>       <!-- Optional: filter by AC type -->
    <PosStr>PIC</PosStr>      <!-- Optional: filter by position -->
</GetCrewList>
```

**Response Type:** `TAIMSGetCrewList`

| Field | Type | Description |
|-------|------|-------------|
| GetCrewListCount | Integer | Number of crew found |
| GetCrewList | Array of TAIMSGetCrewItm | Crew details |
| ErrorExplanation | WideString | Error message if any |

---

### 3.4 CrewMemberRosterDetailsForPeriod (Method #13) ⭐
**Mô tả:** Lấy chi tiết lịch trình (roster) của một crew member trong khoảng thời gian.

**Request:**
```xml
<CrewMemberRosterDetailsForPeriod>
    <UN>username</UN>
    <PSW>password</PSW>
    <ID>12345</ID>          <!-- Crew ID -->
    <FmDD>01</FmDD>
    <FmMM>01</FmMM>
    <FmYY>2026</FmYY>
    <ToDD>31</ToDD>
    <ToMM>01</ToMM>
    <ToYY>2026</ToYY>
</CrewMemberRosterDetailsForPeriod>
```

**Response Type:** `TAIMSCrewRostDetailList`

| Field | Type | Description |
|-------|------|-------------|
| CrewRostCount | Integer | Number of roster items |
| CrewRostList | Array of TAIMSCrewRostItm | Roster details |
| ErrorExplanation | WideString | Error message |

---

### 3.5 FetchCrewQuals (Method #14)
**Mô tả:** Lấy thông tin qualifications của crew trong khoảng thời gian.

**Parameters:**
- `CrewID`: 0 = all crew với qualifications trong period
- `PrimaryQualify`: True = Primary qualifications only
- `GetAllQualsInPeriod`: True = Lấy tất cả qualifications trong period

**Response Type:** `TAIMSCrewQualsList`

---

### 3.6 CrewCheckIn / CrewCheckOut (Methods #15, #16)
**Mô tả:** Ghi nhận check-in/check-out của crew.

**Request:**
```xml
<CrewCheckIn>
    <UN>username</UN>
    <PSW>password</PSW>
    <ID>12345</ID>
    <Confirmed>false</Confirmed>  <!-- false = preview, true = confirm -->
</CrewCheckIn>
```

**Response:** Chi tiết duty tiếp theo và trạng thái check-in.

---

### 3.7 FetchCrewMessages (Method #18)
**Mô tả:** Lấy danh sách messages của crew.

---

## 4. Flight Related Methods

### 4.1 FetchDayFlights (Method #19) ⭐
**Mô tả:** Lấy chi tiết tất cả flights trong một ngày.

**Request:**
```xml
<FetchDayFlights>
    <UN>username</UN>
    <PSW>password</PSW>
    <DD>30</DD>
    <MM>01</MM>
    <YY>2026</YY>
</FetchDayFlights>
```

**Response Type:** `TAIMSFlightList`

---

### 4.2 FetchFlightsFrTo (Method #20) ⭐
**Mô tả:** Lấy flights trong khoảng date/time range.

**Request:**
```xml
<FetchFlightsFrTo>
    <UN>username</UN>
    <PSW>password</PSW>
    <FmDD>30</FmDD>
    <FmMM>01</FmMM>
    <FmYY>2026</FmYY>
    <FmHH>00</FmHH>
    <FmMins>00</FmMins>
    <ToDD>31</ToDD>
    <ToMM>01</ToMM>
    <ToYY>2026</ToYY>
    <ToHH>23</ToHH>
    <ToMins>59</ToMins>
</FetchFlightsFrTo>
```

---

### 4.3 FetchFlightDetails (Method #21)
**Mô tả:** Lấy chi tiết specific flights trong date/time range.

---

### 4.4 UploadJourneyLog (Method #24)
**Mô tả:** Upload dữ liệu Journey Log cho một flight leg.

**Request Type:** `TAIMSJourneyLogRec`

| Field | Type | Description |
|-------|------|-------------|
| JLogDD | WideString | Journey log day |
| JLogMM | WideString | Journey log month |
| JLogYY | WideString | Journey log year |
| JLogFltNo | Integer | Flight number |
| JLogDep | WideString | Departure |
| JLogArr | WideString | Arrival |
| JLogDelayTimes | TAIMSDelayTimesRec | Delay information |

---

### 4.5 FetchACRoutes (Method #25)
**Mô tả:** Lấy Aircraft Routes với flight legs trong period.

---

## 5. Miscellaneous Methods

### 5.1 FetchAircrafts (Method #27)
**Mô tả:** Lấy danh sách aircraft.

**Response Type:** `TAIMSAircraft`

| Field | Type | Description |
|-------|------|-------------|
| cAcType | WideString | Aircraft type |
| cACReg | WideString | Registration number |
| cACCountry | WideString | Country registered |
| cACUsePound | Byte | 1=Kgs, 2=Pounds |

---

### 5.2 FetchACTypes (Method #28)
**Mô tả:** Lấy danh sách aircraft types.

**Response Type:** `TAIMSACType`

| Field | Type | Description |
|-------|------|-------------|
| cAcTypeCode | WideString | AC Type code |
| cDescription | WideString | AC Type description |

---

### 5.3 FetchCountries (Method #29)
**Response Type:** `TAIMSCountry`

---

### 5.4 FetchAirports (Method #30)
**Response Type:** `TAIMSAirport`

| Field | Type | Description |
|-------|------|-------------|
| cAirportCode | WideString | IATA code |
| cAirportName | WideString | Airport name |
| cLatitude | Double | Latitude |
| cLongtitude | Double | Longitude |
| cCountryCode | WideString | Country code |
| cAltitude | Integer | Airport altitude |
| cRunwayLength | Integer | Runway length |

---

### 5.5 FetchCharterers (Method #31)
**Mô tả:** Lấy danh sách charterers.

---

### 5.6 GetTimeDifference (Method #32)
**Mô tả:** Lấy chênh lệch giờ UTC/Local cho một station.

---

## 6. Data Types Reference

### 6.1 TAIMSCrewQualsRec (Crew Qualifications)

| Field | Type | Description |
|-------|------|-------------|
| CrewID | WideString | Crew member ID |
| CrewName | WideString | Full name |
| FirstName | WideString | First name (passport) |
| LastName | WideString | Last name (passport) |
| Crew3LC | WideString | 3-letter code |
| Gender | WideString | M/F |
| Address1-3 | WideString | Physical address |
| City | WideString | City |
| State | WideString | State |
| ZipCode | WideString | Zip code |
| Residence | WideString | Country of residence |
| Telephone | WideString | Phone |
| CellPhone | WideString | Mobile |
| Email | WideString | Email address |
| EmployBeg | WideString | Employment begin date |
| EmployEnd | WideString | Employment end date |
| CrewQuals | Array of TAIMSCrewQualsItm | Qualifications |

---

### 6.2 TAIMSCrewQualsItm (Qualification Item)

| Field | Type | Description |
|-------|------|-------------|
| QualBase | WideString | Qualification base |
| QualAc | WideString | Aircraft type |
| QualPos | WideString | Position (PIC, FO, etc.) |
| RosterGroup | Smallint | Roster group |
| QualBDay | WideString | Begin date |
| QualEDay | WideString | End date |
| PrimaryQual | Boolean | Is primary qualification |
| NotToBeRoster | Boolean | Not to be rostered |

---

### 6.3 TAIMSCrewRostItm (Roster Item)

| Field | Type | Description |
|-------|------|-------------|
| RostDD | WideString | Roster day |
| RostMM | WideString | Roster month |
| RostYY | WideString | Roster year |
| CarrCode | WideString | Carrier code |
| FltNo | Integer | Flight number |
| Dep | WideString | Departure |
| Arr | WideString | Arrival |
| STD_HH | WideString | STD hours |
| STD_MM | WideString | STD minutes |
| STA_HH | WideString | STA hours |
| STA_MM | WideString | STA minutes |
| ACType | WideString | Aircraft type |
| ACReg | WideString | Aircraft registration |
| DutyCode | WideString | Duty code |

---

### 6.4 TAIMSDelayTimesRec (Delay Information)

| Field | Type | Description |
|-------|------|-------------|
| FDepDelayTime1_HH | WideString | 1st departure delay hours |
| FDepDelayTime1_MM | WideString | 1st departure delay minutes |
| FDepDelayCode1 | WideString | 1st delay code |
| FDepDelayTime2_HH | WideString | 2nd departure delay hours |
| FDepDelayTime2_MM | WideString | 2nd departure delay minutes |
| FDepDelayCode2 | WideString | 2nd delay code |
| FArrDelayTime1_HH | WideString | 1st arrival delay hours |
| FArrDelayTime1_MM | WideString | 1st arrival delay minutes |
| FArrDelayCode1 | WideString | 1st arrival delay code |

---

### 6.5 TAIMSLandsTkofRec (Takeoff/Landing Record)

| Field | Type | Description |
|-------|------|-------------|
| TKFLND_ID | Integer | Crew member ID |
| TKOF_DAY | Boolean | Day takeoff |
| TKOF_NIGHT | Boolean | Night takeoff |
| TKOF_MAN | Boolean | Manual takeoff |
| TKOF_AUTO | Boolean | Automatic takeoff |
| LAND_DAY | Boolean | Day landing |
| LAND_NIGHT | Boolean | Night landing |
| LAND_MAN | Boolean | Manual landing |
| LAND_AUTO | Boolean | Automatic landing |
| CAT3_ACT | Boolean | Actual CAT III |
| CAT3_PRAC | Boolean | Practice CAT III |
| RHS | Boolean | Right-hand seat |

---

## 7. Python Integration Example

### 7.1 Basic Setup with Zeep

```python
from zeep import Client
from zeep.transports import Transport
from requests import Session
from datetime import date

class AIMSClient:
    def __init__(self, wsdl_url: str, username: str, password: str):
        session = Session()
        session.verify = True
        transport = Transport(session=session, timeout=30)
        
        self.client = Client(wsdl_url, transport=transport)
        self.un = username
        self.psw = password
    
    def get_crew_for_date(self, target_date: date, base: str = "") -> list:
        """Get all crew for a specific date"""
        response = self.client.service.GetCrewList(
            UN=self.un,
            PSW=self.psw,
            ID=0,
            PrimaryQualify=True,
            FmDD=target_date.strftime("%d"),
            FmMM=target_date.strftime("%m"),
            FmYY=target_date.strftime("%Y"),
            ToDD=target_date.strftime("%d"),
            ToMM=target_date.strftime("%m"),
            ToYY=target_date.strftime("%Y"),
            BaseStr=base,
            ACStr="",
            PosStr=""
        )
        
        if response.ErrorExplanation:
            raise Exception(response.ErrorExplanation)
        
        return response.GetCrewList
    
    def get_flights_for_date(self, target_date: date) -> list:
        """Get all flights for a specific date"""
        response = self.client.service.FetchDayFlights(
            UN=self.un,
            PSW=self.psw,
            DD=target_date.strftime("%d"),
            MM=target_date.strftime("%m"),
            YY=target_date.strftime("%Y")
        )
        return response
    
    def get_crew_roster(self, crew_id: int, from_date: date, to_date: date) -> list:
        """Get roster for specific crew member"""
        response = self.client.service.CrewMemberRosterDetailsForPeriod(
            UN=self.un,
            PSW=self.psw,
            ID=crew_id,
            FmDD=from_date.strftime("%d"),
            FmMM=from_date.strftime("%m"),
            FmYY=from_date.strftime("%Y"),
            ToDD=to_date.strftime("%d"),
            ToMM=to_date.strftime("%m"),
            ToYY=to_date.strftime("%Y")
        )
        
        if response.ErrorExplanation:
            raise Exception(response.ErrorExplanation)
        
        return response.CrewRostList

# Usage example
if __name__ == "__main__":
    client = AIMSClient(
        wsdl_url="http://aims.company.com/wtouch/AIMSWebService.exe/wsdl/IAIMSWebService",
        username="api_user",
        password="api_password"
    )
    
    today = date.today()
    crew_list = client.get_crew_for_date(today, base="SGN")
    
    for crew in crew_list:
        print(f"{crew.CrewID}: {crew.CrewName}")
```

---

## 8. Error Handling

### 8.1 Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Authentication failed` | Invalid UN/PSW | Check credentials in AIMS 7.1 |
| `Object reference not set` | Invalid parameter | Check required fields |
| `Connection timeout` | Network issue | Increase timeout, retry |
| `No data found` | Empty result | Check date range, filters |

### 8.2 Error Response Format

```xml
<TAIMSGetCrewList>
    <GetCrewListCount>0</GetCrewListCount>
    <GetCrewList/>
    <ErrorExplanation>Authentication failed: Invalid credentials</ErrorExplanation>
</TAIMSGetCrewList>
```

---

## 9. Best Practices

### 9.1 Performance Optimization
- Sử dụng date range hợp lý (max 60 ngày)
- Cache static data (airports, aircraft types) - sync daily
- Implement connection pooling
- Use async calls khi có thể

### 9.2 Security
- Store credentials encrypted
- Use HTTPS in production
- Implement IP whitelisting
- Rotate credentials định kỳ
- Log all API access

### 9.3 Error Handling
- Implement retry logic với exponential backoff
- Set appropriate timeouts
- Have fallback mechanism (CSV)
- Alert on repeated failures

---

## Appendix: Method Quick Reference

| # | Method | Category | Description |
|---|--------|----------|-------------|
| 1 | FetchLegMembers | Crew | Crew on flight leg |
| 2 | FetchDayMembers | Crew | Crew for day |
| 3 | FetchTimeDayMembers | Crew | Crew for day+time |
| 4 | FetchPairingMembers | Crew | Crew on pairing |
| 5 | FetchScheduleChanges | Crew | Schedule changes |
| 6 | FetchUnfinalizedPairings | Crew | Disrupted pairings |
| 7 | FetchMissingTraining | Crew | Missing training |
| 8 | InsertCrewMember | Crew | Add crew v1 |
| 9 | InsertCrewMember2 | Crew | Add crew v2 |
| 10 | CrewPendingNotifForPeriod | Crew | Pending notifications |
| 11 | RemoveCrewNotificationIndicator | Crew | Remove notification |
| 12 | **GetCrewList** | Crew | Crew info + quals ⭐ |
| 13 | **CrewMemberRosterDetailsForPeriod** | Crew | Crew roster ⭐ |
| 14 | FetchCrewQuals | Crew | Qualifications |
| 15 | CrewCheckIn | Crew | Check-in |
| 16 | CrewCheckOut | Crew | Check-out |
| 17 | FetchMaxFDP | Crew | Max FDP values |
| 18 | FetchCrewMessages | Crew | Crew messages |
| 19 | **FetchDayFlights** | Flight | Day flights ⭐ |
| 20 | **FetchFlightsFrTo** | Flight | Flight range ⭐ |
| 21 | FetchFlightDetails | Flight | Specific flights |
| 22 | FetchFlightChanges | Flight | Flight changes |
| 23 | FetchFlightModLog | Flight | Modification log |
| 24 | UploadJourneyLog | Flight | Upload JL |
| 25 | FetchACRoutes | Flight | AC routes |
| 26 | UploadLegInfo | Flight | Upload leg info |
| 27 | FetchAircrafts | Misc | Aircraft list |
| 28 | FetchACTypes | Misc | AC types |
| 29 | FetchCountries | Misc | Countries |
| 30 | FetchAirports | Misc | Airports |
| 31 | FetchCharterers | Misc | Charterers |
| 32 | GetTimeDifference | Misc | UTC/Local diff |

⭐ = Commonly used methods
