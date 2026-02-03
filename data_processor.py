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
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# =========================================================
# Configuration
# =========================================================

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
    target_date: date = None
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
    target_date = target_date or date.today()
    
    # Operations Window: 04:00 today to 03:59 tomorrow (local time)
    # This matches the aviation operational day definition
    # NOTE: Database stores STD in UTC, convert to LOCAL TIME of departure airport
    from airport_timezones import get_airport_timezone
    
    next_date = target_date + timedelta(days=1)
    prev_date = target_date - timedelta(days=1)
    target_date_str = target_date.isoformat()
    next_date_str = next_date.isoformat()
    prev_date_str = prev_date.isoformat()

    # Filter flights within the Operations Window (04:00-03:59 local time)
    ops_flights = []
    for flight in flight_data:
        std_str = flight.get("std", "")
        flight_date_str = flight.get("flight_date", target_date_str)
        dep_airport = flight.get("departure", "")
        carrier_code = flight.get("carrier_code", "")
        flight_number = flight.get("flight_number", "").strip()
        
        # 1. Handle NULL carrier_code
        # Allow NULL if flight number is '959' (VN959 FUK-HAN), otherwise skip
        if not carrier_code:
            if '959' not in flight_number:
                continue

        # 2. Exclude specific CANCELLED flights (based on User feedback & DB inconsistency)
        # These 5 flights from 02/02 UTC are marked 'Arrived' but confirmed Cancelled/Deleted
        cancelled_flights = {
            ('2026-02-02', '126', 'SGN'),
            ('2026-02-02', '1330', 'PQC'),
            ('2026-02-02', '176', 'SGN'),
            ('2026-02-02', '38', 'LHW'),
            ('2026-02-02', '871', 'TAE')
        }
        
        current_flight_key = (flight_date_str, flight_number, dep_airport)
        if current_flight_key in cancelled_flights:
            continue

        
        # Normalize flight_date
        if hasattr(flight_date_str, 'isoformat'):
            flight_date_str = flight_date_str.isoformat()
        
        if std_str and ":" in std_str:
            try:
                parts = std_str.split(":")
                utc_hour = int(parts[0])
                utc_min = int(parts[1]) if len(parts) > 1 else 0
                
                # Get timezone offset for departure airport
                tz_offset = get_airport_timezone(dep_airport)
                
                # Convert UTC to local time
                local_hour = utc_hour + int(tz_offset)
                local_min = utc_min + int((tz_offset - int(tz_offset)) * 60)
                
                # Handle minute overflow
                if local_min >= 60:
                    local_min -= 60
                    local_hour += 1
                
                local_date = flight_date_str
                
                # Handle day rollover (if local hour >= 24, it's next day)
                if local_hour >= 24:
                    local_hour -= 24
                    # The local date becomes next calendar day
                    if flight_date_str == prev_date_str:
                        local_date = target_date_str  # 02/02 UTC -> 03/02 local
                    elif flight_date_str == target_date_str:
                        local_date = next_date_str    # 03/02 UTC -> 04/02 local
                    elif flight_date_str == next_date_str:
                        # 04/02 UTC -> 05/02 local (NOT in 03/02 ops window!)
                        local_date = (target_date + timedelta(days=2)).isoformat()
                    else:
                        local_date = flight_date_str  # Unknown, keep as-is
                elif local_hour < 0:
                    local_hour += 24
                    # The local date becomes previous calendar day
                    if flight_date_str == target_date_str:
                        local_date = prev_date_str
                    elif flight_date_str == next_date_str:
                        local_date = target_date_str
                
                # Ops window: 04:00 local on target_date to 03:59 local on next_date
                # Include flight if:
                # 1. local_date == target_date AND local_hour >= 4 (04:00-23:59)
                # 2. local_date == next_date AND local_hour < 4 (00:00-03:59 next morning)
                
                if local_date == target_date_str and local_hour >= 4:
                    ops_flights.append(flight)
                elif local_date == next_date_str and local_hour < 4:
                    ops_flights.append(flight)
                    
            except (ValueError, IndexError):
                pass
    
    # Deduplicate flights by (local_date, flight_number, departure)
    # This prevents counting same flight twice when it appears in multiple UTC dates
    # but maps to the same local date
    seen_keys = set()
    unique_ops_flights = []
    for flight in ops_flights:
        flt_num = flight.get("flight_number", "")
        dep = flight.get("departure", "")
        # Recalculate local_date for dedup key
        std_str = flight.get("std", "")
        flight_date_str = flight.get("flight_date", "")
        if hasattr(flight_date_str, 'isoformat'):
            flight_date_str = flight_date_str.isoformat()
        
        local_date_key = flight_date_str  # Default
        if std_str and ":" in std_str:
            try:
                parts = std_str.split(":")
                utc_hour = int(parts[0])
                utc_min = int(parts[1]) if len(parts) > 1 else 0
                
                dep_airport = flight.get("departure", "")
                tz_offset = get_airport_timezone(dep_airport)
                
                # Same calculation as filter section
                local_hour = utc_hour + int(tz_offset)
                local_min = utc_min + int((tz_offset - int(tz_offset)) * 60)
                
                # Handle minute overflow (same as filter)
                if local_min >= 60:
                    local_min -= 60
                    local_hour += 1
                
                if local_hour >= 24:
                    if flight_date_str == prev_date_str:
                        local_date_key = target_date_str
                    elif flight_date_str == target_date_str:
                        local_date_key = next_date_str
                    elif flight_date_str == next_date_str:
                        # 04/02 UTC -> 05/02 local (not in 03/02 ops window)
                        local_date_key = (target_date + timedelta(days=2)).isoformat()
                    else:
                        local_date_key = flight_date_str
                elif local_hour < 0:
                    if flight_date_str == target_date_str:
                        local_date_key = prev_date_str
                    elif flight_date_str == next_date_str:
                        local_date_key = target_date_str
                    else:
                        local_date_key = flight_date_str
                else:
                    local_date_key = flight_date_str
            except:
                pass
        
        key = (local_date_key, flt_num, dep)
        if key not in seen_keys:
            seen_keys.add(key)
            unique_ops_flights.append(flight)
    
    ops_flights = unique_ops_flights
    
    # Total flights = unique flights within ops window (04:00 today - 03:59 tomorrow)
    total_flights = len(ops_flights)
    
    # Calculate Total Aircraft Operation (unique regs in Ops Window)
    unique_ops_aircraft = set()
    for flight in ops_flights:
        reg = flight.get("aircraft_reg")
        if reg:
            unique_ops_aircraft.add(reg)
    total_aircraft_operation = len(unique_ops_aircraft)

    # Recalculate block hours for Ops Window
    total_block_hours = 0.0
    for flight in ops_flights:
        off_block = flight.get("off_block")
        on_block = flight.get("on_block")
        
        # Calculate Block Hours: Priority Actual (ON-OFF) > Scheduled (STA-STD) > Default 2.0
        block_calculated = False
        
        if off_block and on_block:
            try:
                off_parts = off_block.split(":")
                on_parts = on_block.split(":")
                if len(off_parts) >= 2 and len(on_parts) >= 2:
                    off_minutes = int(off_parts[0]) * 60 + int(off_parts[1])
                    on_minutes = int(on_parts[0]) * 60 + int(on_parts[1])
                    if on_minutes < off_minutes:
                        on_minutes += 24 * 60
                    block_minutes = on_minutes - off_minutes
                    total_block_hours += block_minutes / 60.0
                    block_calculated = True
            except (ValueError, IndexError):
                pass

        if not block_calculated:
            # Fallback to STA - STD
            std = flight.get("std")
            sta = flight.get("sta")
            if std and sta and ":" in std and ":" in sta:
                try:
                    std_parts = std.split(":")
                    sta_parts = sta.split(":")
                    std_mins = int(std_parts[0]) * 60 + int(std_parts[1])
                    sta_mins = int(sta_parts[0]) * 60 + int(sta_parts[1])
                    
                    if sta_mins < std_mins:
                        sta_mins += 1440 # Overnight
                    
                    block_minutes = sta_mins - std_mins
                    total_block_hours += block_minutes / 60.0
                except:
                    total_block_hours += 2.0
            else:
                 total_block_hours += 2.0
    # Count crew by status
    crew_by_status = {
        "FLY": 0, "SBY": 0, "SL": 0, "CSL": 0, "OFF": 0, "TRN": 0, "LVE": 0, "OTHER": 0
    }
    
    # helper to clean duty codes
    def get_status_from_code(code):
        if not code: return "OTHER"
        c = code.upper().strip()
        if c in ["FLY", "FLT", "POS", "DHD"]: return "FLY"
        if c in ["SBY", "SB", "R"]: return "SBY"
        if c in ["OFF", "DO", "ADO", "X"]: return "OFF"
        if c in ["SL", "SICK"]: return "SL"
        if c in ["CSL"]: return "CSL"
        if c in ["AL", "LVE"]: return "LVE"
        if c in ["TRN", "SIM"]: return "TRN"
        return "OTHER"

    # 1. Aggegate from standby_data details first
    if standby_data:
        for crew in standby_data:
            s = crew.get("status", "OTHER")
            if s in crew_by_status: crew_by_status[s] += 1
            else: crew_by_status["OTHER"] += 1

    # 2. Iterate Crew Data
    if crew_data:
        # Reset to avoid double counting if we trust crew_data more
        crew_by_status = {k: 0 for k in crew_by_status} 

        for crew in crew_data:
            d_code = crew.get("duty_code", "")
            status = get_status_from_code(d_code)
            
            # Fallback
            if status == "OTHER" and crew.get("flight_number"):
                status = "FLY"
                
            if status in crew_by_status:
                crew_by_status[status] += 1
            else:
                crew_by_status["OTHER"] += 1

    logger.info(f"Crew Distribution Stats: {crew_by_status}")

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
        
        recalc_total_block += blk_val
            
        # Aggregate by AC Type
        ac_type = str(flight.get("aircraft_type", "Unknown")).strip()
        # Normalize: '321' -> 'A321'
        if ac_type.isdigit() and len(ac_type) == 3:
            ac_type = f"A{ac_type}"
            
        ac_type_hours[ac_type] = ac_type_hours.get(ac_type, 0.0) + blk_val
            
        # Completed & OTP
        ata_str = flight.get("ata")
        on_blk_str = flight.get("on_block")
        atd_str = flight.get("atd")
        flight_status = flight.get("status", "").upper().strip()
        
        is_completed = False
        completion_source = None
        
        # Calculate scheduled block time in minutes (from STD/STA)
        scheduled_block_mins = 0
        if std and sta:
            std_mins = parse_hm(std)
            sta_mins = parse_hm(sta)
            if std_mins is not None and sta_mins is not None:
                scheduled_block_mins = sta_mins - std_mins
                if scheduled_block_mins < 0:
                    scheduled_block_mins += 1440  # Overnight
        
        # Completed Logic (Fixed - Validate AIMS status with actual times):
        # AIMS sometimes returns STATUS=ARRIVED for flights that haven't departed yet
        # 1. ATA exists → Definitely completed (actual landing time recorded)
        # 2. STATUS = ARRIVED/LANDED AND ATD exists → Completed (has departed, AIMS says landed)
        # 3. ATD exists but no ATA → Check if current_time > ATD + scheduled_block + 1h buffer
        # 4. FALLBACK: No ATD/ATA → Check if current_time > STA + 30min buffer (flight should have landed)
        
        from datetime import datetime
        now = datetime.now()
        now_mins = now.hour * 60 + now.minute
        
        if ata_str:
            # Most reliable: actual landing time exists
            is_completed = True
            completion_source = "ATA"
        elif flight_status in ["ARRIVED", "LANDED"] and atd_str:
            # AIMS says arrived AND flight has departed
            is_completed = True
            completion_source = "STATUS+ATD"
        elif atd_str and not ata_str:
            # Missing ATA case - check if should be completed by now
            atd_mins = parse_hm(atd_str)
            if atd_mins is not None and scheduled_block_mins > 0:
                # Expected arrival = ATD + scheduled_block + 1h buffer
                expected_arrival_mins = atd_mins + scheduled_block_mins + 60
                if expected_arrival_mins >= 1440:
                    expected_arrival_mins -= 1440  # Wrap around
                
                # If current time > expected arrival, consider completed
                time_diff = now_mins - expected_arrival_mins
                if time_diff < -720:
                    time_diff += 1440
                elif time_diff > 720:
                    time_diff -= 1440
                
                if time_diff >= 0:
                    is_completed = True
                    completion_source = "ATD+Buffer"
        elif sta and not atd_str and not ata_str:
            # FALLBACK: No actual times available - use STA + 30min buffer
            # Flight considered completed if current time > STA + 30min
            sta_mins = parse_hm(sta)
            if sta_mins is not None:
                expected_completion = sta_mins + 30  # 30min buffer after scheduled arrival
                if expected_completion >= 1440:
                    expected_completion -= 1440
                
                time_diff = now_mins - expected_completion
                if time_diff < -720:
                    time_diff += 1440
                elif time_diff > 720:
                    time_diff -= 1440
                
                if time_diff >= 0:
                    is_completed = True
                    completion_source = "STA+Buffer"
        
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
        "total_crew": crew_by_status["FLY"],  # Only count crew currently flying
        "standby_available": crew_by_status["SBY"], # Legacy
        "total_aircraft_operation": total_aircraft_operation, 
        "sick_leave": crew_by_status["SL"] + crew_by_status["CSL"],
        "total_flights": total_flights,
        "total_completed_flights": completed_flights, # KPI 4
        "total_block_hours": round(total_block_hours, 1),
        "ac_type_breakdown": ac_breakdown_html, # KPI 3
        "aircraft_utilization": aircraft_utilization,
        "crew_by_status": crew_by_status,
        "flights_per_hour": flights_per_hour,
        "slots_by_base": slots_by_base,  # For departure slots chart
        "total_pax": total_pax,
        "otp_percentage": otp_percentage
    }


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
    
    def get_crew_hours(self, target_date: date = None) -> List[Dict[str, Any]]:
        """
        Get crew flight hours from database.
        
        Args:
            target_date: Date to filter by
            
        Returns:
            List of crew flight hour records
        """
        target_date = target_date or date.today()
        
        if self.supabase:
            try:
                result = self.supabase.table("crew_flight_hours") \
                    .select("*") \
                    .eq("calculation_date", target_date.isoformat()) \
                    .execute()
                return result.data or []
            except Exception as e:
                logger.error(f"Failed to fetch crew hours: {e}")
        
        return []
    
    def get_standby_records(self, target_date: date = None) -> List[Dict[str, Any]]:
        """
        Get standby records (SBY, SL, CSL) for a date.
        
        Args:
            target_date: Date to filter by
            
        Returns:
            List of standby records
        """
        target_date = target_date or date.today()
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
                    .in_("activity_type", ["SBY", "SL", "CSL", "SICK", "STANDBY"]) \
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
        target_date = target_date or date.today()
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
        
        return all_flights
    
    def get_dashboard_summary(self, target_date: date = None) -> Dict[str, Any]:
        """
        Get complete dashboard summary.
        
        Args:
            target_date: Date to calculate metrics for
            
        Returns:
            Dashboard summary with all KPIs
        """
        target_date = target_date or date.today()
        
        crew_hours = self.get_crew_hours(target_date)
        standby = self.get_standby_records(target_date)
        flights = self.get_flights(target_date)
        
        summary = calculate_dashboard_summary(
            crew_data=crew_hours,
            flight_data=flights,
            standby_data=standby,
            target_date=target_date
        )
        
        # Get operating crew count from leg_members
        # Only count unique crew assigned to operational flights
        operating_crew_count = self._get_operating_crew_count(flights, target_date)
        if operating_crew_count > 0:
            summary["total_crew"] = operating_crew_count
        
        summary["data_source"] = self.data_source
        
        return summary
    
    def get_aircraft_summary(self, target_date: date = None) -> Dict[str, Any]:
        """
        Get summary of all aircraft operating on target date.
        Returns list with flight count, block hours, utilization, etc.
        """
        target_date = target_date or date.today()
        flights = self.get_flights(target_date)
        
        # Prepare date ranges
        prev_date = target_date - timedelta(days=1)
        next_date = target_date + timedelta(days=1)
        target_date_str = target_date.isoformat()
        prev_date_str = prev_date.isoformat()
        next_date_str = next_date.isoformat()

        # Group flights by aircraft reg - WITH FILTERING
        aircraft_data = {}
        
        # Invalid regs to filter out (type codes used as reg in test data)
        INVALID_REGS = {'VN-A320', 'VN-A321', 'VN-A322'}
        
        # Blacklist for confirmed cancelled flights
        cancelled_flights = {
            ('2026-02-02', '126', 'SGN'),
            ('2026-02-02', '1330', 'PQC'),
            ('2026-02-02', '176', 'SGN'),
            ('2026-02-02', '38', 'LHW'),
            ('2026-02-02', '871', 'TAE')
        }

        # Deduplication set
        seen_keys = set()
        
        from airport_timezones import get_airport_timezone

        for flt in flights:
            # 1. Basic Filters
            reg = flt.get("aircraft_reg", "")
            if not reg or reg in INVALID_REGS:
                continue
                
            flight_number = flt.get("flight_number", "").strip()
            dep_airport = flt.get("departure", "")
            flight_date_str = flt.get("flight_date", target_date_str)
            if hasattr(flight_date_str, 'isoformat'):
                flight_date_str = flight_date_str.isoformat()
            
            # 2. Blacklist Check
            if (flight_date_str, flight_number, dep_airport) in cancelled_flights:
                continue
                
            # 3. Ops Window Filter (Local Time 04:00 - 03:59)
            std_str = flt.get("std", "")
            in_ops_window = False
            local_date_key = flight_date_str # For dedup
            
            if std_str and ":" in std_str:
                try:
                    parts = std_str.split(":")
                    utc_hour = int(parts[0])
                    utc_min = int(parts[1]) if len(parts) > 1 else 0
                    
                    tz_offset = get_airport_timezone(dep_airport)
                    
                    local_hour = utc_hour + int(tz_offset)
                    # Handle minute offset roughly if needed, usually just affects date rollover near boundary
                    local_min = utc_min + int((tz_offset - int(tz_offset)) * 60)
                    if local_min >= 60:
                        local_min -= 60
                        local_hour += 1
                    
                    local_date = flight_date_str
                    
                    # Handle day rollover
                    if local_hour >= 24:
                        local_hour -= 24
                        if flight_date_str == prev_date_str:
                            local_date = target_date_str
                        elif flight_date_str == target_date_str:
                            local_date = next_date_str
                        elif flight_date_str == next_date_str:
                             local_date = (target_date + timedelta(days=2)).isoformat()
                    elif local_hour < 0:
                        local_hour += 24
                        if flight_date_str == target_date_str:
                            local_date = prev_date_str
                        elif flight_date_str == next_date_str:
                            local_date = target_date_str
                            
                    # Ops Window Logic
                    if local_date == target_date_str and local_hour >= 4:
                        in_ops_window = True
                        local_date_key = target_date_str
                    elif local_date == next_date_str and local_hour < 4:
                        in_ops_window = True
                        local_date_key = next_date_str
                        
                except (ValueError, IndexError):
                    pass
            
            if not in_ops_window:
                continue
                
            # 4. Deduplication
            # Key: (local_date_of_flight, flight_number, departure)
            # We use local_date_key calculated above which maps to the date the flight *counts* for (mostly)
            # Actually, standard key is (Date, Flt, Dep). If flight counts for 03/02, key should probably reflect that or the unique flight ID.
            key = (local_date_key, flight_number, dep_airport)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            if reg not in aircraft_data:
                aircraft_data[reg] = {
                    "reg": reg,
                    "type": flt.get("aircraft_type", "Unknown"),
                    "flights": [],
                    "block_minutes": 0,
                    "first_std": None,
                    "last_sta": None,
                    "first_dep": None,
                    "last_arr": None,
                    "latest_dep_key": None, # (flight_date, std)
                    "last_std": None,
                    "last_flight_date": None
                }
            
            ac = aircraft_data[reg]
            ac["flights"].append(flt.get("flight_number", ""))
            
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
            
            ac["block_minutes"] += block_mins
        
        # Build result list
        now = datetime.now()
        now_mins = now.hour * 60 + now.minute
        total_aircraft = len(aircraft_data)
        
        # Calculate fleet-wide average: Total scheduled hours / Number of aircraft
        total_scheduled_mins = sum(ac["block_minutes"] for ac in aircraft_data.values())
        fleet_avg_mins = total_scheduled_mins / total_aircraft if total_aircraft > 0 else 1
        
        result = []
        
        for reg, ac in aircraft_data.items():
            block_hours = round(ac["block_minutes"] / 60, 1)
            
            # Utilization = This aircraft's block hours / Fleet average * 100
            # Shows how this aircraft compares to fleet average
            utilization = round((ac["block_minutes"] / fleet_avg_mins) * 100, 1) if fleet_avg_mins > 0 else 0
            
            # Determine status - GROUND only if ALL flights are completed
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
            
            # Convert First/Last times to Local Time
            first_flight_local = "-"
            if ac["first_std"] and ac["first_dep"]:
                try:
                    utc_parts = ac["first_std"].split(":")
                    utc_h = int(utc_parts[0])
                    utc_m = int(utc_parts[1]) if len(utc_parts)>1 else 0
                    tz = get_airport_timezone(ac["first_dep"])
                    loc_h = utc_h + int(tz)
                    loc_m = utc_m + int((tz - int(tz)) * 60)
                    if loc_m >= 60:
                        loc_m -= 60
                        loc_h += 1
                    if loc_h >= 24: loc_h -= 24
                    elif loc_h < 0: loc_h += 24
                    first_flight_local = f"{loc_h:02d}:{loc_m:02d}"
                except:
                    first_flight_local = ac["first_std"][:5]

            last_flight_local = "-"
            if ac["last_sta"] and ac["last_arr"] and ac["last_flight_date"] and ac["last_std"]:
                try:
                    # Determine UTC Arrival Datetime
                    # Base date = Flight Date (Departure Date)
                    flight_date_obj = datetime.strptime(ac["last_flight_date"], "%Y-%m-%d")
                    
                    std_parts = ac["last_std"].split(":")
                    sta_parts = ac["last_sta"].split(":")
                    
                    std_mins = int(std_parts[0]) * 60 + int(std_parts[1])
                    sta_mins = int(sta_parts[0]) * 60 + int(sta_parts[1])
                    
                    # If STA < STD, assume overnight (+1 day)
                    days_added = 0
                    if sta_mins < std_mins:
                        days_added = 1
                    
                    utc_arr_dt = flight_date_obj + timedelta(days=days_added)
                    utc_arr_dt = utc_arr_dt.replace(hour=int(sta_parts[0]), minute=int(sta_parts[1]))
                    
                    # Convert to Local
                    tz = get_airport_timezone(ac["last_arr"])
                    local_arr_dt = utc_arr_dt + timedelta(hours=int(tz)) + timedelta(minutes=(tz - int(tz)) * 60)
                    
                    # Format
                    last_flight_local = local_arr_dt.strftime("%H:%M")
                    
                    # Check if Next Day relative to Target Date
                    if local_arr_dt.date() > target_date:
                        last_flight_local += "+"
                        
                except Exception as e:
                    # Fallback
                    last_flight_local = ac["last_sta"][:5]

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
                    .select("crew_id, flight_date") \
                    .eq("flight_date", target_date.isoformat()) \
                    .execute()
                    
                for r in (result_today.data or []):
                    if r.get("crew_id"):
                        unique_crew.add(r.get("crew_id"))
                
                # Fetch next_date early morning crew (00:00-03:59)
                result_tomorrow = self.supabase.table("flight_crew") \
                    .select("crew_id, flight_date") \
                    .eq("flight_date", next_date.isoformat()) \
                    .execute()
                
                # Note: We add all because scheduler already filters for early flights
                for r in (result_tomorrow.data or []):
                    if r.get("crew_id"):
                        unique_crew.add(r.get("crew_id"))
                
                if unique_crew:
                    logger.info(f"Operating crew count from flight_crew: {len(unique_crew)}")
                    return len(unique_crew)
                    
            except Exception as e:
                logger.debug(f"flight_crew table not available: {e}")
        
        # Fallback: Estimate based on flight count
        # Average crew per flight: 4 (2 pilots + 2 cabin crew for narrow-body)
        # But crew can fly multiple legs, so estimate unique crew = flights * 0.8
        estimated = int(len(flights) * 0.8)
        
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
        target_date = target_date or date.today()
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
