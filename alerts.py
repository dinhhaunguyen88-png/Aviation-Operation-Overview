"""
Alert System Module
Phase 4: Advanced Features

Handles FTL alerts, notifications, and alert history.
"""

import os
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# =====================================================
# Alert Types & Severity
# =====================================================

class AlertType(Enum):
    FTL_WARNING = "FTL_WARNING"
    FTL_CRITICAL = "FTL_CRITICAL"
    SICK_LEAVE = "SICK_LEAVE"
    CALL_SICK = "CALL_SICK"
    STANDBY_LOW = "STANDBY_LOW"
    FLIGHT_DELAY = "FLIGHT_DELAY"
    CREW_SHORTAGE = "CREW_SHORTAGE"
    SYSTEM = "SYSTEM"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# FTL Thresholds
FTL_28DAY_LIMIT = int(os.getenv("FTL_28DAY_LIMIT", 100))
FTL_12MONTH_LIMIT = int(os.getenv("FTL_12MONTH_LIMIT", 1000))
FTL_WARNING_THRESHOLD = int(os.getenv("FTL_WARNING_THRESHOLD", 85))
FTL_CRITICAL_THRESHOLD = int(os.getenv("FTL_CRITICAL_THRESHOLD", 95))
STANDBY_MIN_THRESHOLD = int(os.getenv("STANDBY_MIN_THRESHOLD", 5))


# =====================================================
# Alert Data Class
# =====================================================

class Alert:
    """
    Represents an alert in the system.
    """
    
    def __init__(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        data: Dict[str, Any] = None,
        crew_id: str = None,
        flight_id: str = None,
        created_at: datetime = None
    ):
        self.id = None  # Set by database
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.message = message
        self.data = data or {}
        self.crew_id = crew_id
        self.flight_id = flight_id
        self.created_at = created_at or datetime.now()
        self.acknowledged = False
        self.acknowledged_at = None
        self.acknowledged_by = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/database."""
        return {
            "id": self.id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "crew_id": self.crew_id,
            "flight_id": self.flight_id,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """Create Alert from dictionary."""
        alert = cls(
            alert_type=AlertType(data["alert_type"]),
            severity=AlertSeverity(data["severity"]),
            title=data["title"],
            message=data["message"],
            data=data.get("data", {}),
            crew_id=data.get("crew_id"),
            flight_id=data.get("flight_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )
        alert.id = data.get("id")
        alert.acknowledged = data.get("acknowledged", False)
        return alert


# =====================================================
# Alert Service
# =====================================================

class AlertService:
    """
    Service for managing alerts.
    """
    
    def __init__(self):
        self._supabase = None
        self._active_alerts: List[Alert] = []
    
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
    
    def create_alert(self, alert: Alert) -> Optional[str]:
        """
        Create a new alert.
        
        Args:
            alert: Alert object to create
            
        Returns:
            Alert ID if successful
        """
        # Try database first
        if self.supabase:
            try:
                result = self.supabase.table("alerts").insert(alert.to_dict()).execute()
                if result.data:
                    alert.id = result.data[0].get("id")
                    return alert.id
            except Exception as e:
                logger.warning(f"Database insert failed, using memory storage: {e}")
        
        # Fallback to memory storage
        alert.id = f"mem_{len(self._active_alerts) + 1}"
        self._active_alerts.append(alert)
        return alert.id
    
    def get_active_alerts(
        self,
        severity: AlertSeverity = None,
        alert_type: AlertType = None,
        limit: int = 50
    ) -> List[Alert]:
        """
        Get active (unacknowledged) alerts.
        
        Args:
            severity: Filter by severity
            alert_type: Filter by type
            limit: Max number to return
            
        Returns:
            List of Alert objects
        """
        # Try database first
        if self.supabase:
            try:
                query = self.supabase.table("alerts") \
                    .select("*") \
                    .eq("acknowledged", False) \
                    .order("created_at", desc=True) \
                    .limit(limit)
                
                if severity:
                    query = query.eq("severity", severity.value)
                if alert_type:
                    query = query.eq("alert_type", alert_type.value)
                
                result = query.execute()
                return [Alert.from_dict(a) for a in (result.data or [])]
            except Exception as e:
                logger.warning(f"Database query failed, using memory storage: {e}")
        
        # Fallback: return from memory
        alerts = [a for a in self._active_alerts if not a.acknowledged]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: ID of alert to acknowledge
            user: User who acknowledged
            
        Returns:
            True if successful
        """
        try:
            if self.supabase:
                self.supabase.table("alerts").update({
                    "acknowledged": True,
                    "acknowledged_at": datetime.now().isoformat(),
                    "acknowledged_by": user
                }).eq("id", alert_id).execute()
                return True
            
            # Fallback: update in memory
            for alert in self._active_alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_at = datetime.now()
                    alert.acknowledged_by = user
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    def get_alert_history(
        self,
        from_date: date = None,
        to_date: date = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Get alert history.
        
        Args:
            from_date: Start date
            to_date: End date
            limit: Max records
            
        Returns:
            List of historical alerts
        """
        try:
            if self.supabase:
                query = self.supabase.table("alerts") \
                    .select("*") \
                    .order("created_at", desc=True) \
                    .limit(limit)
                
                if from_date:
                    query = query.gte("created_at", from_date.isoformat())
                if to_date:
                    query = query.lte("created_at", to_date.isoformat())
                
                result = query.execute()
                return [Alert.from_dict(a) for a in (result.data or [])]
            
            return self._active_alerts[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get alert history: {e}")
            return []


# =====================================================
# Alert Generators
# =====================================================

def generate_ftl_alerts(crew_hours: List[Dict[str, Any]]) -> List[Alert]:
    """
    Generate FTL alerts from crew data.
    
    Args:
        crew_hours: List of crew flight hour records
        
    Returns:
        List of Alert objects
    """
    alerts = []
    
    for crew in crew_hours:
        hours_28d = crew.get("hours_28_day", 0)
        hours_12m = crew.get("hours_12_month", 0)
        
        # Calculate percentages
        pct_28d = (hours_28d / FTL_28DAY_LIMIT) * 100 if FTL_28DAY_LIMIT > 0 else 0
        pct_12m = (hours_12m / FTL_12MONTH_LIMIT) * 100 if FTL_12MONTH_LIMIT > 0 else 0
        
        max_pct = max(pct_28d, pct_12m)
        
        if max_pct >= FTL_CRITICAL_THRESHOLD:
            alerts.append(Alert(
                alert_type=AlertType.FTL_CRITICAL,
                severity=AlertSeverity.CRITICAL,
                title=f"Critical FTL: {crew.get('crew_name', crew.get('crew_id'))}",
                message=f"Flight hours at {max_pct:.1f}% of limit. 28d: {hours_28d}h, 12m: {hours_12m}h",
                data={
                    "hours_28_day": hours_28d,
                    "hours_12_month": hours_12m,
                    "percentage": max_pct
                },
                crew_id=crew.get("crew_id")
            ))
        elif max_pct >= FTL_WARNING_THRESHOLD:
            alerts.append(Alert(
                alert_type=AlertType.FTL_WARNING,
                severity=AlertSeverity.WARNING,
                title=f"FTL Warning: {crew.get('crew_name', crew.get('crew_id'))}",
                message=f"Flight hours at {max_pct:.1f}% of limit",
                data={
                    "hours_28_day": hours_28d,
                    "hours_12_month": hours_12m,
                    "percentage": max_pct
                },
                crew_id=crew.get("crew_id")
            ))
    
    return alerts


def generate_standby_alerts(standby_count: int, required_min: int = None) -> List[Alert]:
    """
    Generate standby availability alerts.
    
    Args:
        standby_count: Number of standby crew
        required_min: Minimum required (uses env default if not set)
        
    Returns:
        List of Alert objects
    """
    required_min = required_min or STANDBY_MIN_THRESHOLD
    alerts = []
    
    if standby_count < required_min:
        severity = AlertSeverity.CRITICAL if standby_count == 0 else AlertSeverity.WARNING
        
        alerts.append(Alert(
            alert_type=AlertType.STANDBY_LOW,
            severity=severity,
            title="Low Standby Availability",
            message=f"Only {standby_count} crew on standby (minimum: {required_min})",
            data={
                "standby_count": standby_count,
                "required_min": required_min
            }
        ))
    
    return alerts


def generate_sick_leave_alerts(sick_records: List[Dict[str, Any]]) -> List[Alert]:
    """
    Generate alerts for sick leave.
    
    Args:
        sick_records: List of sick leave records
        
    Returns:
        List of Alert objects
    """
    alerts = []
    
    for record in sick_records:
        status = record.get("status", "")
        
        if status == "CSL":  # Call sick
            alerts.append(Alert(
                alert_type=AlertType.CALL_SICK,
                severity=AlertSeverity.WARNING,
                title=f"Call Sick: {record.get('crew_name', record.get('crew_id'))}",
                message=f"Crew called in sick",
                data={"duty_date": record.get("duty_start_date")},
                crew_id=record.get("crew_id")
            ))
        elif status == "SL":  # Sick leave
            alerts.append(Alert(
                alert_type=AlertType.SICK_LEAVE,
                severity=AlertSeverity.INFO,
                title=f"Sick Leave: {record.get('crew_name', record.get('crew_id'))}",
                message=f"Crew on sick leave",
                data={
                    "start_date": record.get("duty_start_date"),
                    "end_date": record.get("duty_end_date")
                },
                crew_id=record.get("crew_id")
            ))
    
    return alerts


# =====================================================
# Alert Manager
# =====================================================

class AlertManager:
    """
    Manager class for running alert checks.
    """
    
    def __init__(self):
        self.service = AlertService()
    
    def run_all_checks(self, crew_hours: List[Dict], standby: List[Dict]) -> List[Alert]:
        """
        Run all alert checks and create new alerts.
        
        Args:
            crew_hours: Crew flight hour data
            standby: Standby records
            
        Returns:
            List of new alerts created
        """
        all_alerts = []
        
        # FTL alerts
        ftl_alerts = generate_ftl_alerts(crew_hours)
        all_alerts.extend(ftl_alerts)
        
        # Standby alerts
        sby_count = len([s for s in standby if s.get("status") == "SBY"])
        standby_alerts = generate_standby_alerts(sby_count)
        all_alerts.extend(standby_alerts)
        
        # Sick leave alerts
        sick_records = [s for s in standby if s.get("status") in ["SL", "CSL"]]
        sick_alerts = generate_sick_leave_alerts(sick_records)
        all_alerts.extend(sick_alerts)
        
        # Create alerts in database
        for alert in all_alerts:
            self.service.create_alert(alert)
        
        logger.info(f"Generated {len(all_alerts)} alerts")
        return all_alerts
    
    def get_summary(self) -> Dict[str, Any]:
        """Get alert summary."""
        active = self.service.get_active_alerts()
        
        by_severity = {
            "critical": 0,
            "warning": 0,
            "info": 0
        }
        
        for alert in active:
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
        
        return {
            "total_active": len(active),
            "by_severity": by_severity,
            "latest": [a.to_dict() for a in active[:5]]
        }


# Singleton
alert_manager = AlertManager()


# =====================================================
# Test
# =====================================================

if __name__ == "__main__":
    print("="*60)
    print("Alert System Test")
    print("="*60)
    
    # Test FTL alerts
    test_crew = [
        {"crew_id": "001", "crew_name": "John Doe", "hours_28_day": 95, "hours_12_month": 900},
        {"crew_id": "002", "crew_name": "Jane Smith", "hours_28_day": 88, "hours_12_month": 850},
        {"crew_id": "003", "crew_name": "Bob Wilson", "hours_28_day": 50, "hours_12_month": 500},
    ]
    
    ftl_alerts = generate_ftl_alerts(test_crew)
    print(f"\nFTL Alerts: {len(ftl_alerts)}")
    for a in ftl_alerts:
        print(f"  - [{a.severity.value}] {a.title}")
    
    # Test standby alerts
    standby_alerts = generate_standby_alerts(2)
    print(f"\nStandby Alerts: {len(standby_alerts)}")
    for a in standby_alerts:
        print(f"  - [{a.severity.value}] {a.title}")
    
    print("\nAlert System initialized successfully!")
