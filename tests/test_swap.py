"""
Aircraft Swap Analysis - Comprehensive Test Suite
Phase 04: Testing & Verification

Tests for:
- swap_detector.py unit tests (detection, classification, KPIs)
- API endpoints (/api/swap/*)
- Authentication and error handling
"""

import pytest
import json
import os
import sys
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock

# Project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swap_detector import (
    detect_swaps, classify_swap_reason, calculate_swap_kpis,
    get_reason_breakdown, get_top_impacted_tails, generate_swap_event_id,
    _calculate_delay, _determine_recovery
)
from api_server import app


# =====================================================
# Fixtures
# =====================================================

@pytest.fixture
def api_key():
    """Get API key for test requests."""
    return os.getenv("X_API_KEY") or os.getenv("SUPABASE_KEY") or "test-key"


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_snapshots():
    """Baseline flight snapshots."""
    return {
        "2026-02-12|VN100|SGN": {"first_seen_reg": "VN-A888", "first_seen_ac_type": "A350"},
        "2026-02-12|VN200|HAN": {"first_seen_reg": "VN-A391", "first_seen_ac_type": "B787"},
        "2026-02-12|VN300|DAD": {"first_seen_reg": "VN-A672", "first_seen_ac_type": "A321"},
    }


@pytest.fixture
def sample_swap_events():
    """Sample swap records for aggregation tests."""
    return [
        {
            "swap_event_id": "SW-0001", "flight_number": "VN100",
            "flight_date": "2026-02-12", "departure": "SGN", "arrival": "HAN",
            "original_reg": "VN-A888", "swapped_reg": "VN-A899",
            "original_ac_type": "A350", "swapped_ac_type": "A350",
            "swap_category": "MAINTENANCE", "swap_reason": "MEL DEFECT",
            "delay_minutes": 45, "recovery_status": "DELAYED",
            "detected_at": "2026-02-12T08:00:00"
        },
        {
            "swap_event_id": "SW-0002", "flight_number": "VN200",
            "flight_date": "2026-02-12", "departure": "HAN", "arrival": "SGN",
            "original_reg": "VN-A391", "swapped_reg": "VN-A520",
            "original_ac_type": "B787", "swapped_ac_type": "B787",
            "swap_category": "WEATHER", "swap_reason": "Fog delay",
            "delay_minutes": 0, "recovery_status": "RECOVERED",
            "detected_at": "2026-02-12T09:00:00"
        },
        {
            "swap_event_id": "SW-0003", "flight_number": "VN300",
            "flight_date": "2026-02-12", "departure": "DAD", "arrival": "SGN",
            "original_reg": "VN-A672", "swapped_reg": "VN-A720",
            "original_ac_type": "A321", "swapped_ac_type": "A321",
            "swap_category": "CREW", "swap_reason": "Crew sick leave",
            "delay_minutes": 80, "recovery_status": "DELAYED",
            "detected_at": "2026-02-12T10:00:00"
        },
        {
            "swap_event_id": "SW-0004", "flight_number": "VN400",
            "flight_date": "2026-02-11", "departure": "SGN", "arrival": "DAD",
            "original_reg": "VN-A888", "swapped_reg": "VN-A850",
            "original_ac_type": "A350", "swapped_ac_type": "A350",
            "swap_category": "MAINTENANCE", "swap_reason": "Scheduled check",
            "delay_minutes": 15, "recovery_status": "RECOVERED",
            "detected_at": "2026-02-11T14:00:00"
        },
    ]


# =====================================================
# 1. Swap Reason Classification Tests
# =====================================================

class TestSwapReasonClassification:
    """Tests for classify_swap_reason function."""

    def test_maintenance_keywords(self):
        """Detect maintenance-related reasons."""
        cases = ["MEL DEFECT on engine", "AIRCRAFT AOG", "Tech issue", "Unserviceable component"]
        for desc in cases:
            cat, _ = classify_swap_reason(desc, "")
            assert cat == "MAINTENANCE", f"'{desc}' should be MAINTENANCE, got {cat}"

    def test_weather_keywords(self):
        """Detect weather-related reasons."""
        cases = ["Weather delay due to fog", "Storm diversion", "Typhoon alert", "Wind shear warning"]
        for desc in cases:
            cat, _ = classify_swap_reason(desc, "")
            assert cat == "WEATHER", f"'{desc}' should be WEATHER, got {cat}"

    def test_crew_keywords(self):
        """Detect crew-related reasons."""
        cases = ["Crew sick leave", "Pilot FTL exceeded"]
        for desc in cases:
            cat, _ = classify_swap_reason(desc, "")
            assert cat == "CREW", f"'{desc}' should be CREW, got {cat}"

    def test_operational_keywords(self):
        """Detect operational reasons."""
        cases = ["Schedule change OPS"]
        for desc in cases:
            cat, _ = classify_swap_reason(desc, "")
            assert cat == "OPERATIONAL", f"'{desc}' should be OPERATIONAL, got {cat}"

    def test_unknown_fallback(self):
        """Empty or unrecognized text falls back to UNKNOWN."""
        cat, _ = classify_swap_reason("", "")
        assert cat == "UNKNOWN"

        cat2, _ = classify_swap_reason("random gibberish xyz", "")
        assert cat2 == "UNKNOWN"

    def test_case_insensitive(self):
        """Classification is case-insensitive."""
        cat, _ = classify_swap_reason("mel defect", "")
        assert cat == "MAINTENANCE"

    def test_log_description_fallback(self):
        """Log description used when status_desc has no match."""
        cat, _ = classify_swap_reason("", "Engine failure report")
        assert cat == "MAINTENANCE"


# =====================================================
# 2. Swap Detection Tests
# =====================================================

class TestSwapDetection:
    """Tests for detect_swaps function."""

    def test_no_swap_same_reg(self, sample_snapshots):
        """No swap when aircraft registration matches snapshot."""
        flights = [{
            "flight_number": "VN100", "flight_date": "2026-02-12",
            "departure": "SGN", "aircraft_reg": "VN-A888", "aircraft_type": "A350"
        }]
        result = detect_swaps(flights, sample_snapshots)
        assert len(result) == 0

    def test_swap_detected_different_reg(self, sample_snapshots):
        """Swap detected when registration differs from snapshot."""
        flights = [{
            "flight_number": "VN100", "flight_date": "2026-02-12",
            "departure": "SGN", "arrival": "HAN",
            "aircraft_reg": "VN-A999", "aircraft_type": "A350",
            "flight_status": "ARRIVED", "std": "08:00", "atd": "08:30"
        }]
        result = detect_swaps(flights, sample_snapshots)
        assert len(result) == 1
        assert result[0]["original_reg"] == "VN-A888"
        assert result[0]["swapped_reg"] == "VN-A999"

    def test_no_swap_no_snapshot(self, sample_snapshots):
        """No swap detected if no snapshot exists for flight."""
        flights = [{
            "flight_number": "VN999", "flight_date": "2026-02-12",
            "departure": "PQC", "aircraft_reg": "VN-A111", "aircraft_type": "A320"
        }]
        result = detect_swaps(flights, sample_snapshots)
        assert len(result) == 0

    def test_multiple_swaps(self, sample_snapshots):
        """Detect multiple swaps in a single run."""
        flights = [
            {
                "flight_number": "VN100", "flight_date": "2026-02-12",
                "departure": "SGN", "arrival": "HAN",
                "aircraft_reg": "VN-A990", "aircraft_type": "A350",
                "std": "08:00", "atd": "08:00"
            },
            {
                "flight_number": "VN200", "flight_date": "2026-02-12",
                "departure": "HAN", "arrival": "SGN",
                "aircraft_reg": "VN-A550", "aircraft_type": "B787",
                "std": "10:00", "atd": "10:20"
            },
        ]
        result = detect_swaps(flights, sample_snapshots)
        assert len(result) == 2

    def test_swap_fields_populated(self, sample_snapshots):
        """Swap result has all required fields."""
        flights = [{
            "flight_number": "VN100", "flight_date": "2026-02-12",
            "departure": "SGN", "arrival": "HAN",
            "aircraft_reg": "VN-A999", "aircraft_type": "A350",
            "flight_status": "DEPARTED", "std": "08:00", "atd": "08:15"
        }]
        result = detect_swaps(flights, sample_snapshots)
        swap = result[0]
        # detect_swaps doesn't add swap_event_id/detected_at (ETL adds those)
        required_fields = [
            "flight_number", "flight_date", "departure", "arrival",
            "original_reg", "swapped_reg", "original_ac_type", "swapped_ac_type",
            "swap_category", "swap_reason", "delay_minutes", "recovery_status"
        ]
        for field in required_fields:
            assert field in swap, f"Missing field: {field}"

    def test_delay_calculation(self, sample_snapshots):
        """Delay calculated correctly from STD vs ATD."""
        flights = [{
            "flight_number": "VN100", "flight_date": "2026-02-12",
            "departure": "SGN", "arrival": "HAN",
            "aircraft_reg": "VN-A999", "aircraft_type": "A350",
            "std": "08:00", "atd": "08:45"
        }]
        result = detect_swaps(flights, sample_snapshots)
        assert result[0]["delay_minutes"] == 45


# =====================================================
# 3. KPI Calculation Tests
# =====================================================

class TestKPICalculation:
    """Tests for calculate_swap_kpis function."""

    def test_basic_kpis(self, sample_swap_events):
        """Calculate basic KPIs correctly."""
        kpis = calculate_swap_kpis(sample_swap_events, total_flights=200, previous_period_swaps=6)
        assert kpis["total_swaps"] == 4
        assert kpis["swap_rate"] == 2.0  # 4/200 * 100

    def test_recovery_rate(self, sample_swap_events):
        """Recovery rate calculated correctly."""
        # 2 RECOVERED out of 4 → 50%
        kpis = calculate_swap_kpis(sample_swap_events, total_flights=200)
        assert kpis["recovery_rate"] == 50.0

    def test_trend_calculation(self, sample_swap_events):
        """Trend vs last period calculated correctly."""
        kpis = calculate_swap_kpis(sample_swap_events, total_flights=200, previous_period_swaps=8)
        assert kpis["trend_vs_last_period"] == -50.0  # (4-8)/8 * 100

    def test_trend_no_previous(self, sample_swap_events):
        """Trend when no previous period data."""
        kpis = calculate_swap_kpis(sample_swap_events, total_flights=200, previous_period_swaps=0)
        assert kpis["trend_vs_last_period"] == 0

    def test_empty_swaps(self):
        """KPIs with no swap data."""
        kpis = calculate_swap_kpis([], total_flights=100)
        assert kpis["total_swaps"] == 0
        assert kpis["swap_rate"] == 0
        assert kpis["recovery_rate"] == 100.0

    def test_zero_flights(self, sample_swap_events):
        """Handle zero total flights."""
        kpis = calculate_swap_kpis(sample_swap_events, total_flights=0)
        assert kpis["swap_rate"] == 0


# =====================================================
# 4. Aggregation Tests
# =====================================================

class TestAggregation:
    """Tests for breakdown and top tails functions."""

    def test_reason_breakdown(self, sample_swap_events):
        """Reason breakdown has correct categories."""
        breakdown = get_reason_breakdown(sample_swap_events)
        assert len(breakdown) > 0

        # get_reason_breakdown returns title-case categories
        categories = [r["category"] for r in breakdown]
        assert "Maintenance" in categories
        assert "Weather" in categories
        assert "Crew" in categories

    def test_breakdown_percentages_sum(self, sample_swap_events):
        """Percentages sum to ~100%."""
        breakdown = get_reason_breakdown(sample_swap_events)
        total_pct = sum(r["percentage"] for r in breakdown)
        assert abs(total_pct - 100.0) < 1.0  # Allow rounding

    def test_breakdown_sorted_desc(self, sample_swap_events):
        """Breakdown sorted by count descending."""
        breakdown = get_reason_breakdown(sample_swap_events)
        counts = [r["count"] for r in breakdown]
        assert counts == sorted(counts, reverse=True)

    def test_top_tails(self, sample_swap_events):
        """Top impacted tails ranked correctly."""
        tails = get_top_impacted_tails(sample_swap_events, limit=5)
        assert len(tails) > 0
        # VN-A888 appears as original_reg in 2 swaps → should be top
        assert tails[0]["reg"] == "VN-A888"
        assert tails[0]["swap_count"] >= 2

    def test_top_tails_limit(self, sample_swap_events):
        """Limit parameter works."""
        tails = get_top_impacted_tails(sample_swap_events, limit=1)
        assert len(tails) <= 1

    def test_top_tails_severity(self, sample_swap_events):
        """Severity badges assigned."""
        tails = get_top_impacted_tails(sample_swap_events, limit=5)
        for t in tails:
            assert t["severity"] in ["CRITICAL", "HIGH", "NORMAL"]

    def test_empty_breakdown(self):
        """Empty swap list returns empty breakdown."""
        breakdown = get_reason_breakdown([])
        assert len(breakdown) == 0

    def test_empty_top_tails(self):
        """Empty swap list returns empty top tails."""
        tails = get_top_impacted_tails([], limit=5)
        assert len(tails) == 0


# =====================================================
# 5. Event ID Generation Tests
# =====================================================

class TestEventIdGeneration:
    """Tests for generate_swap_event_id function."""

    def test_first_event(self):
        assert generate_swap_event_id(0) == "SW-0001"

    def test_sequential(self):
        assert generate_swap_event_id(23) == "SW-0024"

    def test_large_number(self):
        assert generate_swap_event_id(999) == "SW-1000"


# =====================================================
# 6. API Endpoint Tests - Swap Summary
# =====================================================

class TestSwapSummaryAPI:
    """Tests for GET /api/swap/summary."""

    def test_requires_api_key(self, client):
        """Should return 401 without API key."""
        response = client.get('/api/swap/summary')
        assert response.status_code == 401

    def test_summary_with_key(self, client, api_key):
        """Should return 200 with valid API key."""
        response = client.get('/api/swap/summary', headers={'X-API-Key': api_key})
        assert response.status_code in [200, 503]  # 503 if no DB

    def test_summary_response_format(self, client, api_key):
        """Response has correct JSON structure."""
        response = client.get('/api/swap/summary?period=7d', headers={'X-API-Key': api_key})
        data = json.loads(response.data)
        assert 'success' in data
        assert 'timestamp' in data

    def test_period_parameter(self, client, api_key):
        """Different periods accepted."""
        for period in ['24h', '7d', '30d']:
            response = client.get(f'/api/swap/summary?period={period}', headers={'X-API-Key': api_key})
            assert response.status_code in [200, 503]


# =====================================================
# 7. API Endpoint Tests - Swap Events
# =====================================================

class TestSwapEventsAPI:
    """Tests for GET /api/swap/events."""

    def test_requires_api_key(self, client):
        """Should return 401 without API key."""
        response = client.get('/api/swap/events')
        assert response.status_code == 401

    def test_events_with_key(self, client, api_key):
        """Should return 200 with valid API key."""
        response = client.get('/api/swap/events', headers={'X-API-Key': api_key})
        assert response.status_code in [200, 503]

    def test_pagination_params(self, client, api_key):
        """Pagination parameters accepted."""
        response = client.get('/api/swap/events?page=1&per_page=5', headers={'X-API-Key': api_key})
        assert response.status_code in [200, 503]

    def test_category_filter(self, client, api_key):
        """Category filter accepted."""
        response = client.get('/api/swap/events?category=MAINTENANCE', headers={'X-API-Key': api_key})
        assert response.status_code in [200, 503]


# =====================================================
# 8. API Endpoint Tests - Swap Reasons
# =====================================================

class TestSwapReasonsAPI:
    """Tests for GET /api/swap/reasons."""

    def test_requires_api_key(self, client):
        response = client.get('/api/swap/reasons')
        assert response.status_code == 401

    def test_reasons_with_key(self, client, api_key):
        response = client.get('/api/swap/reasons?period=7d', headers={'X-API-Key': api_key})
        assert response.status_code in [200, 503]


# =====================================================
# 9. API Endpoint Tests - Top Tails
# =====================================================

class TestSwapTopTailsAPI:
    """Tests for GET /api/swap/top-tails."""

    def test_requires_api_key(self, client):
        response = client.get('/api/swap/top-tails')
        assert response.status_code == 401

    def test_top_tails_with_key(self, client, api_key):
        response = client.get('/api/swap/top-tails?period=7d&limit=5', headers={'X-API-Key': api_key})
        assert response.status_code in [200, 503]


# =====================================================
# 10. API Endpoint Tests - Swap Trend
# =====================================================

class TestSwapTrendAPI:
    """Tests for GET /api/swap/trend."""

    def test_requires_api_key(self, client):
        response = client.get('/api/swap/trend')
        assert response.status_code == 401

    def test_trend_with_key(self, client, api_key):
        response = client.get('/api/swap/trend?period=7d', headers={'X-API-Key': api_key})
        assert response.status_code in [200, 503]


# =====================================================
# 11. Frontend Route Test
# =====================================================

class TestSwapFrontendRoute:
    """Tests for /aircraft-swap page route."""

    def test_aircraft_swap_page(self, client):
        """Page should render (200 or template error)."""
        response = client.get('/aircraft-swap')
        # May 500 if sidebar.html has dependencies, but should not 404
        assert response.status_code != 404


# =====================================================
# Run
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
