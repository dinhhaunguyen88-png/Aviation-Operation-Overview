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
    
    # Count crew by status
    crew_by_status = {
        "FLY": 0,
        "SBY": 0,
        "SL": 0,
        "CSL": 0,
        "OFF": 0,
        "TRN": 0,
        "LVE": 0,
        "OTHER": 0
    }
    
    for crew in standby_data:
        status = crew.get("status", "OTHER")
        if status in crew_by_status:
            crew_by_status[status] += 1
        else:
            crew_by_status["OTHER"] += 1
    
    # Calculate flight metrics
    total_flights = len(flight_data)
    
    # Count unique aircraft
    unique_aircraft = set()
    for flight in flight_data:
        if flight.get("aircraft_reg"):
            unique_aircraft.add(flight["aircraft_reg"])
    
    total_aircraft = len(unique_aircraft)
    
    # Calculate block hours (simplified - would need actual times)
    total_block_hours = 0.0
    for flight in flight_data:
        # Estimate 2 hours per flight if no actual times
        total_block_hours += 2.0
    
    # Calculate aircraft utilization
    aircraft_utilization = 0.0
    if total_aircraft > 0:
        aircraft_utilization = round(total_block_hours / total_aircraft, 1)
    
    # FTL alerts
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
        "date": target_date.isoformat(),
        "total_crew": len(crew_data),
        "crew_by_status": crew_by_status,
        "total_flights": total_flights,
        "total_aircraft": total_aircraft,
        "aircraft_utilization": aircraft_utilization,
        "total_block_hours": round(total_block_hours, 1),
        "alerts_count": len(alerts),
        "alerts": alerts[:10],  # Top 10 alerts
        "standby_available": crew_by_status["SBY"],
        "sick_leave": crew_by_status["SL"] + crew_by_status["CSL"],
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
    return {
        "crew_id": str(aims_crew.get("crew_id", "")),
        "crew_name": aims_crew.get("crew_name", ""),
        "first_name": aims_crew.get("first_name", ""),
        "last_name": aims_crew.get("last_name", ""),
        "three_letter_code": aims_crew.get("three_letter_code", ""),
        "gender": aims_crew.get("gender", ""),
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
        
        if self.supabase:
            try:
                result = self.supabase.table("standby_records") \
                    .select("*") \
                    .lte("duty_start_date", target_date.isoformat()) \
                    .gte("duty_end_date", target_date.isoformat()) \
                    .execute()
                return result.data or []
            except Exception as e:
                logger.error(f"Failed to fetch standby records: {e}")
        
        return []
    
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
        
        summary["data_source"] = self.data_source
        
        return summary


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
