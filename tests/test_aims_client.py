"""
Unit Tests - AIMS SOAP Client
Phase 5: Testing & Deployment

Tests for aims_soap_client.py - Updated to match actual API signatures.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from aims_soap_client import AIMSSoapClient


class TestAIMSSoapClientInit:
    """Tests for AIMSSoapClient initialization."""
    
    @patch('zeep.Client')
    def test_init_with_valid_credentials(self, mock_client):
        """Test initialization with valid credentials."""
        mock_client.return_value = MagicMock()
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        assert client is not None
        assert client.wsdl_url == "http://example.com/wsdl"
        assert client.username == "testuser"
        assert client.password == "testpass"
    
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
    
    @patch('zeep.Client')
    def test_is_connected_true(self, mock_client):
        """Test connection status when connected."""
        mock_client.return_value = MagicMock()
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        # Force connection via connect()
        client.connect()
        
        assert client.is_connected is True
    
    def test_is_connected_false(self):
        """Test connection status when not connected."""
        client = AIMSSoapClient(
            wsdl_url="http://invalid.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        assert client.is_connected is False


class TestGetCrewList:
    """Tests for get_crew_list method."""
    
    @patch('zeep.Client')
    def test_get_crew_list_success(self, mock_client):
        """Test successful crew list retrieval."""
        # Setup mock
        mock_service = MagicMock()
        mock_crew = MagicMock()
        mock_crew.Id = 12345
        mock_crew.CrewName = "John Doe"
        mock_crew.ShortName = "JDO"
        mock_response = MagicMock()
        mock_response.ErrorExplanation = None  # No error
        mock_response.CrewList = MagicMock()
        mock_response.CrewList.TAIMSGetCrewItm = [mock_crew]
        mock_response.GetCrewListCount = 1
        mock_service.GetCrewList.return_value = mock_response
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        # Force connection
        client.client = mock_client.return_value
        client._connected = True
        
        today = date.today()
        result = client.get_crew_list(
            from_date=today,
            to_date=today + timedelta(days=7)
        )
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["crew_id"] == "12345"
    
    @patch('zeep.Client')
    def test_get_crew_list_empty(self, mock_client):
        """Test empty crew list."""
        mock_service = MagicMock()
        mock_response = MagicMock()
        mock_response.ErrorExplanation = None
        mock_response.CrewList = None
        mock_response.GetCrewListCount = 0
        mock_service.GetCrewList.return_value = mock_response
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        client.client = mock_client.return_value
        client._connected = True
        
        today = date.today()
        result = client.get_crew_list(
            from_date=today,
            to_date=today + timedelta(days=7)
        )
        
        assert result == []
    
    @patch('zeep.Client')
    def test_get_crew_list_with_base_filter(self, mock_client):
        """Test crew list with base filter."""
        mock_service = MagicMock()
        mock_response = MagicMock()
        mock_response.ErrorExplanation = None
        mock_response.CrewList = None
        mock_response.GetCrewListCount = 0
        mock_service.GetCrewList.return_value = mock_response
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        client.client = mock_client.return_value
        client._connected = True
        
        today = date.today()
        result = client.get_crew_list(
            from_date=today,
            to_date=today + timedelta(days=7),
            base="SGN"
        )
        
        assert isinstance(result, list)


class TestGetCrewSchedule:
    """Tests for get_crew_schedule method (previously get_crew_roster)."""
    
    @patch('zeep.Client')
    def test_get_crew_schedule_success(self, mock_client):
        """Test successful schedule retrieval."""
        mock_service = MagicMock()
        mock_service.CrewMemberRosterDetailsForPeriod.return_value = MagicMock(
            RosterItems=None
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        today = date.today()
        result = client.get_crew_schedule(
            from_date=today,
            to_date=today + timedelta(days=7),
            crew_id="12345"
        )
        
        assert isinstance(result, list)
    
    @patch('zeep.Client')
    def test_get_crew_schedule_invalid_dates(self, mock_client):
        """Test schedule with invalid date range."""
        mock_client.return_value = MagicMock()
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        # End date before start date should handle gracefully
        today = date.today()
        result = client.get_crew_schedule(
            from_date=today + timedelta(days=7),
            to_date=today,
            crew_id="12345"
        )
        
        # Should return empty or handle gracefully
        assert isinstance(result, list)


class TestGetDayFlights:
    """Tests for get_day_flights method."""
    
    @patch('zeep.Client')
    def test_get_day_flights_success(self, mock_client):
        """Test successful day flights retrieval."""
        mock_service = MagicMock()
        mock_flight = MagicMock()
        mock_flight.FlightNo = "VN123"
        mock_flight.FlightCarrier = "VN"
        mock_flight.FlightDep = "SGN"
        mock_flight.FlightArr = "HAN"
        mock_service.FlightDetailsForPeriod.return_value = MagicMock(
            FlightList=MagicMock(TAIMSFlight=[mock_flight])
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_day_flights(date.today())
        
        assert isinstance(result, list)
    
    @patch('zeep.Client')
    def test_get_day_flights_no_flights(self, mock_client):
        """Test day with no flights."""
        mock_service = MagicMock()
        mock_service.FlightDetailsForPeriod.return_value = MagicMock(
            FlightList=None
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_day_flights(date.today())
        
        assert result == []


class TestGetFlightsRange:
    """Tests for get_flights_range method."""
    
    @patch('zeep.Client')
    def test_get_flights_range(self, mock_client):
        """Test flights in date range."""
        mock_service = MagicMock()
        # Return a list directly since get_flights_range returns response or []
        mock_service.FetchFlightsFrTo.return_value = []
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        client.client = mock_client.return_value
        client._connected = True
        
        today = date.today()
        result = client.get_flights_range(
            from_date=today,
            to_date=today + timedelta(days=7)
        )
        
        assert isinstance(result, list)


class TestGetAircraftList:
    """Tests for aircraft list."""
    
    @patch('zeep.Client')
    def test_get_aircraft_list(self, mock_client):
        """Test getting aircraft list."""
        mock_service = MagicMock()
        mock_service.FetchAircrafts.return_value = MagicMock(
            Aircrafts=None
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
    
    @patch('zeep.Client')
    def test_get_airports(self, mock_client):
        """Test getting airports."""
        mock_service = MagicMock()
        mock_service.FetchAirports.return_value = MagicMock(
            Airports=None
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_airports()
        
        assert isinstance(result, list)


class TestGetDayMembers:
    """Tests for get_day_members method."""
    
    @patch('zeep.Client')
    def test_get_day_members_success(self, mock_client):
        """Test getting day members."""
        mock_service = MagicMock()
        mock_service.FetchDayMembers.return_value = MagicMock(
            DayMembers=None
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        result = client.get_day_members(date.today())
        
        assert isinstance(result, list)


class TestErrorHandling:
    """Tests for error handling."""
    
    @patch('zeep.Client')
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
    
    @patch('zeep.Client')
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
        client.client = mock_client.return_value
        client._connected = True
        
        today = date.today()
        
        # Method raises exception, verify it's properly propagated
        with pytest.raises(Exception):
            client.get_crew_list(
                from_date=today,
                to_date=today + timedelta(days=7)
            )


class TestGetCrewActuals:
    """Tests for get_crew_actuals method."""
    
    @patch('zeep.Client')
    def test_get_crew_actuals_success(self, mock_client):
        """Test getting crew actual flying hours."""
        mock_service = MagicMock()
        mock_service.FlightDetailsForPeriod.return_value = MagicMock(
            FlightList=None
        )
        mock_client.return_value.service = mock_service
        
        client = AIMSSoapClient(
            wsdl_url="http://example.com/wsdl",
            username="testuser",
            password="testpass"
        )
        
        today = date.today()
        result = client.get_crew_actuals(
            from_date=today - timedelta(days=28),
            to_date=today
        )
        
        assert isinstance(result, list)


# =====================================================
# Run tests
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
