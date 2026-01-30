"""
Unit Tests - Data Processor
Phase 5: Testing & Deployment

Tests for data processing functions.
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch

# Import modules to test
from data_processor import (
    parse_hours_string,
    calculate_warning_level,
    get_top_high_intensity_crew,
    calculate_dashboard_summary,
    validate_crew_record,
    validate_flight_record,
    DataProcessor
)


class TestParseHoursString:
    """Tests for parse_hours_string function."""
    
    def test_parse_standard_format(self):
        """Test parsing standard HH:MM format."""
        assert parse_hours_string("85:30") == 85.5
        assert parse_hours_string("100:00") == 100.0
        assert parse_hours_string("12:15") == 12.25
    
    def test_parse_empty_values(self):
        """Test parsing empty/null values."""
        assert parse_hours_string("") == 0.0
        assert parse_hours_string("-") == 0.0
        assert parse_hours_string("N/A") == 0.0
        assert parse_hours_string(None) == 0.0
    
    def test_parse_decimal_format(self):
        """Test parsing decimal format."""
        assert parse_hours_string("85.5") == 85.5
        assert parse_hours_string("100") == 100.0
    
    def test_parse_with_whitespace(self):
        """Test parsing with whitespace."""
        assert parse_hours_string("  85:30  ") == 85.5
        assert parse_hours_string(" 100 ") == 100.0


class TestCalculateWarningLevel:
    """Tests for calculate_warning_level function."""
    
    def test_normal_level(self):
        """Test normal warning level."""
        assert calculate_warning_level(0, 0) == "NORMAL"
        assert calculate_warning_level(50, 500) == "NORMAL"
        assert calculate_warning_level(84, 840) == "NORMAL"
    
    def test_warning_level(self):
        """Test warning level (85-94%)."""
        assert calculate_warning_level(85, 0) == "WARNING"
        assert calculate_warning_level(90, 0) == "WARNING"
        assert calculate_warning_level(0, 850) == "WARNING"
    
    def test_critical_level(self):
        """Test critical level (95%+)."""
        assert calculate_warning_level(95, 0) == "CRITICAL"
        assert calculate_warning_level(100, 0) == "CRITICAL"
        assert calculate_warning_level(0, 950) == "CRITICAL"
    
    def test_mixed_levels(self):
        """Test when 28d and 12m have different levels."""
        # Should return the higher level
        assert calculate_warning_level(50, 950) == "CRITICAL"
        assert calculate_warning_level(95, 500) == "CRITICAL"


class TestGetTopHighIntensityCrew:
    """Tests for get_top_high_intensity_crew function."""
    
    def test_top_n_by_28_day(self):
        """Test getting top N by 28-day hours."""
        crew_data = [
            {"crew_id": "1", "hours_28_day": 90},
            {"crew_id": "2", "hours_28_day": 80},
            {"crew_id": "3", "hours_28_day": 95},
        ]
        
        result = get_top_high_intensity_crew(crew_data, limit=2, sort_by="hours_28_day")
        
        assert len(result) == 2
        assert result[0]["crew_id"] == "3"
        assert result[1]["crew_id"] == "1"
    
    def test_top_n_by_12_month(self):
        """Test getting top N by 12-month hours."""
        crew_data = [
            {"crew_id": "1", "hours_12_month": 800},
            {"crew_id": "2", "hours_12_month": 900},
            {"crew_id": "3", "hours_12_month": 850},
        ]
        
        result = get_top_high_intensity_crew(crew_data, limit=2, sort_by="hours_12_month")
        
        assert len(result) == 2
        assert result[0]["crew_id"] == "2"
    
    def test_empty_list(self):
        """Test with empty list."""
        result = get_top_high_intensity_crew([], limit=10)
        assert result == []


class TestValidateCrewRecord:
    """Tests for validate_crew_record function."""
    
    def test_valid_record(self):
        """Test valid crew record."""
        record = {
            "crew_id": "12345",
            "crew_name": "John Doe",
            "gender": "M"
        }
        is_valid, errors = validate_crew_record(record)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_crew_id(self):
        """Test missing crew_id."""
        record = {"crew_name": "John Doe"}
        is_valid, errors = validate_crew_record(record)
        assert is_valid is False
        assert "crew_id is required" in errors
    
    def test_invalid_gender(self):
        """Test invalid gender."""
        record = {
            "crew_id": "12345",
            "crew_name": "John Doe",
            "gender": "X"
        }
        is_valid, errors = validate_crew_record(record)
        assert is_valid is False
        assert "gender must be M or F" in errors


class TestValidateFlightRecord:
    """Tests for validate_flight_record function."""
    
    def test_valid_record(self):
        """Test valid flight record."""
        record = {
            "flight_number": "VN123",
            "departure": "SGN",
            "arrival": "HAN"
        }
        is_valid, errors = validate_flight_record(record)
        assert is_valid is True
    
    def test_invalid_airport_code(self):
        """Test invalid airport codes."""
        record = {
            "flight_number": "VN123",
            "departure": "SGNN",  # 4 chars
            "arrival": "HA"       # 2 chars
        }
        is_valid, errors = validate_flight_record(record)
        assert is_valid is False
        assert len(errors) == 2


class TestCalculateDashboardSummary:
    """Tests for calculate_dashboard_summary function."""
    
    def test_empty_data(self):
        """Test with empty data."""
        result = calculate_dashboard_summary(
            crew_data=[],
            flight_data=[],
            standby_data=[],
            target_date=date.today()
        )
        
        assert result["total_crew"] == 0
        assert result["total_flights"] == 0
        assert result["standby_available"] == 0
    
    def test_with_standby_data(self):
        """Test with standby data."""
        standby = [
            {"status": "SBY"},
            {"status": "SBY"},
            {"status": "SL"},
            {"status": "CSL"},
        ]
        
        result = calculate_dashboard_summary(
            crew_data=[],
            flight_data=[],
            standby_data=standby,
            target_date=date.today()
        )
        
        assert result["crew_by_status"]["SBY"] == 2
        assert result["crew_by_status"]["SL"] == 1
        assert result["crew_by_status"]["CSL"] == 1


class TestDataProcessor:
    """Tests for DataProcessor class."""
    
    def test_initialization(self):
        """Test DataProcessor initialization."""
        processor = DataProcessor(data_source="CSV")
        assert processor.data_source == "CSV"
    
    def test_set_data_source(self):
        """Test setting data source."""
        processor = DataProcessor()
        processor.set_data_source("CSV")
        assert processor.data_source == "CSV"
        
        processor.set_data_source("AIMS")
        assert processor.data_source == "AIMS"
    
    def test_invalid_data_source(self):
        """Test setting invalid data source."""
        processor = DataProcessor()
        processor.set_data_source("INVALID")
        # Should not change
        assert processor.data_source in ["AIMS", "CSV"]


# =====================================================
# Run tests
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
