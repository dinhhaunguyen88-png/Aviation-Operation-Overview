"""
Integration Tests - API Server
Phase 5: Testing & Deployment

Tests for API endpoints.
"""

import pytest
import json
import os
from datetime import date
from unittest.mock import Mock, patch

# Import Flask app
import sys
sys.path.insert(0, '..')
from api_server import app


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


class TestHealthEndpoints:
    """Tests for health endpoints."""
    
    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['status'] == 'healthy'
        assert 'version' in data['data']
    
    def test_api_status(self, client):
        """Test API status endpoint."""
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'checks' in data['data']
        assert 'api' in data['data']['checks']


class TestDashboardEndpoints:
    """Tests for dashboard endpoints."""
    
    def test_get_dashboard_summary(self, client, api_key):
        """Test dashboard summary endpoint."""
        response = client.get('/api/dashboard/summary', headers={'X-API-Key': api_key})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'total_flights' in data['data']
    
    def test_get_dashboard_summary_with_date(self, client, api_key):
        """Test dashboard summary with date filter."""
        response = client.get('/api/dashboard/summary?date=2026-01-30', headers={'X-API-Key': api_key})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_flights' in data['data']


class TestCrewEndpoints:
    """Tests for crew endpoints."""
    
    def test_get_crew_list(self, client, api_key):
        """Test crew list endpoint."""
        response = client.get('/api/crew', headers={'X-API-Key': api_key})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'crew' in data['data']
        assert 'page' in data['data']
    
    def test_get_crew_list_with_filters(self, client, api_key):
        """Test crew list with filters."""
        response = client.get('/api/crew?base=SGN&page=1&per_page=10', headers={'X-API-Key': api_key})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['page'] == 1
        assert data['data']['per_page'] == 10


class TestStandbyEndpoints:
    """Tests for standby endpoints."""
    
    def test_get_standby_list(self, client):
        """Test standby list endpoint."""
        response = client.get('/api/standby')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'standby' in data['data']
        assert 'by_status' in data['data']
    
    def test_get_standby_with_filter(self, client):
        """Test standby with status filter."""
        response = client.get('/api/standby?status=SBY')
        
        assert response.status_code == 200


class TestFlightEndpoints:
    """Tests for flight endpoints."""
    
    def test_get_flights(self, client, api_key):
        """Test flights endpoint."""
        response = client.get('/api/flights', headers={'X-API-Key': api_key})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'flights' in data['data']
    
    def test_get_flights_with_filter(self, client, api_key):
        """Test flights with date and aircraft filter."""
        response = client.get('/api/flights?date=2026-01-30&aircraft_type=A320', headers={'X-API-Key': api_key})
        
        assert response.status_code == 200


class TestFTLEndpoints:
    """Tests for FTL endpoints."""
    
    def test_get_ftl_summary(self, client, api_key):
        """Test FTL summary endpoint."""
        response = client.get('/api/ftl/summary', headers={'X-API-Key': api_key})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'by_level' in data['data']
        assert 'compliance_rate' in data['data']
    
    def test_get_ftl_alerts(self, client):
        """Test FTL alerts endpoint."""
        response = client.get('/api/ftl/alerts')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'alerts' in data['data']


class TestConfigEndpoints:
    """Tests for config endpoints."""
    
    def test_get_data_source(self, client):
        """Test get data source endpoint."""
        response = client.get('/api/config/datasource')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data_source' in data['data']
    
    def test_set_data_source(self, client):
        """Test set data source endpoint."""
        response = client.post(
            '/api/config/datasource',
            data=json.dumps({'source': 'CSV'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['data_source'] == 'CSV'
    
    def test_set_invalid_data_source(self, client):
        """Test setting invalid data source."""
        response = client.post(
            '/api/config/datasource',
            data=json.dumps({'source': 'INVALID'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400


class TestExportEndpoints:
    """Tests for export endpoints."""
    
    def test_export_crew_csv(self, client):
        """Test crew CSV export."""
        response = client.get('/api/export/crew?format=csv')
        
        assert response.status_code == 200
        assert 'text/csv' in response.content_type
    
    def test_export_flights_csv(self, client):
        """Test flights CSV export."""
        response = client.get('/api/export/flights?format=csv')
        
        assert response.status_code == 200
    
    def test_export_invalid_type(self, client):
        """Test invalid export type."""
        response = client.get('/api/export/invalid')
        
        assert response.status_code == 400


class TestAlertEndpoints:
    """Tests for alert endpoints."""
    
    def test_get_alerts(self, client):
        """Test alerts endpoint."""
        response = client.get('/api/alerts')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'alerts' in data['data']
    
    def test_get_alert_summary(self, client):
        """Test alert summary endpoint."""
        response = client.get('/api/alerts/summary')
        
        assert response.status_code == 200


class TestCacheEndpoints:
    """Tests for cache endpoints."""
    
    def test_get_cache_status(self, client):
        """Test cache status endpoint."""
        response = client.get('/api/cache/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'backend' in data['data']
    
    def test_clear_cache(self, client):
        """Test clear cache endpoint."""
        response = client.post('/api/cache/clear')
        
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_404_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False


# =====================================================
# Run tests
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
