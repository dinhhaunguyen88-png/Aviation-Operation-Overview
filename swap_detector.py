"""
Aircraft Swap Detector Module
Detects aircraft registration changes by comparing current flight data
against first-seen snapshots. Integrates with AIMS modification logs
for reason classification.
"""

import os
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# =========================================================
# Swap Reason Classification
# =========================================================

SWAP_CATEGORIES = {
    "MAINTENANCE": [
        "MEL", "AOG", "MAINT", "TECH", "DEFECT", "ENGINE", "REPAIR",
        "INSPECTION", "HYDRAULIC", "AVIONICS", "CABIN", "SEAL",
        "UNSERVICEABLE", "U/S", "GROUNDED", "MECHANICAL"
    ],
    "WEATHER": [
        "WX", "WEATHER", "WIND", "FOG", "STORM", "TYPHOON",
        "VISIBILITY", "TURBULENCE", "LIGHTNING", "SNOW", "ICE"
    ],
    "CREW": [
        "CREW", "SICK", "FTL", "PILOT", "FA", "DUTY", "REST",
        "QUALIFICATION", "TRAINING", "ABSENCE"
    ],
    "OPERATIONAL": [
        "DELAY", "SCHEDULE", "ROUTE", "OPS", "ROTATION", "COMMERCIAL",
        "PAX", "LOAD", "CAPACITY", "CHARTER", "SLOT"
    ],
}

# Severity thresholds for tail number impact
SEVERITY_THRESHOLDS = {
    "CRITICAL": 10,
    "HIGH": 5,
    "NORMAL": 0
}


def classify_swap_reason(status_desc: str, log_description: str = None) -> Tuple[str, str]:
    """
    Classify swap reason from AIMS modification log description.
    
    Args:
        status_desc: Status description from mod log
        log_description: Additional log description
        
    Returns:
        Tuple of (category, reason_detail)
    """
    if not status_desc and not log_description:
        return "UNKNOWN", "No reason provided"
    
    combined = f"{status_desc or ''} {log_description or ''}".upper()
    
    for category, keywords in SWAP_CATEGORIES.items():
        for keyword in keywords:
            if keyword in combined:
                # Extract a more detailed reason
                detail = _extract_reason_detail(combined, category)
                return category, detail
    
    return "UNKNOWN", status_desc or log_description or "Unclassified"


def _extract_reason_detail(text: str, category: str) -> str:
    """Extract human-readable reason detail from mod log text."""
    text_lower = text.lower().strip()
    
    # Truncate to reasonable length
    if len(text_lower) > 100:
        text_lower = text_lower[:100] + "..."
    
    # Clean up and capitalize
    if text_lower:
        return text_lower.capitalize()
    return category.capitalize()


def detect_swaps(
    current_flights: List[Dict[str, Any]],
    snapshots: Dict[str, Dict[str, Any]],
    mod_logs: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Detect aircraft swaps by comparing current flights against snapshots.
    
    Args:
        current_flights: List of current flight records with aircraft_reg
        snapshots: Dict of {flight_key: snapshot_record} for baseline comparison
        mod_logs: Optional list of modification log entries for reason context
        
    Returns:
        List of detected swap events
    """
    swaps = []
    mod_log_index = _build_mod_log_index(mod_logs) if mod_logs else {}
    
    for flight in current_flights:
        flight_num = str(flight.get("flight_number", "")).strip()
        flight_dt = flight.get("flight_date", "")
        departure = str(flight.get("departure", "")).strip()
        current_reg = str(flight.get("aircraft_reg", "")).strip()
        
        if not flight_num or not current_reg or not departure:
            continue
        
        # Build key for snapshot lookup
        flight_key = f"{flight_dt}|{flight_num}|{departure}"
        
        # Check against snapshot
        snapshot = snapshots.get(flight_key)
        if not snapshot:
            continue  # No baseline = first sync, can't detect swap
        
        original_reg = str(snapshot.get("first_seen_reg", "")).strip()
        
        # Skip if same registration (no swap)
        if not original_reg or current_reg == original_reg:
            continue
        
        # SWAP DETECTED!
        logger.info(
            f"Swap detected: {flight_num} on {flight_dt} "
            f"({original_reg} → {current_reg})"
        )
        
        # Try to find reason from mod logs
        reason_key = f"{flight_dt}|{flight_num}"
        mod_entry = mod_log_index.get(reason_key, {})
        
        swap_category, swap_reason = classify_swap_reason(
            mod_entry.get("status_desc", ""),
            mod_entry.get("log_description", "")
        )
        
        # Calculate delay impact
        delay_minutes = _calculate_delay(flight, snapshot)
        
        # Determine recovery status
        recovery_status = _determine_recovery(flight, delay_minutes)
        
        swaps.append({
            "flight_date": flight_dt,
            "flight_number": flight_num,
            "departure": departure,
            "arrival": flight.get("arrival", ""),
            "original_reg": original_reg,
            "swapped_reg": current_reg,
            "original_ac_type": snapshot.get("first_seen_ac_type", ""),
            "swapped_ac_type": flight.get("aircraft_type", ""),
            "swap_reason": swap_reason,
            "swap_category": swap_category,
            "delay_minutes": delay_minutes,
            "recovery_status": recovery_status,
            "mod_log_ref": mod_entry.get("status_desc", ""),
        })
    
    logger.info(f"Detected {len(swaps)} swap events")
    return swaps


def _build_mod_log_index(mod_logs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Build index of modification logs by flight key for quick lookup.
    Prioritize entries that mention aircraft/registration changes.
    """
    index = {}
    
    if not mod_logs:
        return index
    
    for log in mod_logs:
        flight_num = str(log.get("flight_number", "")).strip()
        flight_dt = str(log.get("flight_date", "")).strip()
        
        if not flight_num:
            continue
        
        key = f"{flight_dt}|{flight_num}"
        status = str(log.get("status_desc", "")).upper()
        
        # Prioritize entries mentioning aircraft changes
        existing = index.get(key)
        if not existing or _is_aircraft_change(status):
            index[key] = log
    
    return index


def _is_aircraft_change(status_desc: str) -> bool:
    """Check if modification log entry relates to aircraft change."""
    if not status_desc:
        return False
    upper = status_desc.upper()
    return any(kw in upper for kw in [
        "AIRCRAFT", "REG", "SWAP", "EQUIPMENT", "A/C", "AC TYPE",
        "TAIL", "CHANGE", "REPLACE"
    ])


def _calculate_delay(flight: Dict, snapshot: Dict) -> int:
    """
    Calculate delay in minutes caused by the swap.
    Compare actual departure vs scheduled departure.
    """
    try:
        std = flight.get("std", "")
        atd = flight.get("atd", "") or flight.get("etd", "")
        
        if not std or not atd:
            return 0
        
        # Parse HH:MM format
        std_parts = str(std).split(":")
        atd_parts = str(atd).split(":")
        
        if len(std_parts) >= 2 and len(atd_parts) >= 2:
            std_mins = int(std_parts[0]) * 60 + int(std_parts[1])
            atd_mins = int(atd_parts[0]) * 60 + int(atd_parts[1])
            delay = atd_mins - std_mins
            
            # Handle day wraparound
            if delay < -720:  # More than 12h negative = next day
                delay += 1440
            
            return max(0, delay)
    except (ValueError, IndexError):
        pass
    
    return 0


def _determine_recovery(flight: Dict, delay_minutes: int) -> str:
    """
    Determine recovery status after swap.
    
    Returns:
        RECOVERED - Flight departed on time or with minimal delay
        DELAYED - Flight was delayed
        PENDING - Flight hasn't departed yet
        CANCELLED - Flight was cancelled
    """
    status = str(flight.get("flight_status", "")).upper()
    
    if "CANCEL" in status:
        return "CANCELLED"
    
    if "ARRIVED" in status or "ARR" in status:
        if delay_minutes <= 15:
            return "RECOVERED"
        else:
            return "DELAYED"
    
    atd = flight.get("atd", "")
    if atd:
        if delay_minutes <= 15:
            return "RECOVERED"
        else:
            return "DELAYED"
    
    return "PENDING"


def generate_swap_event_id(existing_count: int) -> str:
    """Generate sequential swap event ID (e.g., SW-0024)."""
    return f"SW-{existing_count + 1:04d}"


def calculate_swap_kpis(
    swaps: List[Dict[str, Any]],
    total_flights: int = 0,
    previous_period_swaps: int = 0
) -> Dict[str, Any]:
    """
    Calculate KPI metrics for the swap dashboard.
    
    Args:
        swaps: List of swap records
        total_flights: Total flights in the period (for rate calculation)
        previous_period_swaps: Swap count from previous period (for trend)
        
    Returns:
        Dict with KPI values
    """
    total_swaps = len(swaps)
    
    if total_swaps == 0:
        return {
            "total_swaps": 0,
            "impacted_flights": 0,
            "avg_swap_time_hours": 0,
            "recovery_rate": 100.0,
            "swap_rate": 0,
            "trend_vs_last_period": 0,
        }
    
    # Count unique impacted flights
    impacted_flights = len(set(
        f"{s['flight_date']}|{s['flight_number']}" for s in swaps
    ))
    
    # Average delay (swap time)
    delays = [s.get("delay_minutes", 0) for s in swaps if s.get("delay_minutes", 0) > 0]
    avg_delay_minutes = sum(delays) / len(delays) if delays else 0
    avg_swap_time_hours = round(avg_delay_minutes / 60, 1)
    
    # Recovery rate
    recovered = sum(1 for s in swaps if s.get("recovery_status") == "RECOVERED")
    completed = sum(1 for s in swaps if s.get("recovery_status") in ("RECOVERED", "DELAYED"))
    recovery_rate = round((recovered / completed * 100), 1) if completed > 0 else 0
    
    # Swap rate (% of total flights)
    swap_rate = round((total_swaps / total_flights * 100), 1) if total_flights > 0 else 0
    
    # Trend vs last period
    if previous_period_swaps > 0:
        trend = round(((total_swaps - previous_period_swaps) / previous_period_swaps * 100), 1)
    else:
        trend = 0
    
    return {
        "total_swaps": total_swaps,
        "impacted_flights": impacted_flights,
        "avg_swap_time_hours": avg_swap_time_hours,
        "recovery_rate": recovery_rate,
        "swap_rate": swap_rate,
        "trend_vs_last_period": trend,
    }


def get_reason_breakdown(swaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate swap reasons breakdown by category.
    
    Returns:
        List of {category, count, percentage} sorted by count desc
    """
    if not swaps:
        return []
    
    category_counts = {}
    for swap in swaps:
        cat = swap.get("swap_category", "UNKNOWN")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    total = len(swaps)
    breakdown = []
    for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        breakdown.append({
            "category": category.capitalize(),
            "count": count,
            "percentage": round(count / total * 100, 1)
        })
    
    return breakdown


def get_top_impacted_tails(
    swaps: List[Dict[str, Any]],
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get top impacted tail numbers (aircraft registrations).
    
    Returns:
        List of {reg, ac_type, swap_count, severity}
    """
    if not swaps:
        return []
    
    tail_counts = {}
    tail_types = {}
    
    for swap in swaps:
        # Count both original and swapped registrations
        for reg_field in ["original_reg", "swapped_reg"]:
            reg = swap.get(reg_field, "")
            if reg:
                tail_counts[reg] = tail_counts.get(reg, 0) + 1
                if reg not in tail_types:
                    ac_type = swap.get(
                        "original_ac_type" if reg_field == "original_reg" else "swapped_ac_type",
                        ""
                    )
                    tail_types[reg] = ac_type
    
    # Sort by count descending
    sorted_tails = sorted(tail_counts.items(), key=lambda x: -x[1])[:limit]
    
    result = []
    for reg, count in sorted_tails:
        severity = "NORMAL"
        if count >= SEVERITY_THRESHOLDS["CRITICAL"]:
            severity = "CRITICAL"
        elif count >= SEVERITY_THRESHOLDS["HIGH"]:
            severity = "HIGH"
        
        result.append({
            "reg": reg,
            "ac_type": tail_types.get(reg, ""),
            "swap_count": count,
            "severity": severity,
        })
    
    return result
