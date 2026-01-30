"""
Unit Tests - Alert System
Phase 5: Testing & Deployment

Tests for alert generation and management.
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch

from alerts import (
    Alert,
    AlertType,
    AlertSeverity,
    AlertService,
    AlertManager,
    generate_ftl_alerts,
    generate_standby_alerts,
    generate_sick_leave_alerts
)


class TestAlertClass:
    """Tests for Alert class."""
    
    def test_create_alert(self):
        """Test creating an alert."""
        alert = Alert(
            alert_type=AlertType.FTL_WARNING,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test",
            crew_id="12345"
        )
        
        assert alert.alert_type == AlertType.FTL_WARNING
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.crew_id == "12345"
        assert alert.acknowledged is False
    
    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = Alert(
            alert_type=AlertType.FTL_CRITICAL,
            severity=AlertSeverity.CRITICAL,
            title="Critical Alert",
            message="Critical message"
        )
        
        result = alert.to_dict()
        
        assert result["alert_type"] == "FTL_CRITICAL"
        assert result["severity"] == "critical"
        assert result["title"] == "Critical Alert"
    
    def test_alert_from_dict(self):
        """Test creating alert from dictionary."""
        data = {
            "alert_type": "FTL_WARNING",
            "severity": "warning",
            "title": "Test",
            "message": "Message",
            "created_at": "2026-01-30T10:00:00"
        }
        
        alert = Alert.from_dict(data)
        
        assert alert.alert_type == AlertType.FTL_WARNING
        assert alert.severity == AlertSeverity.WARNING


class TestGenerateFTLAlerts:
    """Tests for FTL alert generation."""
    
    def test_no_alerts_for_normal(self):
        """Test no alerts for normal hours."""
        crew_data = [
            {"crew_id": "1", "crew_name": "Test", "hours_28_day": 50, "hours_12_month": 500}
        ]
        
        alerts = generate_ftl_alerts(crew_data)
        assert len(alerts) == 0
    
    def test_warning_alert(self):
        """Test warning alert generation."""
        crew_data = [
            {"crew_id": "1", "crew_name": "Test Pilot", "hours_28_day": 90, "hours_12_month": 800}
        ]
        
        alerts = generate_ftl_alerts(crew_data)
        
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.FTL_WARNING
        assert alerts[0].severity == AlertSeverity.WARNING
    
    def test_critical_alert(self):
        """Test critical alert generation."""
        crew_data = [
            {"crew_id": "1", "crew_name": "Test Pilot", "hours_28_day": 98, "hours_12_month": 900}
        ]
        
        alerts = generate_ftl_alerts(crew_data)
        
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.FTL_CRITICAL
        assert alerts[0].severity == AlertSeverity.CRITICAL
    
    def test_multiple_alerts(self):
        """Test multiple alerts."""
        crew_data = [
            {"crew_id": "1", "hours_28_day": 90, "hours_12_month": 800},
            {"crew_id": "2", "hours_28_day": 98, "hours_12_month": 950},
            {"crew_id": "3", "hours_28_day": 50, "hours_12_month": 500},
        ]
        
        alerts = generate_ftl_alerts(crew_data)
        
        assert len(alerts) == 2


class TestGenerateStandbyAlerts:
    """Tests for standby alert generation."""
    
    def test_no_alert_sufficient_standby(self):
        """Test no alert when standby is sufficient."""
        alerts = generate_standby_alerts(10, required_min=5)
        assert len(alerts) == 0
    
    def test_warning_low_standby(self):
        """Test warning for low standby."""
        alerts = generate_standby_alerts(3, required_min=5)
        
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.STANDBY_LOW
        assert alerts[0].severity == AlertSeverity.WARNING
    
    def test_critical_zero_standby(self):
        """Test critical for zero standby."""
        alerts = generate_standby_alerts(0, required_min=5)
        
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL


class TestGenerateSickLeaveAlerts:
    """Tests for sick leave alert generation."""
    
    def test_call_sick_alert(self):
        """Test call sick alert."""
        records = [
            {"crew_id": "1", "crew_name": "Test", "status": "CSL"}
        ]
        
        alerts = generate_sick_leave_alerts(records)
        
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.CALL_SICK
        assert alerts[0].severity == AlertSeverity.WARNING
    
    def test_sick_leave_info_alert(self):
        """Test sick leave info alert."""
        records = [
            {"crew_id": "1", "crew_name": "Test", "status": "SL"}
        ]
        
        alerts = generate_sick_leave_alerts(records)
        
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.SICK_LEAVE
        assert alerts[0].severity == AlertSeverity.INFO


class TestAlertService:
    """Tests for AlertService class."""
    
    def test_create_alert_memory(self):
        """Test creating alert in memory."""
        service = AlertService()
        
        alert = Alert(
            alert_type=AlertType.SYSTEM,
            severity=AlertSeverity.INFO,
            title="Test",
            message="Test message"
        )
        
        result = service.create_alert(alert)
        assert result is not None
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        service = AlertService()
        
        # Create some alerts
        for i in range(3):
            alert = Alert(
                alert_type=AlertType.SYSTEM,
                severity=AlertSeverity.INFO,
                title=f"Test {i}",
                message="Message"
            )
            service.create_alert(alert)
        
        alerts = service.get_active_alerts()
        assert len(alerts) == 3


class TestAlertManager:
    """Tests for AlertManager class."""
    
    def test_run_all_checks(self):
        """Test running all alert checks."""
        manager = AlertManager()
        
        crew_hours = [
            {"crew_id": "1", "hours_28_day": 95, "hours_12_month": 900}
        ]
        standby = [
            {"status": "SBY"},
            {"status": "CSL", "crew_id": "2", "crew_name": "Test"}
        ]
        
        alerts = manager.run_all_checks(crew_hours, standby)
        
        # Should have FTL + call sick alerts (standby count = 1, may trigger low standby too)
        assert len(alerts) >= 2
    
    def test_get_summary(self):
        """Test getting alert summary."""
        manager = AlertManager()
        
        summary = manager.get_summary()
        
        assert "total_active" in summary
        assert "by_severity" in summary
        assert "latest" in summary


# =====================================================
# Run tests
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
