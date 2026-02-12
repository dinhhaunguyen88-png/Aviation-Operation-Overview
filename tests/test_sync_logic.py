import pytest
from unittest.mock import MagicMock, patch
from datetime import date, datetime
import sys
import os

# Add parent directory to path to import api_server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test (we need to patch the global objects mostly)
# Since we can't easily import api_server if it runs app.run(), we assume it doesn't run on import.
# Based on the code, app.run is not at top level, so it's safe.
import api_server

@pytest.fixture
def mock_aims_client():
    # Patch the underlying attribute, not the property
    with patch('api_server.data_processor._aims_client', new_callable=MagicMock) as mock:
        yield mock

@pytest.fixture
def mock_supabase():
    # Patch the underlying attribute, not the property
    with patch('api_server.data_processor._supabase', new_callable=MagicMock) as mock:
        yield mock

@pytest.fixture
def mock_helpers():
    # Helper for mocking helper functions if needed, or testing them directly
    pass

# ============================================================================
# Test: _sync_flight_history
# ============================================================================
def test_sync_flight_history(mock_aims_client):
    """Test standard flow of fetching flight history."""
    # Setup
    target_date = date(2026, 2, 1)
    
    mock_aims_client.get_flights_range.return_value = [
        {"flight_date": "2026-01-10", "flight_number": "VJ100", "block_time": "02:00"},
        {"flight_date": "2026-01-11", "flight_number": "VJ101", "block_time": "01:30"}
    ]
    
    # Execute - now returns a tuple (map_28d, map_12m)
    result_28d, result_12m = api_server._sync_flight_history(target_date)
    
    # Verify - both maps should contain the flights (within 28d window)
    assert len(result_12m) == 2
    # Verify normalized keys (numeric part only)
    assert result_12m[("2026-01-10", "100")] == 120  # VJ100 -> 100
    assert result_12m[("2026-01-11", "101")] == 90   # VJ101 -> 101
    
    # Verify calls (simplistic check that it was called at least once)
    assert mock_aims_client.get_flights_range.called

# ============================================================================
# Test: _sync_daily_flights (7-day window)
# ============================================================================
def test_sync_daily_flights(mock_aims_client, mock_supabase):
    """Test fetching and upserting flights for 7-day window."""
    from datetime import timedelta
    target_date = date(2026, 2, 1)
    sync_dates = [target_date + timedelta(days=d) for d in range(-2, 5)]  # 7 days
    
    mock_aims_client.get_day_flights.return_value = [
        {"flight_number": "VJ200", "departure": "SGN", "arrival": "HAN", "flight_status": "SCH"}
    ]
    
    # Mock the mod log query (cancellations)
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    api_server._sync_daily_flights(sync_dates)
    
    # Verify get_day_flights called 7 times (once per date)
    assert mock_aims_client.get_day_flights.call_count == 7
    
    # Verify upsert was called (at least once for the flights)
    assert mock_supabase.table.return_value.upsert.return_value.execute.called

# ============================================================================
# Test: _fetch_candidate_crew
# ============================================================================
def test_fetch_candidate_crew(mock_aims_client):
    """Test fetching candidate crew and injecting position."""
    # Use side_effect to return a NEW list/dict each time to avoid reference mutation during the loop
    mock_aims_client.get_crew_list.side_effect = lambda *args, **kwargs: [{"crew_id": "1", "crew_name": "A"}]
    
    target_date = date(2026, 2, 1)
    result = api_server._fetch_candidate_crew(target_date)
    
    # Should have 4 positions * 1 crew = 4 crew total
    assert len(result) == 4
    # Check that position was injected
    assert "position" in result[0]
    assert result[0]["position"] == "CP" 

# ============================================================================
# Test: _process_crew_duties
# ============================================================================
def test_process_crew_duties(mock_aims_client):
    """Test parallel duty processing."""
    target_date = date(2026, 2, 1)
    today_iso = target_date.isoformat()
    
    # Mocks
    candidate_crew = [
        {"crew_id": "1001", "crew_name": "Capt A", "position": "CP", "base": "SGN"},
        {"crew_id": "1002", "crew_name": "FO B", "position": "FO", "base": "SGN"} # Will have no duty
    ]
    
    flight_block_map_28d = {
        ("2026-02-01", "300"): 120
    }
    
    flight_block_map_12m = {
        ("2026-02-01", "300"): 120
    }
    
    # Mock schedules
    def side_effect_schedule(*args, **kwargs):
        cid = kwargs.get("crew_id")
        if cid == "1001":
            return [
                {"start_dt": f"{today_iso}T08:00:00", "flight_number": "VJ300", "activity_code": "FLY"}
            ]
        return []

    mock_aims_client.get_crew_schedule.side_effect = side_effect_schedule
    
    # Execute with 4 args (28d map, 12m map, target_date)
    with patch('time.sleep'):
        results = api_server._process_crew_duties(candidate_crew, flight_block_map_28d, flight_block_map_12m, target_date)
    
    # Verify
    assert len(results) == 1
    res = results[0]
    assert res["meta"]["crew_id"] == "1001"
    assert res["ftl_28d_mins"] == 120
    assert len(res["roster"]) == 1

# ============================================================================
# Test: _upsert_sync_results
# ============================================================================
def test_upsert_sync_results(mock_supabase):
    """Test batch upsert logic."""
    target_date = date(2026, 2, 1)
    
    results = [
        {
            "meta": {"crew_id": "1001", "crew_name": "Test Crew", "position": "CAPT"},
            "roster": [{"activity_code": "FLY", "start_dt": "2026-02-01T10:00", "end_dt": "2026-02-01T14:00", "flight_number": "VJ999"}],
            "ftl_mins": 5400 # 90 hours
        }
    ]
    
    # Import constants to verify logic if needed, but here we check output
    # 90 hours > 85 (WARNING) but <= 95 (CRITICAL) -> WARNING
    
    api_server._upsert_sync_results(results, target_date)
    
    # Verify tables called
    # Check that crew_members upsert includes 'position'
    found_crew_upsert = False
    for call in mock_supabase.table.return_value.upsert.call_args_list:
        data = call[0][0]
        if data and "position" in data[0]:
            found_crew_upsert = True
            assert data[0]["position"] == "CAPT" # From meta in results
            break
    assert found_crew_upsert

# ============================================================================
# Test: API Join Logic
# ============================================================================
def test_api_crew_join(mock_supabase):
    """Test that /api/crew correctly queries crew_members table."""
    import os
    with api_server.app.test_client() as client:
        api_key = os.getenv("X_API_KEY") or os.getenv("SUPABASE_KEY") or "test-key"
        
        # Mock the count query chain
        mock_count = MagicMock()
        mock_count.count = 0
        mock_supabase.table.return_value.select.return_value.neq.return_value.range.return_value.execute.return_value = mock_count
        
        # Mock the data query chain  
        mock_data = MagicMock()
        mock_data.data = []
        mock_supabase.table.return_value.select.return_value.neq.return_value.execute.return_value = mock_data
        
        response = client.get('/api/crew', headers={'X-API-Key': api_key})
        
        # Verify that the crew_members table was queried
        mock_supabase.table.assert_any_call("crew_members")

# ============================================================================
# Test: normalize_flight_id
# ============================================================================
def test_normalize_flight_id():
    """Test various flight number formats for normalization."""
    from api_server import normalize_flight_id
    
    assert normalize_flight_id("VJ1250") == "1250"
    assert normalize_flight_id("VJ1250A") == "1250"
    assert normalize_flight_id("1250/SGN") == "1250"
    assert normalize_flight_id("1250") == "1250"
    assert normalize_flight_id("VN123") == "123"
    assert normalize_flight_id(None) == ""
    assert normalize_flight_id("") == ""
    assert normalize_flight_id("ABC") == "ABC" # Fallback if no digits
