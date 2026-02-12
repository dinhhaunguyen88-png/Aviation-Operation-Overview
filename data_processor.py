"""
Data Processor Module
Phase 2: Data Integration

Handles data transformation, validation, and ETL operations
for both AIMS API and CSV fallback sources.
"""

import os
import csv
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from dotenv import load_dotenv
# Load environment
dotenv_path = os.getenv("DOTENV_CONFIG_PATH", ".env")
load_dotenv(dotenv_path)

logger = logging.getLogger(__name__)

# =========================================================
# Configuration
# =========================================================

def get_today_vn() -> date:
    """Get today's date in Vietnam timezone (UTC+7)."""
    # Use UTC + 7h for Vietnam
    from datetime import timezone
    return (datetime.now(timezone.utc) + timedelta(hours=7)).date()

def normalize_ac_type(ac_type: Any) -> str:
    """Normalize aircraft type (e.g., A321XLR -> 32W)."""
    if not ac_type: return "Unknown"
    ac_type = str(ac_type).upper().strip()
    if "XLR" in ac_type or ac_type == "32W":
        return "32W"
    if ac_type.isdigit() and len(ac_type) == 3:
        return f"A{ac_type}"
    return ac_type

def normalize_flight_id(flight_id: Any) -> str:
    """
    Normalize flight ID to its base numeric part.
    Example: VJ1250A -> 1250, 1250/SGN -> 1250, VN123 -> 123
    """
    if not flight_id:
        return ""
    import re
    s = str(flight_id).strip()
    # Extract only the numeric part
    match = re.search(r'(\d+)', s)
    if match:
        return match.group(1)
    return s


FTL_28DAY_LIMIT = int(os.getenv("FTL_28DAY_LIMIT", 100))
FTL_12MONTH_LIMIT = int(os.getenv("FTL_12MONTH_LIMIT", 1000))
FTL_WARNING_THRESHOLD = int(os.getenv("FTL_WARNING_THRESHOLD", 85))
FTL_CRITICAL_THRESHOLD = int(os.getenv("FTL_CRITICAL_THRESHOLD", 95))

# Crew status mapping from AIMS duty codes
DUTY_CODE_MAPPING = {
    # Standby
    "SBY": "SBY", "STBY": "SBY", "STB": "SBY",
    # Sick Leave
    "SL": "SL", "SICK": "SL", "ILL": "SL",
    # Call Sick
    "CSL": "CSL", "CSICK": "CSL",
    # Day Off
    "OFF": "OFF", "DO": "OFF", "REST": "OFF",
    # Training
    "TRN": "TRN", "SIM": "TRN", "TRAINING": "TRN",
    # Leave
    "LVE": "LVE", "AL": "LVE", "ANNUAL": "LVE",
    # Flight duty (detected by flight number presence)
    "FLY": "FLY",
}


# =========================================================
# CSV Parsing Functions
# =========================================================

def parse_hours_string(time_str: str) -> float:
    """
    Convert HH:MM time string to decimal hours.
    
    Args:
        time_str: Time in HH:MM format (e.g., "85:30")
        
    Returns:
        Decimal hours (e.g., 85.5)
    """
    if not time_str or time_str.strip() in ["-", "", "N/A"]:
        return 0.0
    
    try:
        time_str = time_str.strip()
        if ":" in time_str:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return hours + minutes / 60.0
        else:
            return float(time_str)
    except (ValueError, IndexError):
        logger.warning(f"Could not parse time string: {time_str}")
        return 0.0


def parse_rol_cr_tot_report(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse RolCrTotReport CSV for crew flight hours.
    
    Expected columns: Staff ID, Name, Total 28 Days, Total 12 Months
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of crew flight hour records
    """
    records = []
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # Try to detect header row
            first_lines = [f.readline() for _ in range(5)]
            f.seek(0)
            
            # Find header row (contains "Staff ID" or similar)
            skip_rows = 0
            for i, line in enumerate(first_lines):
                if "Staff" in line or "ID" in line:
                    skip_rows = i
                    break
            
            # Skip to header
            for _ in range(skip_rows):
                next(f)
            
            reader = csv.DictReader(f)
            
            for row in reader:
                # Get crew ID - try different column names
                crew_id = (
                    row.get("Staff ID", "") or 
                    row.get("StaffID", "") or 
                    row.get("Crew ID", "") or
                    row.get("ID", "")
                ).strip()
                
                # Skip non-operating crew (marked with *)
                if crew_id.startswith("*"):
                    continue
                
                if not crew_id:
                    continue
                
                # Get crew name
                crew_name = (
                    row.get("Name", "") or 
                    row.get("Crew Name", "") or
                    row.get("Full Name", "")
                ).strip()
                
                # Get flight hours
                hours_28d_str = (
                    row.get("Total 28 Days", "") or
                    row.get("28 Days", "") or
                    row.get("28-Day", "")
                )
                
                hours_12m_str = (
                    row.get("Total 12 Months", "") or
                    row.get("12 Months", "") or
                    row.get("12-Month", "")
                )
                
                hours_28d = parse_hours_string(hours_28d_str)
                hours_12m = parse_hours_string(hours_12m_str)
                
                # Determine warning level
                warning_level = calculate_warning_level(hours_28d, hours_12m)
                
                records.append({
                    "crew_id": crew_id,
                    "crew_name": crew_name,
                    "hours_28_day": round(hours_28d, 2),
                    "hours_12_month": round(hours_12m, 2),
                    "warning_level": warning_level,
                    "source": "CSV",
                    "calculation_date": date.today().isoformat()
                })
        
        logger.info(f"Parsed {len(records)} records from RolCrTotReport")
        return records
        
    except Exception as e:
        logger.error(f"Failed to parse RolCrTotReport: {e}")
        raise


def parse_day_rep_report(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse DayRepReport CSV for flight data.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of flight records
    """
    records = []
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                flight_number = row.get("Flight No", "") or row.get("Flt", "")
                
                if not flight_number:
                    continue
                
                records.append({
                    "flight_number": flight_number.strip(),
                    "departure": row.get("Dep", "").strip(),
                    "arrival": row.get("Arr", "").strip(),
                    "std": row.get("STD", "").strip(),
                    "sta": row.get("STA", "").strip(),
                    "aircraft_type": row.get("AC Type", "").strip(),
                    "aircraft_reg": row.get("AC Reg", "").strip(),
                    "source": "CSV"
                })
        
        logger.info(f"Parsed {len(records)} flights from DayRepReport")
        return records
        
    except Exception as e:
        logger.error(f"Failed to parse DayRepReport: {e}")
        raise


def parse_standby_report(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse standby report CSV.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of standby records
    """
    records = []
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                crew_name = row.get("Crew Name", "") or row.get("Name", "")
                status = row.get("Status", "") or row.get("Duty", "")
                
                # Normalize status
                status = DUTY_CODE_MAPPING.get(status.upper(), status.upper())
                
                if not crew_name:
                    continue
                
                records.append({
                    "crew_id": row.get("Crew ID", ""),
                    "crew_name": crew_name.strip(),
                    "status": status,
                    "duty_start_date": row.get("Start Date", ""),
                    "duty_end_date": row.get("End Date", ""),
                    "base": row.get("Base", ""),
                    "source": "CSV"
                })
        
        logger.info(f"Parsed {len(records)} standby records")
        return records
        
    except Exception as e:
        logger.error(f"Failed to parse standby report: {e}")
        raise


# =========================================================
# FTL Calculation Functions
# =========================================================

def calculate_warning_level(hours_28d: float, hours_12m: float) -> str:
    """
    Calculate FTL warning level based on flight hours.
    
    Args:
        hours_28d: 28-day rolling flight hours
        hours_12m: 12-month rolling flight hours
        
    Returns:
        Warning level: NORMAL, WARNING, or CRITICAL
    """
    # Calculate percentages
    pct_28d = (hours_28d / FTL_28DAY_LIMIT) * 100 if FTL_28DAY_LIMIT > 0 else 0
    pct_12m = (hours_12m / FTL_12MONTH_LIMIT) * 100 if FTL_12MONTH_LIMIT > 0 else 0
    
    max_pct = max(pct_28d, pct_12m)
    
    if max_pct >= FTL_CRITICAL_THRESHOLD:
        return "CRITICAL"
    elif max_pct >= FTL_WARNING_THRESHOLD:
        return "WARNING"
    else:
        return "NORMAL"


def fetch_all_rows(query, page_size: int = 1000) -> list:
    """
    Fetch ALL rows from a Supabase query by paginating with .range().
    Supabase limits responses to 1000 rows by default.
    This function loops until all rows are retrieved.
    
    Args:
        query: A Supabase query builder (before .execute())
        page_size: Number of rows per batch (max 1000)
    
    Returns:
        List of all rows from the query
    """
    all_rows = []
    offset = 0
    
    while True:
        batch = query.range(offset, offset + page_size - 1).execute()
        batch_data = batch.data or []
        all_rows.extend(batch_data)
        
        if len(batch_data) < page_size:
            break  # Last page
        
        offset += page_size
    
    return all_rows


def get_top_high_intensity_crew(
    crew_hours: List[Dict[str, Any]], 
    limit: int = 20,
    sort_by: str = "hours_28_day"
) -> List[Dict[str, Any]]:
    """
    Get top N crew members with highest flight hours.
    
    Args:
        crew_hours: List of crew flight hour records
        limit: Number of records to return
        sort_by: Field to sort by (hours_28_day or hours_12_month)
        
    Returns:
        Top N crew sorted by specified field
    """
    sorted_crew = sorted(
        crew_hours,
        key=lambda x: x.get(sort_by, 0),
        reverse=True
    )
    return sorted_crew[:limit]


# =========================================================
# Dashboard Metrics Calculation
# =========================================================

def calculate_dashboard_summary(
    crew_data: List[Dict[str, Any]],
    flight_data: List[Dict[str, Any]],
    standby_data: List[Dict[str, Any]],
    target_date: date = None,
    assignments: List[Dict[str, Any]] = None, # New parameter for roster details
    crew_positions: Dict[str, str] = None # crew_id -> position (CPT/FO/PU/FA)
) -> Dict[str, Any]:
    """
    Calculate all dashboard KPI metrics.
    
    Args:
        crew_data: List of crew records
        flight_data: List of flight records
        standby_data: List of standby records
        target_date: Date to calculate metrics for
        
    Returns:
        Dictionary of dashboard metrics
    """
    target_date = target_date or get_today_vn()
    
    # Operations Window: 04:00 today to 03:59 tomorrow (local time)
    # This matches the aviation operational day definition
    # NOTE: Database stores STD in UTC, convert to LOCAL TIME of departure airport
    from airport_timezones import get_airport_timezone
    
    next_date = target_date + timedelta(days=1)
    prev_date = target_date - timedelta(days=1)
    target_date_str = target_date.isoformat()
    next_date_str = next_date.isoformat()
    prev_date_str = prev_date.isoformat()

    # filter flights using common logic
    # [FIX] Do NOT refilter if already filtered, just pass through
    # If flight_data is raw, we might need filtering, but get_flights already does it.
    ops_flights = flight_data 
    
    # Total flights = unique flights within ops window (04:00 today - 03:59 tomorrow)
    total_flights = len(ops_flights)
    
    # Calculate Total Aircraft Operation (unique regs in Ops Window)
    unique_ops_aircraft = set()
    for flight in ops_flights:
        reg = flight.get("aircraft_reg")
        if reg:
            unique_ops_aircraft.add(reg)
    total_aircraft_operation = len(unique_ops_aircraft)

    # [REMOVED DUPLICATE BLOCK HOURS LOOP]
    # Count crew by status
    crew_by_status = {
        "FLY": 0, "SBY": 0, "SL": 0, "CSL": 0, "OFF": 0, "TRN": 0, "LVE": 0, "OTHER": 0
    }
    
    # Sick crew by position (CPT, FO, PU, FA)
    sick_by_position = {"CPT": 0, "FO": 0, "PU": 0, "FA": 0}
    pos_map = crew_positions or {}  # crew_id -> position
    
    # helper to clean duty codes
    def get_status_from_code(code):
        if not code: return "OTHER"
        c = code.upper().strip()
        if c in ["FLY", "FLT", "POS", "DHD"]: return "FLY"
        if c in ["SBY", "SB", "R"]: return "SBY"
        if c in ["OFF", "DO", "ADO", "X"]: return "OFF"
        if c in ["SL", "SICK", "SCL"]: return "SL"
        if c in ["CSL", "CSICK", "NS", "NOSHOW"]: return "CSL"
        if c in ["AL", "LVE"]: return "LVE"
        if c in ["TRN", "SIM"]: return "TRN"
        return "OTHER"
    
    # helper to normalize position to CPT/FO/PU/FA
    def normalize_position(pos):
        if not pos: return None
        p = pos.upper().strip()
        if p in ["CP", "CPT", "CAPT", "CMD", "PIC"]: return "CPT"
        if p in ["FO", "SFO", "P2", "COP"]: return "FO"
        if p in ["PU", "ISM", "SP", "SEP", "SCC"]: return "PU"
        if p in ["FA", "CA", "CC", "FA1", "FA2", "FA3", "FA4", "FA5", "FA6"]: return "FA"
        return None
    
    def track_sick_position(crew_id):
        """Track position for sick crew member."""
        raw_pos = pos_map.get(str(crew_id), "")
        norm = normalize_position(raw_pos)
        if norm and norm in sick_by_position:
            sick_by_position[norm] += 1

    # 1. Aggegate from standby_data details first
    if standby_data:
        for crew in standby_data:
            s_raw = crew.get("status", "OTHER")
            status = get_status_from_code(s_raw)
            
            if status in crew_by_status: 
                crew_by_status[status] += 1
            else: 
                crew_by_status["OTHER"] += 1
                
            # Track position for sick crew
            if status in ["SL", "CSL"]:
                track_sick_position(crew.get("crew_id", ""))

    # 2. Iterate Crew Data
    if crew_data:
        # NOTE: Do NOT reset crew_by_status or sick_by_position here.
        # crew_data (FTL) may contain many crew members with different duty codes.
        # We want to ADD to the counts, especially for statuses not covered by standby_data.
        
        for crew in crew_data:
            d_code = crew.get("duty_code", "")
            status = get_status_from_code(d_code)
            
            # Fallback
            if status == "OTHER" and crew.get("flight_number"):
                status = "FLY"
                
            if status in crew_by_status:
                # To avoid double counting same crew member if they are in both standby_data and crew_data,
                # we should ideally track crew_ids already counted.
                # However, for now, we just allow addition but usually standby_records are distinct.
                crew_by_status[status] += 1
            else:
                crew_by_status["OTHER"] += 1
            
            # Track position for sick crew
            if status in ["SL", "CSL"]:
                track_sick_position(crew.get("crew_id", ""))

    logger.info(f"Crew Distribution Stats: {crew_by_status}")
    logger.info(f"Sick by Position: {sick_by_position}")

    # Calculate flights per hour (Operational Pulse) & AC Usage
    flights_per_hour = [0] * 24
    
    # Slots by base per hour (SGN, HAN, DAD)
    slots_by_base = {
        "SGN": [0] * 24,
        "HAN": [0] * 24,
        "DAD": [0] * 24
    }
    
    total_pax = 0
    
    # OTP Vars
    otp_threshold_mins = 15
    delayed_flights = 0
    completed_flights = 0
    on_time_flights = 0
    
    # AC Type Breakdown
    ac_type_hours = {} 
    
    # Helper to parse time string HH:MM
    def parse_hm(t_str):
        if not t_str or ":" not in t_str: return None
        try:
            parts = t_str.split(":")
            # ignore seconds if present
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None

    # Recalculate Total Block Hours from verified Ops Flights
    recalc_total_block = 0.0

    for flight in ops_flights:
        # Pulse Chart
        std = flight.get("std", "")
        sta = flight.get("sta", "")  # Also extract STA for completed logic
        etd = flight.get("etd", "")  # Estimated Time Departure
        dep_airport = flight.get("departure", "").upper().strip()  # Field name is 'departure' not 'dep_airport'
        
        if std:
            try:
                parts = std.split(":")
                if len(parts) >= 2:
                    h = int(parts[0])
                    if 0 <= h < 24:
                        flights_per_hour[h] += 1
            except ValueError:
                pass
        
        # Slots by Base (use ETD if available, else STD)
        departure_time = etd if etd else std
        if departure_time and dep_airport in slots_by_base:
            try:
                parts = departure_time.split(":")
                if len(parts) >= 2:
                    h = int(parts[0])
                    if 0 <= h < 24:
                        slots_by_base[dep_airport][h] += 1
            except ValueError:
                pass
        
        # Pax
        try:
            pax = int(flight.get("pax_total", 0) or 0)
            total_pax += pax
        except (ValueError, TypeError):
            pass
            
        # Block Hours Calculation 
        blk_val = 0.0
        
        raw_blk_hrs = flight.get("block_hours")
        raw_blk_time = flight.get("block_time")
        
        # 1. Try DB float
        if raw_blk_hrs is not None:
             try:
                 blk_val = float(raw_blk_hrs)
             except ValueError: pass
        # 2. Try DB string HH:MM
        elif raw_blk_time and ":" in str(raw_blk_time):
             mins = parse_hm(str(raw_blk_time))
             if mins is not None: blk_val = mins / 60.0
        # 3. Fallback: Calc from ON - OFF
        if blk_val == 0.0:
            off = parse_hm(flight.get("off_block"))
            on = parse_hm(flight.get("on_block"))
            
            if off is not None and on is not None:
                diff = on - off
                if diff < 0: diff += 1440 # Overnight
                blk_val = diff / 60.0
        
        # 4. Fallback: Scheduled (STA - STD)
        if blk_val == 0.0:
            std_mins = parse_hm(flight.get("std"))
            sta_mins = parse_hm(flight.get("sta"))
            if std_mins is not None and sta_mins is not None:
                 diff = sta_mins - std_mins
                 if diff < 0: diff += 1440
                 blk_val = diff / 60.0
        
        # Final Fallback to 2.0 (only if ALL above failed)
        if blk_val == 0.0:
            blk_val = 2.0
        
        if flight.get("flight_date") == target_date_str:
            recalc_total_block += blk_val
            
            # Aggregate by AC Type (Only for flights starting today)
            ac_type = normalize_ac_type(flight.get("aircraft_type"))
            ac_type_hours[ac_type] = ac_type_hours.get(ac_type, 0.0) + blk_val
            
        # Completed & OTP
        ata_str = flight.get("ata")
        on_blk_str = flight.get("on_block")
        atd_str = flight.get("atd")
        flight_status = flight.get("status", "").upper().strip()
        
        is_completed = False
        completion_source = None
        
        # [FIX v4.4] Date-aware completion logic using local_* fields + flight_date
        # filter_operational_flights now sets: local_std, local_sta, local_atd, local_ata,
        # local_flight_date, _original_db_date on each flight.
        from datetime import datetime as dt_cls
        today_vn = get_today_vn()
        
        # Use local_flight_date for date context (the actual local calendar day of departure)
        local_fdate_str = flight.get("local_flight_date") or flight.get("flight_date", target_date_str)
        try:
            local_fdate = date.fromisoformat(str(local_fdate_str))
        except (ValueError, TypeError):
            local_fdate = target_date
        
        # Use local times if available (set by filter_operational_flights), fallback to raw
        local_std_str = flight.get("local_std") or std
        local_sta_str = flight.get("local_sta") or sta
        local_atd_str = flight.get("local_atd") or atd_str
        local_ata_str = flight.get("local_ata") or ata_str
        
        # Calculate scheduled block time from local times
        scheduled_block_mins = 0
        if local_std_str and local_sta_str:
            std_mins = parse_hm(local_std_str)
            sta_mins = parse_hm(local_sta_str)
            if std_mins is not None and sta_mins is not None:
                scheduled_block_mins = sta_mins - std_mins
                if scheduled_block_mins < 0:
                    scheduled_block_mins += 1440  # Overnight
        
        if target_date > today_vn:
            is_completed = False
            completion_source = None
        elif target_date < today_vn:
            is_completed = True
            completion_source = "PAST_DATE"
        else:
            # Today: use real-time completion check with full datetime comparison
            now = dt_cls.now()

            if local_ata_str:
                is_completed = True
                completion_source = "ATA"
            elif flight_status in ["ARRIVED", "LANDED"] and local_atd_str:
                is_completed = True
                completion_source = "STATUS+ATD"
            elif local_atd_str and not local_ata_str:
                # Build full datetime from local_flight_date + local_atd
                atd_m = parse_hm(local_atd_str)
                if atd_m is not None and scheduled_block_mins > 0:
                    atd_dt = dt_cls.combine(local_fdate, dt_cls.strptime(local_atd_str[:5], "%H:%M").time())
                    expected_arrival_dt = atd_dt + timedelta(minutes=scheduled_block_mins + 60)
                    if now >= expected_arrival_dt:
                        is_completed = True
                        completion_source = "ATD+Buffer"
            elif local_sta_str and not local_atd_str and not local_ata_str:
                # FALLBACK: local STA + 30 min buffer
                sta_m = parse_hm(local_sta_str)
                if sta_m is not None:
                    sta_dt = dt_cls.combine(local_fdate, dt_cls.strptime(local_sta_str[:5], "%H:%M").time())
                    # Handle overnight: if STA < STD, arrival is next day
                    if local_std_str:
                        std_m = parse_hm(local_std_str)
                        if std_m is not None and sta_m < std_m:
                            sta_dt += timedelta(days=1)
                    expected_completion_dt = sta_dt + timedelta(minutes=30)
                    if now >= expected_completion_dt:
                        is_completed = True
                        completion_source = "STA+30 (Fallback)"
        
        if is_completed:
            completed_flights += 1
            
            # OTP Check: STD vs ATD (Departure OTP) logic as standard fallback
            if atd_str and std:
                std_mins = parse_hm(std)
                atd_mins = parse_hm(atd_str)
                
                if std_mins is not None and atd_mins is not None:
                    dep_diff = atd_mins - std_mins
                    
                    if dep_diff < -720: dep_diff += 1440
                    elif dep_diff > 720: dep_diff -= 1440
                    
                    if dep_diff <= otp_threshold_mins:
                        on_time_flights += 1
                    else:
                        delayed_flights += 1

    otp_percentage = 0.0
    otp_denominator = on_time_flights + delayed_flights
    if otp_denominator > 0:
        otp_percentage = (on_time_flights / otp_denominator) * 100.0

    # Format AC Breakdown
    sorted_ac = sorted(ac_type_hours.items(), key=lambda x: x[1], reverse=True)
    ac_breakdown_html = ""
    for k, v in sorted_ac:
        if v > 0:
            ac_breakdown_html += f"{k}: {v:.1f}h<br>"
    if not ac_breakdown_html: ac_breakdown_html = "No Data"

    aircraft_utilization = 0.0
    if total_aircraft_operation > 0:
         aircraft_utilization = round(recalc_total_block / total_aircraft_operation, 1)

    # Alerts logic remains...
    alerts = []
    for crew in crew_data:
        warning_level = crew.get("warning_level", "NORMAL")
        if warning_level in ["WARNING", "CRITICAL"]:
            alerts.append({
                "type": f"FTL_{warning_level}",
                "crew_id": crew.get("crew_id"),
                "crew_name": crew.get("crew_name"),
                "hours_28_day": crew.get("hours_28_day"),
                "hours_12_month": crew.get("hours_12_month"),
            })

    return {
        "total_crew": sum(crew_by_status.values()),
        "standby_available": crew_by_status["SBY"], # Legacy
        "total_aircraft_operation": total_aircraft_operation, 
        "sick_leave": crew_by_status["SL"] + crew_by_status["CSL"],
        "crew_sick_total": crew_by_status["SL"] + crew_by_status["CSL"],
        "crew_sick_by_position": sick_by_position,
        "total_flights": total_flights,
        "total_completed_flights": completed_flights, # KPI 4
        "total_block_hours": round(recalc_total_block, 1),
        "ac_type_breakdown": ac_breakdown_html, # KPI 3
        "aircraft_utilization": aircraft_utilization,
        "crew_by_status": crew_by_status,
        "flights_per_hour": flights_per_hour,
        "slots_by_base": slots_by_base,  # For departure slots chart
        "total_pax": total_pax,
        "otp_percentage": otp_percentage
    }


def get_completed_flights_detail(
    flight_data: List[Dict[str, Any]],
    target_date: date = None
) -> List[Dict[str, Any]]:
    """
    Return per-flight completion details for verification popup.
    Uses same date-aware logic as calculate_dashboard_summary.
    Relies on local_* fields set by filter_operational_flights.
    """
    target_date = target_date or get_today_vn()
    target_date_str = target_date.isoformat()

    def parse_hm(t_str):
        if not t_str or ":" not in t_str: return None
        try:
            parts = t_str.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None

    today_vn = get_today_vn()
    completed = []

    for flight in flight_data:
        std = flight.get("std", "")
        sta = flight.get("sta", "")
        ata_str = flight.get("ata")
        atd_str = flight.get("atd")
        flight_status = flight.get("status", "").upper().strip()

        is_completed = False
        completion_source = None

        # Use local_* fields (set by filter_operational_flights)
        local_fdate_str = flight.get("local_flight_date") or flight.get("flight_date", target_date_str)
        try:
            local_fdate = date.fromisoformat(str(local_fdate_str))
        except (ValueError, TypeError):
            local_fdate = target_date

        local_std_str = flight.get("local_std") or std
        local_sta_str = flight.get("local_sta") or sta
        local_atd_str = flight.get("local_atd") or atd_str
        local_ata_str = flight.get("local_ata") or ata_str

        # Calculate scheduled block time from local times
        scheduled_block_mins = 0
        if local_std_str and local_sta_str:
            std_mins = parse_hm(local_std_str)
            sta_mins = parse_hm(local_sta_str)
            if std_mins is not None and sta_mins is not None:
                scheduled_block_mins = sta_mins - std_mins
                if scheduled_block_mins < 0:
                    scheduled_block_mins += 1440

        if target_date > today_vn:
            is_completed = False
        elif target_date < today_vn:
            is_completed = True
            completion_source = "PAST_DATE"
        else:
            from datetime import datetime as dt_cls
            now = dt_cls.now()

            if local_ata_str:
                is_completed = True
                completion_source = "ATA"
            elif flight_status in ["ARRIVED", "LANDED"] and local_atd_str:
                is_completed = True
                completion_source = "STATUS+ATD"
            elif local_atd_str and not local_ata_str:
                atd_m = parse_hm(local_atd_str)
                if atd_m is not None and scheduled_block_mins > 0:
                    atd_dt = dt_cls.combine(local_fdate, dt_cls.strptime(local_atd_str[:5], "%H:%M").time())
                    expected_arrival_dt = atd_dt + timedelta(minutes=scheduled_block_mins + 60)
                    if now >= expected_arrival_dt:
                        is_completed = True
                        completion_source = "ATD+Buffer"
            elif local_sta_str and not local_atd_str and not local_ata_str:
                sta_m = parse_hm(local_sta_str)
                if sta_m is not None:
                    sta_dt = dt_cls.combine(local_fdate, dt_cls.strptime(local_sta_str[:5], "%H:%M").time())
                    # Handle overnight: if STA < STD, arrival is next day
                    if local_std_str:
                        std_m = parse_hm(local_std_str)
                        if std_m is not None and sta_m < std_m:
                            sta_dt += timedelta(days=1)
                    expected_completion_dt = sta_dt + timedelta(minutes=30)
                    if now >= expected_completion_dt:
                        is_completed = True
                        completion_source = "STA+30"

        if is_completed:
            dep = flight.get("departure", "")
            arr = flight.get("arrival", "")
            completed.append({
                "flight_number": flight.get("flight_number", ""),
                "aircraft_reg": flight.get("aircraft_reg", ""),
                "aircraft_type": normalize_ac_type(flight.get("aircraft_type")),
                "route": f"{dep}→{arr}",
                "std": (flight.get("local_std") or std or "")[:5],
                "sta": (flight.get("local_sta") or sta or "")[:5],
                "atd": (flight.get("local_atd") or atd_str or "")[:5] if (local_atd_str or atd_str) else "",
                "ata": (flight.get("local_ata") or ata_str or "")[:5] if (local_ata_str or ata_str) else "",
                "completion_source": completion_source,
            })

    return completed


# =========================================================
# Data Transformation for Database
# =========================================================

def transform_aims_crew_to_db(aims_crew: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform AIMS crew data to database format.
    
    Args:
        aims_crew: Raw crew data from AIMS API
        
    Returns:
        Formatted record for database insertion
    """
    gender = aims_crew.get("gender", "")
    if gender not in ["M", "F"]:
        gender = None

    return {
        "crew_id": str(aims_crew.get("crew_id", "")),
        "crew_name": aims_crew.get("crew_name", ""),
        "first_name": aims_crew.get("first_name", ""),
        "last_name": aims_crew.get("last_name", ""),
        "three_letter_code": aims_crew.get("three_letter_code", ""),
        "gender": gender,
        "email": aims_crew.get("email", ""),
        "cell_phone": aims_crew.get("cell_phone", ""),
        "base": aims_crew.get("base", ""),
        "source": "AIMS",
        "updated_at": datetime.now().isoformat()
    }


def transform_aims_flight_to_db(aims_flight: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform AIMS flight data to database format.
    
    Args:
        aims_flight: Raw flight data from AIMS API
        
    Returns:
        Formatted record for database insertion
    """
    return {
        "flight_date": aims_flight.get("flight_date"),
        "carrier_code": aims_flight.get("carrier_code", ""),
        "flight_number": aims_flight.get("flight_number"),
        "departure": aims_flight.get("departure", ""),
        "arrival": aims_flight.get("arrival", ""),
        "aircraft_type": aims_flight.get("aircraft_type", ""),
        "aircraft_reg": aims_flight.get("aircraft_reg", ""),
        # Detailed fields
        "std": aims_flight.get("std", ""),
        "sta": aims_flight.get("sta", ""),
        "etd": aims_flight.get("etd", ""),
        "eta": aims_flight.get("eta", ""),
        "off_block": aims_flight.get("off_block", ""),
        "on_block": aims_flight.get("on_block", ""),
        "delay_code_1": aims_flight.get("delay_code_1", ""),
        "delay_time_1": aims_flight.get("delay_time_1", 0),
        "pax_total": aims_flight.get("pax_total", 0),
        "source": "AIMS",
        "updated_at": datetime.now().isoformat()
    }


# =========================================================
# Data Validation
# =========================================================

def validate_crew_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a crew record.
    
    Args:
        record: Crew data to validate
        
    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []
    
    crew_id = record.get("crew_id", "")
    if not crew_id:
        errors.append("crew_id is required")
    
    crew_name = record.get("crew_name", "")
    if not crew_name or len(crew_name) < 2:
        errors.append("crew_name must be at least 2 characters")
    
    gender = record.get("gender", "")
    if gender and gender not in ["M", "F", ""]:
        errors.append("gender must be M or F")
    
    return (len(errors) == 0, errors)


def validate_flight_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a flight record.
    
    Args:
        record: Flight data to validate
        
    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []
    
    if not record.get("flight_number"):
        errors.append("flight_number is required")
    
    dep = record.get("departure", "")
    if not dep or len(dep) != 3:
        errors.append("departure must be 3-character IATA code")
    
    arr = record.get("arrival", "")
    if not arr or len(arr) != 3:
        errors.append("arrival must be 3-character IATA code")
    
    return (len(errors) == 0, errors)


# =========================================================
# Operational Logic
# =========================================================

def filter_operational_flights(flight_data: List[Dict[str, Any]], target_date: date, supabase=None) -> List[Dict[str, Any]]:
    """
    Filter flights for the operational day.
    
    IMPORTANT LOGIC (v3.3 - Matched to AIMS DayRepReport):
    - Rule 1: Same-date flights are included, UNLESS they are "phantoms":
      local STD falls on next calendar day >= 04:00 AND no prev-date copy
      exists. Flights with prev-date copies are daily recurring flights
      that AIMS correctly assigned to target date.
    - Rule 2: Previous-date flights are EXCLUDED (prevents double-counting).
    - Rule 3: Next-date flights are included if local STD < 04:00
      (early morning flights still in current ops day).
    """
    # [FIX v4.4] Import get_airport_timezone here — this was previously missing,
    # causing ALL flights to hit the except handler and skip local time conversion.
    from airport_timezones import get_airport_timezone
    
    target_date_str = target_date.isoformat()
    prev_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)
    prev_date_str = prev_date.isoformat()
    next_date_str = next_date.isoformat()
    
    # Dynamic Fetch: Get cancelled flights from aims_flight_mod_log
    cancelled_flights = set()
    if supabase:
        try:
            # Look for deletions that apply to this operational period
            # Modified around target date
            res = supabase.table('aims_flight_mod_log') \
                .select('flight_date, flight_number, departure') \
                .eq('modification_type', 'DELETED') \
                .execute()
            if res.data:
                for log in res.data:
                    cancelled_flights.add((log['flight_date'], log['flight_number'], log['departure']))
            logger.info(f"Loaded {len(cancelled_flights)} dynamic cancellations from AIMS log")
        except Exception as e:
            logger.error(f"Failed to fetch dynamic cancellations: {e}")
    
    # Pre-compute: which (flight_number, departure) exist on PREV date?
    # Used by Rule 1 to distinguish legitimate daily recurring flights from
    # phantom flights. Legitimate flights exist on both prev and target dates
    # (daily recurring). Phantoms exist only on target date (UTC window artifacts).
    prev_date_keys = set()
    for f in flight_data:
        fd = f.get("flight_date", "")
        fd_str = fd.isoformat() if hasattr(fd, 'isoformat') else fd
        if fd_str == prev_date_str:
            fn = f.get("flight_number", "").strip()
            dep = f.get("departure", "")
            prev_date_keys.add((fn, dep))
    
    ops_flights = []
    
    # Operational Window Boundaries (Local)
    # Start: Target Date 04:00
    # End: Next Date 03:59
    ops_start_boundary = datetime.combine(target_date, datetime.strptime("04:00", "%H:%M").time())
    ops_end_boundary = datetime.combine(next_date, datetime.strptime("03:59", "%H:%M").time())

    for flight in flight_data:
        std_str = flight.get("std", "")
        f_date_raw = flight.get("flight_date", target_date_str)
        # Handle both date objects and ISO strings
        if hasattr(f_date_raw, 'isoformat'):
            f_date_obj = f_date_raw
            f_date_str = f_date_raw.isoformat()
        else:
            f_date_str = str(f_date_raw)
            try:
                f_date_obj = date.fromisoformat(f_date_str)
            except ValueError:
                f_date_obj = target_date # Fallback

        flight_number = flight.get("flight_number", "").strip()
        dep_airport = flight.get("departure", "")

        if (f_date_str, flight_number, dep_airport) in cancelled_flights:
            continue

        if std_str and ":" in std_str:
            try:
                # Get timezone offset for local time conversion
                tz_offset = get_airport_timezone(dep_airport)
                
                # Parse UTC datetime from DB flight_date + scheduled STD
                utc_dt = datetime.combine(
                    f_date_obj,
                    datetime.strptime(std_str[:5], "%H:%M").time()
                )
                
                # Convert to local station datetime
                local_dt = utc_dt + timedelta(hours=tz_offset)
                
                # ====================================================
                # LOGIC v4.0: Strict 04:00 Local Ops Day Window
                # ====================================================
                # A flight belongs to the operational day if its local STD 
                # falls within [Today 04:00, Tomorrow 03:59]
                if ops_start_boundary <= local_dt <= ops_end_boundary:
                    include_flight = True
                else:
                    include_flight = False
                
                if include_flight:
                    # Create a copy and add local format for frontend
                    f_copy = flight.copy()
                    
                    # 1. Base STD/STA Local Conversion
                    f_copy['local_std'] = local_dt.strftime("%H:%M")
                    
                    sta_raw = flight.get("sta", "")
                    arr_airport = flight.get("arrival", "")
                    arr_tz = get_airport_timezone(arr_airport)
                    dep_tz = tz_offset # Already calculated for local_dt
                    
                    if sta_raw and ":" in sta_raw:
                        utc_sta = datetime.combine(f_date_obj, datetime.strptime(sta_raw[:5], "%H:%M").time())
                        f_copy['local_sta'] = (utc_sta + timedelta(hours=arr_tz)).strftime("%H:%M")

                    # 2. STATUS Times Local Conversion (ETD/ATD/TKOF use Dep TZ, ETA/ATA/TDWN use Arr TZ)
                    time_fields = [
                        ('etd', dep_tz, 'local_etd'),
                        ('atd', dep_tz, 'local_atd'),
                        ('tkof', dep_tz, 'local_tkof'),
                        ('eta', arr_tz, 'local_eta'),
                        ('ata', arr_tz, 'local_ata'),
                        ('tdwn', arr_tz, 'local_tdwn')
                    ]
                    
                    for field, tz, local_key in time_fields:
                        val = flight.get(field)
                        if val and ":" in val:
                            try:
                                utc_val = datetime.combine(f_date_obj, datetime.strptime(val[:5], "%H:%M").time())
                                f_copy[local_key] = (utc_val + timedelta(hours=tz)).strftime("%H:%M")
                            except: pass

                    # Keep original flight_date for operational day tracking
                    f_copy['flight_date'] = target_date_str
                    f_copy['local_flight_date'] = local_dt.date().isoformat()  # For display
                    f_copy['_is_ops_filtered'] = True
                    f_copy['_original_db_date'] = f_date_str  # For debugging
                    ops_flights.append(f_copy)

            except Exception as e:
                # If parsing fails, still include target_date flights
                if f_date_str == target_date_str:
                    f_copy = flight.copy()
                    f_copy['flight_date'] = target_date_str
                    f_copy['_is_ops_filtered'] = True
                    f_copy['_parse_error'] = str(e)
                    ops_flights.append(f_copy)
                
    # deduplicate based on (base_flight_number, departure)
    # This handles cases like 1250 and 1250A being the same flight operational-wise
    groups = {}
    for flt in ops_flights:
        fn_full = flt.get("flight_number", "").strip()
        base_fn = normalize_flight_id(fn_full)
        
        dep = flt.get("departure", "")
        key = (base_fn, dep)
        
        if key not in groups:
            groups[key] = []
        groups[key].append(flt)
    
    unique_flights = []
    for key, variants in groups.items():
        if len(variants) == 1:
            unique_flights.append(variants[0])
            continue
            
        # Pick the best candidate
        best = variants[0]
        for v in variants[1:]:
            v_status = v.get("status", "").upper()
            best_status = best.get("status", "").upper()
            
            # Priority 1: Suffix over no-suffix (e.g. 1250A over 1250)
            v_num = normalize_flight_id(v.get("flight_number", ""))
            best_num = normalize_flight_id(best.get("flight_number", ""))
            
            v_has_suffix = v.get("flight_number", "").strip() != v_num
            best_has_suffix = best.get("flight_number", "").strip() != best_num
            
            if v_has_suffix and not best_has_suffix:
                best = v
                continue
            
            # Priority 2: ARRIVED/DEPARTED over SCHEDULED
            if (v_status in ["ARRIVED", "DEPARTED"]) and (best_status == "SCHEDULED"):
                best = v
                continue
                
            # Priority 3: Latest status
            status_rank = {"ARRIVED": 3, "DEPARTED": 2, "SCHEDULED": 1, "CANCELLED": 0}
            if status_rank.get(v_status, -1) > status_rank.get(best_status, -1):
                best = v
        
        unique_flights.append(best)
            
    return unique_flights


# =========================================================
# Main Data Processor Class
# =========================================================

class DataProcessor:
    """
    Main data processor for Aviation Operations Dashboard.
    
    Handles both AIMS API and CSV fallback data sources.
    """
    
    def __init__(self, data_source: str = "AIMS"):
        """
        Initialize data processor.
        
        Args:
            data_source: "AIMS" or "CSV"
        """
        self.data_source = data_source
        self._supabase = None
        self._aims_client = None
    
    @property
    def supabase(self):
        """Lazy load Supabase client."""
        if self._supabase is None:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                self._supabase = create_client(url, key)
        return self._supabase
    
    @property
    def aims_client(self):
        """Lazy load AIMS client."""
        if self._aims_client is None:
            from aims_soap_client import AIMSSoapClient
            self._aims_client = AIMSSoapClient()
        return self._aims_client
    
    def set_data_source(self, source: str):
        """Set data source (AIMS or CSV)."""
        if source in ["AIMS", "CSV"]:
            self.data_source = source
            logger.info(f"Data source set to: {source}")
    
    def get_best_ftl_date(self, target_date: date = None) -> str:
        """
        Find the best calculation_date for FTL data.
        Prefers target_date if it has meaningful data, otherwise falls back
        to the latest date with non-zero hours.
        
        Returns:
            ISO date string of the best available FTL data date.
        """
        target_date = target_date or get_today_vn()
        target_iso = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
        
        if not self.supabase:
            return target_iso
        
        try:
            # Check if target_date has meaningful data
            check = self.supabase.table("crew_flight_hours") \
                .select("hours_28_day") \
                .eq("calculation_date", target_iso) \
                .gt("hours_28_day", 0) \
                .limit(5) \
                .execute()
            
            if check.data and len(check.data) >= 5:
                return target_iso
            
            # Fallback: find latest date with actual data
            # Get distinct dates ordered by most recent
            all_dates = self.supabase.table("crew_flight_hours") \
                .select("calculation_date, hours_28_day") \
                .gt("hours_28_day", 0) \
                .order("calculation_date", desc=True) \
                .limit(1) \
                .execute()
            
            if all_dates.data:
                best_date = all_dates.data[0]["calculation_date"]
                if best_date != target_iso:
                    logger.info(f"FTL fallback: using {best_date} instead of {target_iso} (no meaningful data on target date)")
                return best_date
            
        except Exception as e:
            logger.error(f"get_best_ftl_date failed: {e}")
        
        return target_iso

    def get_crew_hours(self, target_date: date = None, fallback_to_latest: bool = False) -> List[Dict[str, Any]]:
        """
        Get crew flight hours from database.
        
        Args:
            target_date: Date to filter by
            fallback_to_latest: If True, returns latest available calculation if target_date is empty
            
        Returns:
            List of crew flight hour records
        """
        target_date = target_date or get_today_vn()
        
        if self.supabase:
            try:
                # Use smart fallback to find date with real data
                if fallback_to_latest:
                    actual_date = self.get_best_ftl_date(target_date)
                else:
                    actual_date = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
                
                query = self.supabase.table("crew_flight_hours") \
                    .select("*") \
                    .eq("calculation_date", actual_date)
                    
                return fetch_all_rows(query)
            except Exception as e:
                logger.error(f"Failed to fetch crew hours: {e}")
        
        return []
    
    def get_crew_positions(self, target_date: date = None) -> Dict[str, str]:
        """
        Get crew positions from aims_leg_members table.
        Returns a dict: crew_id -> position (e.g. "CP", "FO", "PU", "FA").
        """
        target_date = target_date or get_today_vn()
        positions = {}
        
        if self.supabase:
            try:
                # Query aims_leg_members for crew positions on target date
                result = self.supabase.table("aims_leg_members") \
                    .select("crew_id, position") \
                    .eq("flight_date", target_date.isoformat()) \
                    .execute()
                
                if result.data:
                    for r in result.data:
                        cid = r.get("crew_id", "")
                        pos = r.get("position", "")
                        if cid and pos:
                            positions[str(cid)] = pos
                    
                    logger.info(f"Loaded {len(positions)} crew positions from aims_leg_members for {target_date}")
            except Exception as e:
                logger.warning(f"Failed to fetch crew positions from aims_leg_members: {e}")
        
        return positions
    
    def get_standby_records(self, target_date: date = None) -> List[Dict[str, Any]]:
        """
        Get standby records (SBY, SL, CSL) for a date.
        
        Args:
            target_date: Date to filter by
            
        Returns:
            List of standby records
        """
        target_date = target_date or get_today_vn()
        records = []
        
        if self.supabase:
            # Query standby_records table
            try:
                result = self.supabase.table("standby_records") \
                    .select("*") \
                    .lte("duty_start_date", target_date.isoformat()) \
                    .gte("duty_end_date", target_date.isoformat()) \
                    .execute()
                if result.data:
                    for r in result.data:
                        records.append({
                            "crew_id": r.get("crew_id"),
                            "crew_name": r.get("crew_name"),
                            "status": r.get("status"),
                            "base": r.get("base")
                        })
            except Exception as e:
                logger.error(f"Failed to fetch standby_records: {e}")
            
            # Also query fact_roster for SBY/SL/CSL activity types
            try:
                date_str = target_date.isoformat()
                result = self.supabase.table("fact_roster") \
                    .select("*") \
                    .gte("start_dt", f"{date_str}T00:00:00") \
                    .lte("start_dt", f"{date_str}T23:59:59") \
                    .in_("activity_type", ["SBY", "SL", "CSL", "SICK", "STANDBY", "SCL", "NS"]) \
                    .execute()
                if result.data:
                    for r in result.data:
                        records.append({
                            "crew_id": r.get("crew_id"),
                            "crew_name": r.get("crew_name", ""),
                            "status": r.get("activity_type"),
                            "base": ""
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch fact_roster standby: {e}")
        
        return records

    def get_roster_assignments(self, target_date: date = None) -> List[Dict[str, Any]]:
        """
        Get flight assignments from fact_roster for the target date.
        Used for 'No Crew = No Flight' filtering.
        """
        target_date = target_date or get_today_vn()
        records = []
        
        if self.supabase:
            try:
                date_str = target_date.isoformat()
                prev_date_str = (target_date - timedelta(days=1)).isoformat()
                next_date_str = (target_date + timedelta(days=1)).isoformat()
                
                # 1. Fetch from fact_roster (Step 5 of sync)
                # Fetch for 3 days to match flight window, with pagination
                start = 0
                step = 1000
                while start < 5000:
                    result = self.supabase.table("fact_roster") \
                        .select("flight_no, crew_id") \
                        .gte("start_dt", f"{prev_date_str}T00:00:00") \
                        .lte("start_dt", f"{next_date_str}T23:59:59") \
                        .not_.is_("flight_no", "null") \
                        .neq("flight_no", "") \
                        .range(start, start + step - 1) \
                        .execute()
                    
                    if not result.data:
                        break
                    records.extend(result.data)
                    if len(result.data) < step:
                        break
                    start += step

                # 2. Fetch from flight_crew (Step 2 of sync - faster updates)
                # Fetch for 3 days window, with pagination
                start = 0
                while start < 5000:
                    try:
                        res_fc = self.supabase.table("flight_crew") \
                            .select("flight_number, crew_id") \
                            .in_("flight_date", [prev_date_str, date_str, next_date_str]) \
                            .range(start, start + step - 1) \
                            .execute()
                            
                        if not res_fc.data:
                            break
                            
                        # normalize keys to match fact_roster (flight_no vs flight_number)
                        for r in res_fc.data:
                            records.append({
                                "flight_no": r.get("flight_number"),
                                "crew_id": r.get("crew_id")
                            })
                            
                        if len(res_fc.data) < step:
                            break
                        start += step
                    except Exception as e:
                        logger.warning(f"Failed to fetch flight_crew fallbacks: {e}")
                        break

                if records:
                    logger.info(f"Fetched {len(records)} roster assignments (3-day window, fact_roster + flight_crew)")
            except Exception as e:
                logger.warning(f"Failed to fetch roster assignments: {e}")
                
        return records
    
    def get_flights(self, target_date: date = None) -> List[Dict[str, Any]]:
        """
        Get flights for Operational Day (04:00 VN target_date to 03:59 VN next_date).
        
        Note: Database stores STD in UTC. We need to fetch flights from:
        - prev_date (UTC 21:00-23:59 = VN 04:00-06:59 next day)
        - target_date (all flights, filter in calculate_dashboard_summary)
        - next_date (UTC 00:00-20:59 = VN 07:00-03:59+1)
        
        Args:
            target_date: Date to filter by (VN local date)
            
        Returns:
            List of flight records for the ops day window
        """
        target_date = target_date or get_today_vn()
        prev_date = target_date - timedelta(days=1)
        next_date = target_date + timedelta(days=1)
        
        all_flights = []
        
        if self.supabase:
            try:
                # Fetch prev_date flights (late night UTC = early morning VN next day)
                result_prev = self.supabase.table("flights") \
                    .select("*") \
                    .eq("flight_date", prev_date.isoformat()) \
                    .execute()
                all_flights.extend(result_prev.data or [])
                
                # Fetch target_date flights
                result_today = self.supabase.table("flights") \
                    .select("*") \
                    .eq("flight_date", target_date.isoformat()) \
                    .execute()
                all_flights.extend(result_today.data or [])
                
                # Fetch next_date flights
                result_tomorrow = self.supabase.table("flights") \
                    .select("*") \
                    .eq("flight_date", next_date.isoformat()) \
                    .execute()
                all_flights.extend(result_tomorrow.data or [])
            except Exception as e:
                logger.error(f"Failed to fetch flights: {e}")
        
        # 4. Apply Operational Window Filter
        return filter_operational_flights(all_flights, target_date, supabase=self.supabase)
    
    def get_dashboard_summary(self, target_date: date = None) -> Dict[str, Any]:
        """
        Get complete dashboard summary.
        
        Args:
            target_date: Date to calculate metrics for
            
        Returns:
            Dashboard summary with all KPIs
        """
        target_date = target_date or get_today_vn()
        
        from concurrent.futures import ThreadPoolExecutor
    
        with ThreadPoolExecutor(max_workers=5) as executor:
            f_crew = executor.submit(self.get_crew_hours, target_date, fallback_to_latest=True)
            f_sby = executor.submit(self.get_standby_records, target_date)
            f_flt = executor.submit(self.get_flights, target_date)
            f_asn = executor.submit(self.get_roster_assignments, target_date)
            f_pos = executor.submit(self.get_crew_positions, target_date)
            
            crew_hours = f_crew.result()
            standby = f_sby.result()
            flights = f_flt.result()
            assignments = f_asn.result()
            crew_positions = f_pos.result()
        
        summary = calculate_dashboard_summary(
            crew_data=crew_hours,
            flight_data=flights,
            standby_data=standby,
            target_date=target_date,
            assignments=assignments,
            crew_positions=crew_positions
        )
        
        # [REMOVED] operating_crew_count override
        
        summary["data_source"] = self.data_source
        
        return summary
    
    def get_aircraft_summary(self, target_date: date = None) -> Dict[str, Any]:
        """
        Get summary of all aircraft operating on target date.
        Returns list with flight count, block hours, utilization, etc.
        """
        target_date = target_date or get_today_vn()
        from airport_timezones import get_airport_timezone
        flights = self.get_flights(target_date)
        
        # Prepare date ranges
        prev_date = target_date - timedelta(days=1)
        next_date = target_date + timedelta(days=1)
        target_date_str = target_date.isoformat()
        prev_date_str = prev_date.isoformat()
        next_date_str = next_date.isoformat()

        # INVALID_REGS to filter out (type codes used as reg in test data)
        INVALID_REGS = {'VN-A320', 'VN-A321', 'VN-A322'}

        # [FIX] Do NOT refilter. self.get_flights already returns filtered ops day flights. 
        ops_flights = flights
        
        # [REMOVED] assignments-based filtering to stay consistent with dashboard KPIs
        # and ignore flight number suffix mismatches.
        


        # Group flights by aircraft reg
        aircraft_data = {}
        for flt in ops_flights:
            # Since we filtered for Ops Day, all flights here validly belong to this day
            is_main_day = True 
                
            reg = flt.get("aircraft_reg", "")
            if not reg or reg in INVALID_REGS:
                continue

            flight_number = flt.get("flight_number", "").strip()
            dep_airport = flt.get("departure", "")
            # Re-fetch flight date string for internal tracking
            f_date = flt.get("flight_date", target_date.isoformat())
            flight_date_str = f_date.isoformat() if hasattr(f_date, 'isoformat') else f_date

            if reg not in aircraft_data:
                aircraft_data[reg] = {
                    "reg": reg,
                    "type": normalize_ac_type(flt.get("aircraft_type")),
                    "flights": [],
                    "block_minutes": 0,
                    "first_std": None,
                    "last_sta": None,
                    "first_dep": None,
                    "last_arr": None,
                    "last_dep_airport": None, # [FIX] Track last dep for TZ
                    "latest_dep_key": None, # (flight_date, std)
                    "last_std": None,
                    "last_flight_date": None
                }
            
            ac = aircraft_data[reg]
            if is_main_day:
                ac["flights"].append(flt.get("flight_number", ""))
                # Track for FIRST/LAST logic (only for main day)
                # Actually, standard is FIRST/LAST of the day, 
                # but let's keep it consistent.
            
            # Parse times
            std = flt.get("std", "")
            sta = flt.get("sta", "")
            off_block = flt.get("off_block", "")
            on_block = flt.get("on_block", "")
            
            # Track first/last times
            if std:
                # First Flight: Earliest Departure
                current_dep_key = (flight_date_str, std)
                
                if ac["latest_dep_key"] is None or current_dep_key < (ac["first_flight_date"], ac["first_std"]) if ac.get("first_flight_date") else True:
                     # Re-evaluating first logic: Just minimize (date, std)
                     pass

                if ac["first_std"] is None or current_dep_key < (ac.get("first_flight_date", "9999-99-99"), ac["first_std"]):
                    ac["first_std"] = std
                    ac["first_dep"] = dep_airport
                    ac["first_flight_date"] = flight_date_str

                # Last Flight: Latest Departure
                if ac["latest_dep_key"] is None or current_dep_key > ac["latest_dep_key"]:
                    ac["latest_dep_key"] = current_dep_key
                    ac["last_sta"] = sta # This is the STA of the last flight
                    ac["last_std"] = std # Store STD to check overnight
                    ac["last_arr"] = flt.get("arrival", "")
                    ac["last_dep_airport"] = dep_airport # [FIX]
                    ac["last_flight_date"] = flight_date_str
            
            # Calculate block time - Priority: Actual > Scheduled
            block_mins = 0
            
            if off_block and on_block:
                # Use actual times
                try:
                    off_parts = off_block.split(":")
                    on_parts = on_block.split(":")
                    off_mins = int(off_parts[0]) * 60 + int(off_parts[1])
                    on_mins = int(on_parts[0]) * 60 + int(on_parts[1])
                    if on_mins < off_mins:
                        on_mins += 24 * 60  # Overnight
                    block_mins = on_mins - off_mins
                except:
                    pass
            elif std and sta:
                # Fallback to scheduled times (STD/STA)
                try:
                    std_parts = std.split(":")
                    sta_parts = sta.split(":")
                    std_mins = int(std_parts[0]) * 60 + int(std_parts[1])
                    sta_mins = int(sta_parts[0]) * 60 + int(sta_parts[1])
                    if sta_mins < std_mins:
                        sta_mins += 24 * 60  # Overnight
                    block_mins = sta_mins - std_mins
                except:
                    pass
            
            # [FIX] Only sum block minutes for main day
            if is_main_day:
                ac["block_minutes"] += block_mins
        
        # [FIX v4.3] Date-aware aircraft status logic
        from datetime import timezone
        today_vn = get_today_vn()
        is_future_date = target_date > today_vn
        is_past_date = target_date < today_vn
        
        now = datetime.now(timezone.utc)
        now_mins = now.hour * 60 + now.minute
        total_aircraft = len(aircraft_data)
        
        # Calculate fleet-wide average: Total scheduled hours / Number of aircraft
        total_scheduled_mins = sum(ac["block_minutes"] for ac in aircraft_data.values())
        fleet_avg_mins = total_scheduled_mins / total_aircraft if total_aircraft > 0 else 1
        
        result = []
        
        for reg, ac in aircraft_data.items():
            block_hours = round(ac["block_minutes"] / 60, 1)
            
            # Utilization % based on 24h operational day
            utilization = round((ac["block_minutes"] / 1440) * 100, 1)
            
            # [FIX v4.3] Date-aware status:
            # - Future date: all aircraft "FLYING" (not yet operated)
            # - Past date: all aircraft "GROUND" (all flights done)
            # - Today: real-time check
            if is_future_date:
                status = "FLYING"
            elif is_past_date:
                has_any_flight = any(flt.get("aircraft_reg") == reg for flt in flights)
                status = "GROUND" if has_any_flight else "FLYING"
            else:
                # Today: Determine status - GROUND only if ALL flights are completed
                # A flight is completed if: has ATA, or ETA+60min passed, or ATD+block+60min passed
                all_flights_completed = True
                has_any_flight = False
                
                for flt in flights:
                    if flt.get("aircraft_reg") != reg:
                        continue
                        
                    has_any_flight = True
                    ata = flt.get("ata", "")
                    eta = flt.get("eta", "")
                    atd = flt.get("atd", "")
                    sta = flt.get("sta", "")
                    std = flt.get("std", "")
                    
                    flight_completed = False
                    
                    # Check 1: Has ATA → Completed
                    if ata:
                        flight_completed = True
                    else:
                        # Check 2: Has ETA and now > ETA + 60min
                        if eta:
                            try:
                                eta_parts = eta.split(":")
                                eta_mins = int(eta_parts[0]) * 60 + int(eta_parts[1])
                                if now_mins > eta_mins + 60:
                                    flight_completed = True
                                elif now_mins < eta_mins - 720:  # Handle overnight
                                    flight_completed = True
                            except:
                                pass
                        
                        # Check 3: Has ATD and now > ATD + scheduled_block + 60min
                        if not flight_completed and atd and std and sta:
                            try:
                                atd_parts = atd.split(":")
                                atd_mins = int(atd_parts[0]) * 60 + int(atd_parts[1])
                                std_parts = std.split(":")
                                sta_parts = sta.split(":")
                                std_mins = int(std_parts[0]) * 60 + int(std_parts[1])
                                sta_mins = int(sta_parts[0]) * 60 + int(sta_parts[1])
                                if sta_mins < std_mins:
                                    sta_mins += 1440
                                scheduled_block = sta_mins - std_mins
                                expected_arrival = atd_mins + scheduled_block + 60
                                if expected_arrival >= 1440:
                                    expected_arrival -= 1440
                                if now_mins > expected_arrival or (now_mins < expected_arrival - 720):
                                    flight_completed = True
                            except:
                                pass
                    
                    if not flight_completed:
                        all_flights_completed = False
                        break
                
                # Status: GROUND only if all flights completed
                status = "GROUND" if (has_any_flight and all_flights_completed) else "FLYING"
            
            # Format First/Last times
            # [FIX v4.5] Absolute local minutes logic for reliable next-day (+) indicators
            first_flight_local = "-"
            if ac["first_std"] and ac["first_flight_date"] and ac["first_dep"]:
                try:
                    # Get timezone offset for departure airport
                    first_tz_offset = get_airport_timezone(ac["first_dep"])
                    # Calculate absolute local minutes since target_date 00:00 UTC
                    f_date_obj = date.fromisoformat(ac["first_flight_date"])
                    days_diff = (f_date_obj - target_date).days
                    
                    std_parts = ac["first_std"].split(":")
                    utc_abs_mins = (days_diff * 1440) + int(std_parts[0]) * 60 + int(std_parts[1])
                    local_abs_mins = utc_abs_mins + (first_tz_offset * 60)
                    
                    # Format as time of whatever calendar day it falls on
                    display_mins = local_abs_mins % 1440
                    first_flight_local = f"{display_mins // 60:02d}:{display_mins % 60:02d}"
                    
                    # Mark '+' if local time falls on target_date + 1 (relative to local midnight)
                    if local_abs_mins >= 1440:
                         first_flight_local += "+"
                except:
                    first_flight_local = ac["first_std"][:5] if ac["first_std"] else "-"

            last_flight_local = "-"
            if ac["last_sta"] and ac["last_flight_date"] and ac["last_arr"]:
                try:
                    # 1. Get local arrival minutes
                    last_arr_tz = get_airport_timezone(ac["last_arr"])
                    l_date_obj = date.fromisoformat(ac["last_flight_date"])
                    days_diff_arr = (l_date_obj - target_date).days
                    
                    sta_parts = ac["last_sta"].split(":")
                    sta_utc_abs = (days_diff_arr * 1440) + int(sta_parts[0]) * 60 + int(sta_parts[1])
                    
                    # Handle AIMS overnight STA: if STA < STD and they are same flight_date,
                    # it means STA is actually on next day.
                    std_parts_last = ac["last_std"].split(":")
                    std_val = int(std_parts_last[0]) * 60 + int(std_parts_last[1])
                    sta_val = int(sta_parts[0]) * 60 + int(sta_parts[1])
                    if sta_val < std_val:
                        sta_utc_abs += 1440 # Arrival is next day relative to departure
                    
                    sta_local_abs = sta_utc_abs + (last_arr_tz * 60)
                    
                    # 2. Get local departure minutes (to detect overnight leg)
                    last_dep_tz = get_airport_timezone(ac.get("last_dep_airport", ac["last_arr"]))
                    std_local_abs = (days_diff_arr * 1440) + std_val + (last_dep_tz * 60)
                    
                    # Format last flight local time
                    display_mins_last = sta_local_abs % 1440
                    last_flight_local = f"{display_mins_last // 60:02d}:{display_mins_last % 60:02d}"
                    
                    # Mark '+' if:
                    # - Dep is on next day (local_abs >= 1440)
                    # - OR it's an overnight leg (local_arr_abs > local_dep_abs crossing midnight)
                    is_next_day_dep = std_local_abs >= 1440
                    is_overnight = (sta_local_abs > std_local_abs) and (sta_local_abs >= 1440)
                    
                    if is_next_day_dep or is_overnight:
                        last_flight_local += "+"
                except:
                    last_flight_local = ac["last_sta"][:5] if ac["last_sta"] else "-"


            result.append({
                "reg": reg,
                "type": ac["type"],
                "flight_count": len(ac["flights"]),
                "flight_list": ac["flights"],
                "block_hours": block_hours,
                "utilization": utilization,
                "first_flight": first_flight_local,
                "last_flight": last_flight_local,
                "status": status
            })
        
        # Sort by flight count descending
        result.sort(key=lambda x: x["flight_count"], reverse=True)
        
        return {
            "aircraft": result,
            "total": len(result),
            "date": target_date.isoformat()
        }
    
    def _get_operating_crew_count(self, flights: List[Dict[str, Any]], target_date: date) -> int:
        """
        Count unique crew members assigned to flights in Operational Day.
        Reads from flight_crew table (synced by scheduler from leg_members API).
        
        Ops Day = 04:00 target_date to 03:59 next_date
        
        Args:
            flights: List of flight records for the day
            target_date: Date to count crew for
            
        Returns:
            Count of unique crew members operating
        """
        if not flights:
            return 0
        
        next_date = target_date + timedelta(days=1)
        unique_crew = set()
        
        # Try to get from flight_crew table (cached from leg_members API)
        if self.supabase:
            try:
                # Fetch target_date crew
                result_today = self.supabase.table("flight_crew") \
                    .select("crew_id, flight_date, flight_number, departure") \
                    .eq("flight_date", target_date.isoformat()) \
                    .execute()
                
                # Fetch next_date crew
                result_tomorrow = self.supabase.table("flight_crew") \
                    .select("crew_id, flight_date, flight_number, departure") \
                    .eq("flight_date", next_date.isoformat()) \
                    .execute()

                # Define operational flight keys for precise filtering
                ops_keys = set()
                for flt in flights:
                    f_date = flt.get("flight_date", "")
                    f_date_str = f_date.isoformat() if hasattr(f_date, 'isoformat') else f_date
                    # Normalize flight number for robust matching with roster data
                    f_num_norm = normalize_flight_id(flt.get("flight_number"))
                    ops_keys.add((f_date_str, f_num_norm, flt.get("departure")))

                # Process results and filter by operational flight keys
                all_raw_crew = (result_today.data or []) + (result_tomorrow.data or [])
                for r in all_raw_crew:
                    crew_id = r.get("crew_id")
                    if not crew_id: continue
                    
                    # Also normalize roster/crew flight number for matching
                    r_num_norm = normalize_flight_id(r.get("flight_number"))
                    key = (r.get("flight_date"), r_num_norm, r.get("departure"))
                    if key in ops_keys:
                        unique_crew.add(crew_id)
                
                if unique_crew:
                    logger.info(f"Operating crew count from flight_crew (filtered): {len(unique_crew)} for {len(flights)} flights")
                    return len(unique_crew)
                    
            except Exception as e:
                logger.debug(f"flight_crew table not available: {e}")
        
        # Fallback: Estimate based on flight count
        # Average crew per flight: 6 (2 pilots + 4 cabin crew)
        # But crew fly multiple legs, so estimate unique crew = flights * 1.6
        estimated = int(len(flights) * 1.6)
        
        # Cap at reasonable maximum (assume crew fly avg 2 legs/day)
        max_crew = int(len(flights) * 4 / 2)  # 4 crew per flight, 2 legs each
        
        operating_count = min(estimated, max_crew)
        logger.info(f"Operating crew estimated: {operating_count} (from {len(flights)} flights)")
        
        return operating_count

    # =========================================================
    # AIMS Integration Business Logic
    # =========================================================

    def calculate_28day_rolling_hours(self, crew_id: str, target_date: date = None) -> float:
        """
        Calculate sum(block_minutes) for last 28 days from fact_actuals.
        
        Logic: SUM(block_minutes) WHERE dep_actual_dt BETWEEN (Today - 28) AND Today.
        """
        target_date = target_date or get_today_vn()
        start_date = target_date - timedelta(days=28)
        
        if not self.supabase:
            return 0.0
            
        try:
            result = self.supabase.table("fact_actuals") \
                .select("block_minutes") \
                .eq("crew_id", crew_id) \
                .gte("dep_actual_dt", start_date.isoformat()) \
                .lte("dep_actual_dt", target_date.isoformat()) \
                .execute()
            
            total_minutes = sum(row.get("block_minutes", 0) for row in result.data or [])
            return round(total_minutes / 60.0, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate 28-day hours for {crew_id}: {e}")
            return 0.0

    def calculate_ftl_alert_status(self, hours_28d: float, hours_12m: float) -> str:
        """Calculate warning level based on FTL hours."""
        from data_processor import calculate_warning_level
        return calculate_warning_level(hours_28d, hours_12m)

    def sync_and_calculate_ftl(self, target_date: date = None) -> int:
        """
        Comprehensive FTL Sync & Calculation.
        Optimized for Phase 1 "Fast Run" using Yesterday as anchor if Today is empty.
        """
        target_date = target_date or get_today_vn()
        logger.info(f"FTL SYNC: Target Date = {target_date}")

        # Check for cooldown (60 mins) to avoid excessive AIMS calls
        if self.supabase:
            try:
                last_job = self.supabase.table("etl_jobs") \
                    .select("started_at") \
                    .eq("job_name", "FTL Sync") \
                    .eq("status", "SUCCESS") \
                    .order("started_at", desc=True) \
                    .limit(1) \
                    .execute()
                if last_job.data:
                    last_time = datetime.fromisoformat(last_job.data[0]["started_at"].replace("Z", "+00:00"))
                    # Only check cooldown if it's the SAME target date
                    if datetime.now(last_time.tzinfo) - last_time < timedelta(minutes=60):
                        logger.info("  FTL Sync cooldown active (60m), skipping full calculation.")
                        return 0
            except Exception as e:
                logger.warning(f"Cooldown check failed, proceeding: {e}")

        # Step 0: Check if Today has any block hours. If not, anchor to Yesterday.
        # This solves the 0.0 display issue when Today's flights haven't started.
        original_target_date = target_date # Store original target_date for placeholder copy
        try:
            today_flights = self.supabase.table("aims_flights") \
                .select("block_time_minutes") \
                .eq("flight_date", target_date.isoformat()) \
                .gte("block_time_minutes", 10) \
                .limit(5) \
                .execute()
            
            if not today_flights.data:
                yesterday = target_date - timedelta(days=1)
                logger.info(f"  Today ({target_date}) has no actual flights yet. Anchoring rolling calculation to Yesterday ({yesterday}).")
                target_date = yesterday
        except Exception as e:
            logger.warning(f"  Error checking today's flights: {e}")

        # Step 1: Rapid Initial Populate ("Phase 1 Placeholder Copy")
        # Copy yesterday's data to Today's date immediately if Today is empty.
        # This gives the user data to look at while the heavy calculation runs.
        self._fast_copy_ftl_placeholder(original_target_date)

        logger.info(f"Starting optimized FTL calculation for {target_date}")
        
        if not self.aims_client or not self.supabase:
            logger.error("AIMS client or Supabase not initialized")
            return 0

        # Step 1: Build Flight Block Map (12 months)
        # Optimization: Priority 1: Use Database (aims_flights), Priority 2: AIMS API for gaps/recent
        # Heavy Calculation Step
        start_date_12m = target_date - timedelta(days=365)
        flight_block_map = {}
        
        logger.info("  Step 1/3: Building Flight Block Map (Database First)...")
        # 1.1 Load from Local DB
        try:
            db_flights = self.supabase.table("aims_flights") \
                .select("flight_date, flight_number, off_block, on_block") \
                .gte("flight_date", start_date_12m.isoformat()) \
                .lte("flight_date", target_date.isoformat()) \
                .execute()
            
            for f in db_flights.data or []:
                f_date = f["flight_date"]
                f_num = normalize_flight_id(f["flight_number"])
                ob = f.get("off_block")
                nib = f.get("on_block")
                
                if ob and nib:
                    try:
                        # Format "YYYY-MM-DD HH:MM:SS"
                        fmt = "%Y-%m-%d %H:%M:%S"
                        t1 = datetime.strptime(ob, fmt)
                        t2 = datetime.strptime(nib, fmt)
                        flight_block_map[(f_date, f_num)] = int((t2 - t1).total_seconds() / 60)
                    except: pass
        except Exception as e:
            logger.error(f"Failed to load flights from DB: {e}")

        # 1.2 Fetch from AIMS for the last 7 days (to ensure freshness) + gaps
        logger.info("  Step 1.2: Fetching recent/missing flights from AIMS...")
        aims_fetch_start = target_date - timedelta(days=7)
        current_start = aims_fetch_start
        while current_start <= target_date:
            current_end = min(current_start + timedelta(days=7), target_date)
            try:
                batch = self.aims_client.get_flights_range(current_start, current_end)
                for flt in batch:
                    f_date = flt.get("flight_date", "")
                    f_num = normalize_flight_id(flt.get("flight_number", ""))
                    if not f_date or not f_num: continue
                    
                    blk = flt.get("block_time", "00:00")
                    m = 0
                    if ":" in blk:
                        try:
                            parts = blk.split(":")
                            m = int(parts[0]) * 60 + int(parts[1])
                        except: pass
                    flight_block_map[(f_date, f_num)] = m
            except Exception as e:
                logger.error(f"Flight history AIMS fetch failed for {current_start}: {e}")
            current_start += timedelta(days=8)
        
        logger.info(f"  Final block map size: {len(flight_block_map)} flights")

        # Step 2: Get active crew members
        logger.info("  Step 2/3: Fetching crew members...")
        try:
            crew_res = self.supabase.table("crew_members").select("crew_id, crew_name").execute()
            all_crew = crew_res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch crew: {e}")
            return 0

        # Step 3: Calculate for each crew member (Parallel)
        logger.info(f"  Step 3/3: Calculating FTL for {len(all_crew)} crew members...")
        
        # Log job as running
        if self.supabase:
            self.supabase.table("etl_jobs").insert({
                "job_name": "FTL Sync",
                "status": "RUNNING",
                "started_at": datetime.now().isoformat()
            }).execute()

        ftl_records = []
        
        def process_one_crew(crew):
            cid = crew.get("crew_id")
            if not cid or str(cid).lower() == "none" or str(cid).strip() == "":
                return None
            try:
                # Fetch roster for 12 months
                sched = self.aims_client.get_crew_schedule(start_date_12m, target_date, crew_id=cid)
                
                total_mins_28d = 0
                total_mins_12m = 0
                start_date_28d_str = (target_date - timedelta(days=28)).isoformat()
                
                for item in sched:
                    s_dt = item.get("start_dt", "")
                    f_num_raw = item.get("flight_number")
                    if not s_dt or not f_num_raw: continue
                    
                    d_str = s_dt.split("T")[0]
                    f_num_norm = normalize_flight_id(f_num_raw)
                    
                    mins = flight_block_map.get((d_str, f_num_norm), 0)
                    total_mins_12m += mins
                    if d_str >= start_date_28d_str:
                        total_mins_28d += mins
                
                hours_28d = round(total_mins_28d / 60.0, 2)
                hours_12m = round(total_mins_12m / 60.0, 2)
                
                return {
                    "crew_id": cid,
                    "crew_name": crew.get("crew_name", ""),
                    "hours_28_day": hours_28d,
                    "hours_12_month": hours_12m,
                    "warning_level": self.calculate_ftl_alert_status(hours_28d, hours_12m),
                    "calculation_date": target_date.isoformat(),
                    "source": "AIMS_SYNC_OPT",
                    "updated_at": datetime.now().isoformat()
                }
            except:
                return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Process all crew to ensure full consistency across 3000+ crew
            futures = [executor.submit(process_one_crew, c) for c in all_crew]
            for future in as_completed(futures):
                res = future.result()
                if res: ftl_records.append(res)
        
        if ftl_records:
            try:
                self.supabase.table("crew_flight_hours").upsert(
                    ftl_records, 
                    on_conflict="crew_id,calculation_date"
                ).execute()
                
                # Success Log
                self.supabase.table("etl_jobs").insert({
                    "job_name": "FTL Sync",
                    "status": "SUCCESS",
                    "records_processed": len(ftl_records),
                    "completed_at": datetime.now().isoformat()
                }).execute()
                
                logger.info(f"  Successfully updated FTL for {len(ftl_records)} crew")
            except Exception as e:
                logger.error(f"Failed to upsert FTL results: {e}")
                
        return len(ftl_records)

    def _fast_copy_ftl_placeholder(self, target_date: date):
        """
        Rapidly copy the latest available valid FTL snapshot to the target date.
        This provides immediate data for the UI while full calculation runs.
        """
        if not self.supabase: return

        try:
            target_iso = target_date.isoformat()
            
            # 1. Check if target date already has substantial data
            existing = self.supabase.table("crew_flight_hours") \
                .select("hours_28_day") \
                .eq("calculation_date", target_iso) \
                .limit(10) \
                .execute()
            
            total_existing_hrs = sum(r.get("hours_28_day", 0) for r in (existing.data or []))
            if len(existing.data or []) >= 100 or total_existing_hrs > 50:
                logger.info(f"  Target date {target_iso} already has data. Skipping placeholder copy.")
                return

            # 2. Get the latest snapshot date
            latest_res = self.supabase.table("crew_flight_hours") \
                .select("calculation_date") \
                .order("calculation_date", desc=True) \
                .neq("calculation_date", target_iso) \
                .limit(1) \
                .execute()
            
            if not latest_res.data:
                logger.info("  No previous FTL data found for placeholder copy.")
                return
            
            latest_date = latest_res.data[0]["calculation_date"]
            logger.info(f"  Copying placeholder FTL data from {latest_date} to {target_iso}...")

            # 3. Fetch all records from latest date
            # We do this in batches if there are many crew (usually ~3000)
            all_records = []
            page_size = 1000
            for i in range(5): # Limit to 5000 crew for speed
                res = self.supabase.table("crew_flight_hours") \
                    .select("*") \
                    .eq("calculation_date", latest_date) \
                    .range(i*page_size, (i+1)*page_size - 1) \
                    .execute()
                if not res.data: break
                all_records.extend(res.data)

            if not all_records: return

            # 4. Prepare for upsert to target date
            placeholder_batch = []
            now_iso = datetime.now().isoformat()
            for r in all_records:
                # Remove original ID and creation time to allow new record insertion
                record = {
                    "crew_id": r["crew_id"],
                    "crew_name": r.get("crew_name"),
                    "hours_28_day": r.get("hours_28_day", 0),
                    "hours_12_month": r.get("hours_12_month", 0),
                    "warning_level": r.get("warning_level", "NORMAL"),
                    "calculation_date": target_iso,
                    "source": "PLACEHOLDER_COPY",
                    "updated_at": now_iso
                }
                placeholder_batch.append(record)

            # 5. Upsert batch
            if placeholder_batch:
                self.supabase.table("crew_flight_hours").upsert(
                    placeholder_batch,
                    on_conflict="crew_id,calculation_date"
                ).execute()
                logger.info(f"  Successfully copied {len(placeholder_batch)} placeholder FTL records to {target_iso}")

        except Exception as e:
            logger.error(f"  Failed to copy FTL placeholder: {e}")

    def get_crew_alert_status(self, hours_28d: float) -> str:
        """
        Determine alert level based on 28-day hours.
        - Yellow (WARNING): > 85 hours
        - Red (CRITICAL): > 95 hours
        """
        if hours_28d > 95:
            return "CRITICAL"
        elif hours_28d > 85:
            return "WARNING"
        return "NORMAL"

    def convert_to_gmt7(self, dt_str: str) -> str:
        """Convert UTC timestamp string to GMT+7."""
        if not dt_str:
            return ""
        try:
            # Simple offset - in production use pytz
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            dt_gmt7 = dt + timedelta(hours=7)
            return dt_gmt7.isoformat()
        except:
            return dt_str

    def get_top_crew_stats(self, days: int = 28, limit: int = 20, threshold: float = 100.0) -> List[Dict[str, Any]]:
        """
        Get top crew members by flight hours for the last N days.
        Optimized to avoid N+1 queries by fetching bulk data and aggregating in-memory.
        
        Args:
            days: Lookback period in days
            limit: Number of top crew to return
            threshold: Alert threshold for flight hours
            
        Returns:
            List of crew with aggregated hours and alert status
        """
        if not self.supabase:
            return []
            
        try:
            target_date = get_today_vn()
            start_date = target_date - timedelta(days=days)
            
            logger.info(f"Calculating bulk FTL stats for {days} days (since {start_date})")
            
            # 1. Fetch all flights in range to get block times
            # Note: Leg members join flights on (date, number, departure)
            flights_result = self.supabase.table("aims_flights") \
                .select("flight_date, flight_number, departure, block_time_minutes") \
                .gte("flight_date", start_date.isoformat()) \
                .execute()
                
            flight_mins_map = {}
            for f in flights_result.data or []:
                key = (f["flight_date"], f["flight_number"], f["departure"])
                flight_mins_map[key] = f.get("block_time_minutes", 0) or 0
                
            # 2. Fetch all leg members (assignments) in range
            members_result = self.supabase.table("aims_leg_members") \
                .select("crew_id, crew_name, position, flight_date, flight_number, departure") \
                .gte("flight_date", start_date.isoformat()) \
                .execute()
                
            if not members_result.data:
                return []
                
            # 3. Aggregate hours per crew
            crew_stats = {} # crew_id -> {hours, name, position}
            
            for m in members_result.data:
                cid = m["crew_id"]
                key = (m["flight_date"], m["flight_number"], m["departure"])
                mins = flight_mins_map.get(key, 0)
                
                if cid not in crew_stats:
                    crew_stats[cid] = {
                        "crew_id": cid,
                        "crew_name": m.get("crew_name", "Unknown"),
                        "position": m.get("position", ""),
                        "total_minutes": 0
                    }
                
                crew_stats[cid]["total_minutes"] += mins
                
            # 4. Filter, Sort and Format
            all_crew = []
            for cid, stats in crew_stats.items():
                hours = round(stats["total_minutes"] / 60.0, 2)
                
                # Determine alert level
                warning_level = "NORMAL"
                if hours >= threshold:
                    warning_level = "CRITICAL"
                elif hours >= threshold * 0.85: # Hardcoded 85% warning for now
                    warning_level = "WARNING"
                    
                all_crew.append({
                    "crew_id": cid,
                    "crew_name": stats["crew_name"],
                    "position": stats["position"],
                    "hours_28_day": hours,
                    "warning_level": warning_level
                })
                
            # Sort by hours descending
            sorted_crew = sorted(all_crew, key=lambda x: x["hours_28_day"], reverse=True)
            
            return sorted_crew[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get top crew stats: {e}")
            return []

    def get_roster_heatmap_data(self, days_range: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch roster data for top crew members for a heatmap view.
        """
        if not self.supabase:
            return []
            
        try:
            target_date = date.today()
            start_date = target_date - timedelta(days=days_range - 1)
            
            # 1. Get top 10 crew by flight hours (to have some data to show)
            crew_result = self.supabase.table("crew_flight_hours") \
                .select("crew_id") \
                .order("hours_28_day", desc=True) \
                .limit(10) \
                .execute()
            
            top_crew_ids = [row["crew_id"] for row in crew_result.data or []]
            if not top_crew_ids:
                return []
                
            # 2. Get roster for these crew members
            roster_result = self.supabase.table("fact_roster") \
                .select("crew_id, activity_type, start_dt, end_dt") \
                .in_("crew_id", top_crew_ids) \
                .gte("start_dt", start_date.isoformat()) \
                .lte("start_dt", target_date.isoformat()) \
                .execute()
            
            return roster_result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get roster heatmap data: {e}")
            return []


# =========================================================
# Test Function
# =========================================================

if __name__ == "__main__":
    # Test the data processor
    processor = DataProcessor()
    
    print("="*60)
    print("Data Processor Test")
    print("="*60)
    
    # Test FTL calculation
    print("\nFTL Warning Level Tests:")
    print(f"  0 hours: {calculate_warning_level(0, 0)}")
    print(f"  50 hours (28d): {calculate_warning_level(50, 500)}")
    print(f"  90 hours (28d): {calculate_warning_level(90, 800)}")
    print(f"  97 hours (28d): {calculate_warning_level(97, 950)}")
    
    print("\nHours Parsing Tests:")
    print(f"  '85:30' = {parse_hours_string('85:30')} hours")
    print(f"  '100:00' = {parse_hours_string('100:00')} hours")
    print(f"  '-' = {parse_hours_string('-')} hours")
    
    print("\nData Processor initialized successfully!")
