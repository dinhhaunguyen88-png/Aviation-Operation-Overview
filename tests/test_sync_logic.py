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
    
    # Execute
    result = api_server._sync_flight_history(target_date)
    
    # Verify
    assert len(result) == 2
    assert result[("2026-01-10", "VJ100")] == 120 # 2 hours * 60
    assert result[("2026-01-11", "VJ101")] == 90 # 1.5 hours * 60
    
    # Verify calls (simplistic check that it was called at least once)
    assert mock_aims_client.get_flights_range.called

# ============================================================================
# Test: _sync_today_flights
# ============================================================================
def test_sync_today_flights(mock_aims_client, mock_supabase):
    """Test fetching and upserting today's flights."""
    target_date = date(2026, 2, 1)
    
    mock_aims_client.get_day_flights.return_value = [
        {"flight_number": "VJ200", "departure": "SGN", "arrival": "HAN", "flight_status": "SCH"}
    ]
    
    api_server._sync_today_flights(target_date)
    
    # Verify upsert called
    mock_supabase.table.return_value.upsert.return_value.execute.assert_called()
    
    # Check args
    call_args = mock_supabase.table.return_value.upsert.call_args[0][0]
    assert len(call_args) == 1
    assert call_args[0]["flight_number"] == "VJ200"

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
    
    flight_block_map = {
        ("2026-02-01", "VJ300"): 120
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
    
    # Execute
    # We mock ThreadPool to run synchronously for ease or trust it handles the mock objects
    # With patching properly key components, it should work even threaded.
    
    # Note: Using patched time.sleep to speed up test
    with patch('time.sleep'):
        results = api_server._process_crew_duties(candidate_crew, flight_block_map, target_date)
    
    # Verify
    assert len(results) == 1
    res = results[0]
    assert res["meta"]["crew_id"] == "1001"
    assert res["ftl_mins"] == 120
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
    """Test that /api/crew uses the correct join syntax."""
    # We mock the flask request context if needed, but here we can just test the query builder
    # Since /api/crew is a route, we use app.test_client()
    with api_server.app.test_client() as client:
        # Mock supabase query chain
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value.data = []
        
        client.get('/api/crew')
        
        # Verify select was called with the join string
        mock_supabase.table.return_value.select.assert_called_with("*, crew_flight_hours(hours_28_day, warning_level)")

