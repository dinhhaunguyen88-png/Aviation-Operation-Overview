"""
Unit Tests - Exports Module
Phase 5: Testing & Deployment

Tests for export functionality.
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock

from exports import (
    export_to_csv,
    export_crew_list,
    export_flight_hours,
    export_flights,
    export_standby,
    export_alerts,
    export_to_excel,
    export_dashboard_report
)


class TestExportToCSV:
    """Tests for export_to_csv function."""
    
    def test_export_basic_data(self):
        """Test exporting basic data."""
        data = [
            {"id": 1, "name": "Test 1", "value": 100},
            {"id": 2, "name": "Test 2", "value": 200},
        ]
        
        result = export_to_csv(data)
        
        assert isinstance(result, bytes)
        assert b"id" in result
        assert b"name" in result
        assert b"Test 1" in result
    
    def test_export_empty_data(self):
        """Test exporting empty data."""
        result = export_to_csv([])
        
        assert result == b""
    
    def test_export_single_row(self):
        """Test exporting single row."""
        data = [{"field": "value"}]
        
        result = export_to_csv(data)
        
        assert b"field" in result
        assert b"value" in result
    
    def test_export_unicode_data(self):
        """Test exporting unicode data."""
        data = [{"name": "Nguyễn Văn A", "city": "Hồ Chí Minh"}]
        
        result = export_to_csv(data)
        
        assert isinstance(result, bytes)
        # UTF-8 BOM should be present
        assert result.startswith(b'\xef\xbb\xbf') or b"Nguy" in result


class TestExportCrewList:
    """Tests for export_crew_list function."""
    
    def test_export_crew_data(self):
        """Test exporting crew data."""
        crew_data = [
            {
                "crew_id": "12345",
                "crew_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
                "base": "SGN",
                "position": "Captain",
                "email": "john@example.com",
                "cell_phone": "0901234567",
                "status": "Active"
            }
        ]
        
        result = export_crew_list(crew_data)
        
        assert isinstance(result, bytes)
        assert b"Crew ID" in result
        assert b"12345" in result
        assert b"John Doe" in result
    
    def test_export_empty_crew(self):
        """Test exporting empty crew list."""
        result = export_crew_list([])
        
        assert result == b""


class TestExportFlightHours:
    """Tests for export_flight_hours function."""
    
    def test_export_flight_hours_data(self):
        """Test exporting flight hours."""
        crew_hours = [
            {
                "crew_id": "12345",
                "crew_name": "John Doe",
                "hours_28_day": 85,
                "hours_12_month": 800,
                "warning_level": "NORMAL",
                "calculation_date": "2026-01-30"
            }
        ]
        
        result = export_flight_hours(crew_hours)
        
        assert isinstance(result, bytes)
        assert b"28-Day Hours" in result
        assert b"12-Month Hours" in result
        assert b"85" in result


class TestExportFlights:
    """Tests for export_flights function."""
    
    def test_export_flights_data(self):
        """Test exporting flights."""
        flight_data = [
            {
                "flight_date": "2026-01-30",
                "carrier_code": "VN",
                "flight_number": "123",
                "departure": "SGN",
                "arrival": "HAN",
                "std": "08:00",
                "sta": "10:00",
                "aircraft_type": "A321",
                "aircraft_reg": "VN-A123",
                "status": "On Time"
            }
        ]
        
        result = export_flights(flight_data)
        
        assert isinstance(result, bytes)
        assert b"Flight Number" in result
        assert b"SGN" in result
        assert b"HAN" in result


class TestExportStandby:
    """Tests for export_standby function."""
    
    def test_export_standby_data(self):
        """Test exporting standby records."""
        standby_data = [
            {
                "crew_id": "12345",
                "crew_name": "John Doe",
                "status": "SBY",
                "duty_start_date": "2026-01-30",
                "duty_end_date": "2026-01-30",
                "base": "SGN"
            }
        ]
        
        result = export_standby(standby_data)
        
        assert isinstance(result, bytes)
        assert b"Status" in result
        assert b"SBY" in result


class TestExportAlerts:
    """Tests for export_alerts function."""
    
    def test_export_alerts_data(self):
        """Test exporting alerts."""
        alerts = [
            {
                "id": "alert1",
                "alert_type": "FTL_WARNING",
                "severity": "warning",
                "title": "FTL Warning",
                "message": "Flight hours at 90%",
                "crew_id": "12345",
                "created_at": "2026-01-30T10:00:00",
                "acknowledged": False
            }
        ]
        
        result = export_alerts(alerts)
        
        assert isinstance(result, bytes)
        assert b"Type" in result
        assert b"FTL_WARNING" in result


class TestExportToExcel:
    """Tests for export_to_excel function."""
    
    def test_export_single_sheet(self):
        """Test exporting single sheet Excel."""
        sheets = {
            "Data": [
                {"id": 1, "name": "Test"}
            ]
        }
        
        result = export_to_excel(sheets)
        
        # Result should be bytes (Excel file or CSV fallback)
        assert isinstance(result, bytes)
    
    def test_export_multiple_sheets(self):
        """Test exporting multiple sheets."""
        sheets = {
            "Sheet1": [{"col1": "val1"}],
            "Sheet2": [{"col2": "val2"}]
        }
        
        result = export_to_excel(sheets)
        
        assert isinstance(result, bytes)
    
    def test_export_empty_sheets(self):
        """Test exporting empty sheets."""
        sheets = {}
        
        result = export_to_excel(sheets)
        
        # Should handle gracefully
        assert isinstance(result, bytes) or result == b""


class TestExportDashboardReport:
    """Tests for export_dashboard_report function."""
    
    def test_export_full_report(self):
        """Test exporting full dashboard report."""
        summary = {
            "date": "2026-01-30",
            "total_crew": 100,
            "total_flights": 50,
            "total_block_hours": 200,
            "aircraft_utilization": 85,
            "standby_available": 10,
            "sick_leave": 5,
            "alerts_count": 3,
            "crew_by_status": {"FLY": 60, "SBY": 20, "OFF": 20}
        }
        
        crew_hours = [
            {"crew_id": "1", "hours_28_day": 80}
        ]
        
        flights = [
            {"flight_number": "VN123"}
        ]
        
        standby = [
            {"crew_id": "1", "status": "SBY"}
        ]
        
        result = export_dashboard_report(summary, crew_hours, flights, standby)
        
        assert isinstance(result, bytes)


class TestExportEdgeCases:
    """Tests for edge cases."""
    
    def test_special_characters(self):
        """Test exporting data with special characters."""
        data = [
            {"field": "Value with, comma"},
            {"field": 'Value with "quotes"'},
            {"field": "Value with\nnewline"}
        ]
        
        result = export_to_csv(data)
        
        assert isinstance(result, bytes)
    
    def test_numeric_values(self):
        """Test exporting numeric values."""
        data = [
            {"int_val": 123, "float_val": 123.456}
        ]
        
        result = export_to_csv(data)
        
        assert b"123" in result
    
    def test_none_values(self):
        """Test exporting None values."""
        data = [
            {"field1": "value", "field2": None}
        ]
        
        result = export_to_csv(data)
        
        assert isinstance(result, bytes)
    
    def test_large_dataset(self):
        """Test exporting large dataset."""
        data = [{"id": i, "value": f"row_{i}"} for i in range(1000)]
        
        result = export_to_csv(data)
        
        assert isinstance(result, bytes)
        assert len(result) > 10000  # Should be substantial


class TestExportFormats:
    """Tests for different export formats."""
    
    def test_csv_format(self):
        """Test CSV format output."""
        data = [{"a": 1, "b": 2}]
        
        result = export_to_csv(data)
        
        # Should be valid CSV with headers
        lines = result.decode('utf-8-sig').split('\r\n')
        assert len(lines) >= 2  # Header + data
    
    def test_csv_delimiter(self):
        """Test CSV uses correct delimiter."""
        data = [{"col1": "val1", "col2": "val2"}]
        
        result = export_to_csv(data)
        decoded = result.decode('utf-8-sig')
        
        assert "," in decoded


# =====================================================
# Run tests
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
