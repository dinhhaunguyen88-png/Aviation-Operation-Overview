"""
Unit Tests - AIMS SOAP Client
Phase 5: Testing & Deployment

Tests for AIMS SOAP API integration.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import module to test
from aims_soap_client import AIMSSoapClient


class TestAIMSSoapClientInit:
    """Tests for AIMSSoapClient initialization."""
    
    @patch('aims_soap_client.Client')
    def test_init_with_valid_credentials(self, mock_client):
        """Test initialization with valid credentials."""
        mock_client.return_value = MagicMock()
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        assert client.username == "testuser"
        assert client.password == "testpass"
    
    @patch('aims_soap_client.Client')
    def test_init_with_timeout(self, mock_client):
        """Test initialization with custom timeout."""
        mock_client.return_value = MagicMock()
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass",
            timeout=60
        )
        
        assert client is not None
    
    def test_init_with_invalid_wsdl(self):
        """Test initialization with invalid WSDL URL."""
        # Should handle gracefully
        client = AIMSSoapClient(
            wsdl_url="invalid-url",
            username="testuser",
            password="testpass"
        )
        
        assert client.is_connected is False


class TestAIMSSoapClientConnection:
    """Tests for connection status."""
    
    @patch('aims_soap_client.Client')
    def test_is_connected_true(self, mock_client):
        """Test connection status when connected."""
        mock_client.return_value = MagicMock()
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        # Force connection status
        client._client = MagicMock()
        
        assert client.is_connected is True
    
    def test_is_connected_false(self):
        """Test connection status when not connected."""
        client = AIMSSoapClient(
            wsdl_url="invalid-url",
            username="",
            password=""
        )
        
        assert client.is_connected is False


class TestGetCrewList:
    """Tests for GetCrewList method."""
    
    @patch('aims_soap_client.Client')
    def test_get_crew_list_success(self, mock_client):
        """Test successful crew list retrieval."""
        # Setup mock
        mock_service = MagicMock()
        mock_service.GetCrewList.return_value = MagicMock(
            CrewMembers=[
                MagicMock(
                    CrewID="12345",
                    CrewFirstName="John",
                    CrewSurName="Doe",
                    Gender="M",
                    Base="SGN"
                )
            ]
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_crew_list()
        
        assert isinstance(result, list)
    
    @patch('aims_soap_client.Client')
    def test_get_crew_list_empty(self, mock_client):
        """Test empty crew list."""
        mock_service = MagicMock()
        mock_service.GetCrewList.return_value = MagicMock(CrewMembers=[])
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_crew_list()
        
        assert result == []
    
    @patch('aims_soap_client.Client')
    def test_get_crew_list_with_base_filter(self, mock_client):
        """Test crew list with base filter."""
        mock_service = MagicMock()
        mock_service.GetCrewList.return_value = MagicMock(CrewMembers=[])
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_crew_list(base="SGN")
        
        assert isinstance(result, list)


class TestGetCrewRoster:
    """Tests for GetCrewRoster method."""
    
    @patch('aims_soap_client.Client')
    def test_get_crew_roster_success(self, mock_client):
        """Test successful roster retrieval."""
        mock_service = MagicMock()
        mock_service.CrewMemberRosterDetailsForPeriod.return_value = MagicMock(
            RosterItems=[]
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        today = date.today()
        result = client.get_crew_roster(
            crew_id="12345",
            from_date=today,
            to_date=today + timedelta(days=7)
        )
        
        assert isinstance(result, list)
    
    @patch('aims_soap_client.Client')
    def test_get_crew_roster_invalid_dates(self, mock_client):
        """Test roster with invalid date range."""
        mock_client.return_value = MagicMock()
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        # End date before start date should handle gracefully
        today = date.today()
        result = client.get_crew_roster(
            crew_id="12345",
            from_date=today + timedelta(days=7),
            to_date=today
        )
        
        assert result == [] or isinstance(result, list)


class TestFetchDayFlights:
    """Tests for FetchDayFlights method."""
    
    @patch('aims_soap_client.Client')
    def test_fetch_day_flights_success(self, mock_client):
        """Test successful day flights retrieval."""
        mock_service = MagicMock()
        mock_service.FetchDayFlights.return_value = MagicMock(
            Flights=[
                MagicMock(
                    FlightNo="VN123",
                    Dep="SGN",
                    Arr="HAN",
                    Std="08:00",
                    Sta="10:00"
                )
            ]
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_day_flights(date.today())
        
        assert isinstance(result, list)
    
    @patch('aims_soap_client.Client')
    def test_fetch_day_flights_no_flights(self, mock_client):
        """Test day with no flights."""
        mock_service = MagicMock()
        mock_service.FetchDayFlights.return_value = MagicMock(Flights=[])
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_day_flights(date.today())
        
        assert result == []


class TestGetFlightsRange:
    """Tests for GetFlightsRange method."""
    
    @patch('aims_soap_client.Client')
    def test_get_flights_range(self, mock_client):
        """Test flights in date range."""
        mock_service = MagicMock()
        mock_service.FetchFlightsFrTo.return_value = MagicMock(Flights=[])
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        today = date.today()
        result = client.get_flights_range(
            from_date=today,
            to_date=today + timedelta(days=7)
        )
        
        assert isinstance(result, list)


class TestGetCrewQualifications:
    """Tests for crew qualifications."""
    
    @patch('aims_soap_client.Client')
    def test_get_crew_qualifications(self, mock_client):
        """Test getting crew qualifications."""
        mock_service = MagicMock()
        mock_service.FetchCrewQuals.return_value = MagicMock(
            CrewQuals=[]
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_crew_qualifications("12345")
        
        assert isinstance(result, list)


class TestGetAircraftList:
    """Tests for aircraft list."""
    
    @patch('aims_soap_client.Client')
    def test_get_aircraft_list(self, mock_client):
        """Test getting aircraft list."""
        mock_service = MagicMock()
        mock_service.FetchAircrafts.return_value = MagicMock(
            Aircrafts=[]
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_aircraft_list()
        
        assert isinstance(result, list)


class TestGetAirports:
    """Tests for airports list."""
    
    @patch('aims_soap_client.Client')
    def test_get_airports(self, mock_client):
        """Test getting airports."""
        mock_service = MagicMock()
        mock_service.FetchAirports.return_value = MagicMock(
            Airports=[]
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_airports()
        
        assert isinstance(result, list)


class TestErrorHandling:
    """Tests for error handling."""
    
    @patch('aims_soap_client.Client')
    def test_connection_timeout(self, mock_client):
        """Test connection timeout handling."""
        import socket
        mock_client.side_effect = socket.timeout("Connection timed out")
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        assert client.is_connected is False
    
    @patch('aims_soap_client.Client')
    def test_soap_fault(self, mock_client):
        """Test SOAP fault handling."""
        from zeep.exceptions import Fault
        
        mock_service = MagicMock()
        mock_service.GetCrewList.side_effect = Fault("Authentication failed")
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_crew_list()
        
        # Should return empty list on error
        assert result == []


class TestBulkOperations:
    """Tests for bulk operations."""
    
    @patch('aims_soap_client.Client')
    def test_get_bulk_crew_status(self, mock_client):
        """Test getting bulk crew status."""
        mock_service = MagicMock()
        mock_service.GetCrewList.return_value = MagicMock(CrewMembers=[])
        mock_service.CrewMemberRosterDetailsForPeriod.return_value = MagicMock(RosterItems=[])
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_bulk_crew_status(
            base="SGN",
            target_date=date.today()
        )
        
        assert isinstance(result, dict)
        assert "SBY" in result or result == {}


# =====================================================
# Run tests
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
