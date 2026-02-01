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
    
    # Define Operations Window: 04:00 today to 03:59 tomorrow
    start_dt = datetime.combine(target_date, datetime.min.time()).replace(hour=4, minute=0, second=0)
    end_dt = start_dt + timedelta(hours=24) - timedelta(seconds=1)

    # Filter flights within the Operations Window
    ops_flights = []
    for flight in flight_data:
        std_str = flight.get("std", "")
        if std_str and ":" in std_str:
            try:
                parts = std_str.split(":")
                f_hour = int(parts[0])
                
                # Simplified check for just "HH:MM" assuming it belongs to target_date:
                # In a real scenario with cross-day data, we'd check timestamps.
                # Here we assume data is for target_date. 
                # Flights 00:00-03:59 belong to PREVIOUS Ops Day.
                # Flights 04:00-23:59 belong to CURRENT Ops Day.
                # Wait, if we are loading data for Feb 1st, and we see 02:00, it is Feb 1st 02:00.
                # Does Feb 1st 02:00 belong to Feb 1st Ops Day (Starts Feb 1st 04:00)? NO.
                # It belongs to Jan 31st Ops Day.
                
                # So for target_date Feb 1st, we want:
                # - Feb 1st 04:00 -> 23:59
                # - Feb 2nd 00:00 -> 03:59
                
                # If flight_data ONLY contains Feb 1st flights:
                # We Keep 04:00 -> 23:59.
                # We exclude 00:00 -> 03:59.
                
                if 4 <= f_hour <= 23:
                     ops_flights.append(flight)
                     
                # Note: We are missing T+1 00:00-03:59 data if not provided in flight_data.
                
            except (ValueError, IndexError):
                pass
    
    # Overwrite total_flights with Operational count
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
            except (ValueError, IndexError):
                total_block_hours += 2.0
        else:
            total_block_hours += 2.0
    
    # Count crew by status
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
        # Format usually HH:MM:SS or HH:MM
        if std:
            try:
                parts = std.split(":")
                if len(parts) >= 2:
                    h = int(parts[0])
                    if 0 <= h < 24:
                        flights_per_hour[h] += 1
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
        
        is_completed = False
        completion_source = None
        
        if ata_str:
            is_completed = True
            completion_source = "ATA"
        elif on_blk_str:
            # Fallback completion (Gate Arrival)
            is_completed = True
            completion_source = "ONBLOCK"
            
        atd_str = flight.get("atd") 
        
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
        "total_crew": len(crew_data),
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
        "alerts": alerts,
        "alerts_count": len(alerts),
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
        Get flights for a date.
        
        Args:
            target_date: Date to filter by
            
        Returns:
            List of flight records
        """
        target_date = target_date or date.today()
        
        if self.supabase:
            try:
                result = self.supabase.table("flights") \
                    .select("*") \
                    .eq("flight_date", target_date.isoformat()) \
                    .execute()
                return result.data or []
            except Exception as e:
                logger.error(f"Failed to fetch flights: {e}")
        
        return []
    
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
        
        # Override total_crew with actual count from crew_members table
        if self.supabase:
            try:
                result = self.supabase.table("crew_members").select("crew_id", count="exact").execute()
                summary["total_crew"] = result.count if result.count else len(result.data or [])
            except Exception as e:
                logger.warning(f"Failed to fetch crew count: {e}")
        
        summary["data_source"] = self.data_source
        
        return summary

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
