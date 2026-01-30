"""
AIMS SOAP Web Service Client
Phase 1: Foundation Setup

Provides interface to AIMS Web Service for crew and flight data.
Based on AIMS IT Guide Section 4 - SOAP/WSDL API.
"""

import os
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class AIMSSoapClient:
    """
    Client for AIMS SOAP Web Service.
    
    Requires zeep library for SOAP communication.
    Credentials must be configured in AIMS Option 7.1.
    """
    
    def __init__(
        self,
        wsdl_url: str = None,
        username: str = None,
        password: str = None
    ):
        """
        Initialize AIMS SOAP client.
        
        Args:
            wsdl_url: AIMS WSDL endpoint URL
            username: Web service username
            password: Web service password
        """
        self.wsdl_url = wsdl_url or os.getenv("AIMS_WSDL_URL")
        self.username = username or os.getenv("AIMS_WS_USERNAME")
        self.password = password or os.getenv("AIMS_WS_PASSWORD")
        
        self.client = None
        self._connected = False
        
    def connect(self) -> bool:
        """
        Establish connection to AIMS Web Service.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            from zeep import Client
            from zeep.transports import Transport
            from requests import Session
            
            if not self.wsdl_url:
                raise ValueError("AIMS_WSDL_URL not configured")
                
            session = Session()
            session.verify = True  # Enable SSL verification
            transport = Transport(session=session, timeout=30)
            
            self.client = Client(self.wsdl_url, transport=transport)
            self._connected = True
            logger.info("Connected to AIMS Web Service")
            return True
            
        except ImportError:
            logger.error("zeep library not installed. Run: pip install zeep")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to AIMS: {e}")
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self.client is not None
    
    def _ensure_connection(self):
        """Ensure client is connected before making calls."""
        if not self.is_connected:
            if not self.connect():
                raise ConnectionError("Unable to connect to AIMS Web Service")
    
    @staticmethod
    def _format_date(d: date) -> Dict[str, str]:
        """Format date for AIMS API (DD, MM, YY/YYYY components)."""
        return {
            "DD": d.strftime("%d"),
            "MM": d.strftime("%m"),
            "YY": d.strftime("%Y")
        }
    
    # =========================================================
    # Crew Related Methods
    # =========================================================
    
    def get_crew_list(
        self,
        from_date: date,
        to_date: date,
        crew_id: int = 0,
        base: str = "",
        aircraft_type: str = "",
        position: str = "",
        primary_qualify: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get crew list with qualifications (Method #12: GetCrewList).
        
        Args:
            from_date: Start date for qualification period
            to_date: End date for qualification period
            crew_id: Specific crew ID (0 = all crew)
            base: Filter by base code
            aircraft_type: Filter by aircraft type
            position: Filter by position (PIC, FO, etc.)
            primary_qualify: True for primary qualifications only
            
        Returns:
            List of crew members with their details.
        """
        self._ensure_connection()
        
        try:
            from_dt = self._format_date(from_date)
            to_dt = self._format_date(to_date)
            
            response = self.client.service.GetCrewList(
                UN=self.username,
                PSW=self.password,
                ID=crew_id,
                PrimaryQualify=primary_qualify,
                FmDD=from_dt["DD"],
                FmMM=from_dt["MM"],
                FmYY=from_dt["YY"],
                ToDD=to_dt["DD"],
                ToMM=to_dt["MM"],
                ToYY=to_dt["YY"],
                BaseStr=base,
                ACStr=aircraft_type,
                PosStr=position
            )
            
            if response.ErrorExplanation:
                raise Exception(response.ErrorExplanation)
            
            # Convert SOAP response to dict list
            crew_list = []
            if response.GetCrewList:
                for crew in response.GetCrewList:
                    crew_list.append({
                        "crew_id": str(crew.CrewID) if crew.CrewID else None,
                        "crew_name": crew.CrewName,
                        "first_name": crew.FirstName,
                        "last_name": crew.LastName,
                        "three_letter_code": crew.Crew3LC,
                        "gender": crew.Gender,
                        "email": crew.Email,
                        "cell_phone": crew.CellPhone,
                        "base": base,
                    })
            
            logger.info(f"GetCrewList returned {len(crew_list)} records")
            return crew_list
            
        except Exception as e:
            logger.error(f"GetCrewList failed: {e}")
            raise
    
    def get_crew_roster(
        self,
        crew_id: int,
        from_date: date,
        to_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get crew roster details (Method #13: CrewMemberRosterDetailsForPeriod).
        
        Args:
            crew_id: Crew member ID
            from_date: Period start date
            to_date: Period end date
            
        Returns:
            List of roster items for the crew member.
        """
        self._ensure_connection()
        
        try:
            from_dt = self._format_date(from_date)
            to_dt = self._format_date(to_date)
            
            response = self.client.service.CrewMemberRosterDetailsForPeriod(
                UN=self.username,
                PSW=self.password,
                ID=crew_id,
                FmDD=from_dt["DD"],
                FmMM=from_dt["MM"],
                FmYY=from_dt["YY"],
                ToDD=to_dt["DD"],
                ToMM=to_dt["MM"],
                ToYY=to_dt["YY"]
            )
            
            if response.ErrorExplanation:
                raise Exception(response.ErrorExplanation)
            
            roster = []
            if response.CrewRostList:
                for item in response.CrewRostList:
                    roster.append({
                        "duty_date": f"{item.RostDD}/{item.RostMM}/{item.RostYY}",
                        "duty_code": item.DutyCode,
                        "flight_number": item.FltNo,
                        "departure": item.Dep,
                        "arrival": item.Arr,
                        "aircraft_type": item.ACType,
                        "aircraft_reg": item.ACReg,
                    })
            
            logger.info(f"GetCrewRoster for {crew_id} returned {len(roster)} items")
            return roster
            
        except Exception as e:
            logger.error(f"GetCrewRoster failed: {e}")
            raise
    
    def get_crew_qualifications(
        self,
        from_date: date,
        to_date: date,
        crew_id: int = 0,
        primary_qualify: bool = True,
        get_all_in_period: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get crew qualifications (Method #14: FetchCrewQuals).
        
        Args:
            from_date: Period start date
            to_date: Period end date
            crew_id: Specific crew ID (0 = all crew)
            primary_qualify: True for primary qualifications
            get_all_in_period: Get all quals in period
            
        Returns:
            List of crew with their qualifications.
        """
        self._ensure_connection()
        
        try:
            from_dt = self._format_date(from_date)
            to_dt = self._format_date(to_date)
            
            response = self.client.service.FetchCrewQuals(
                UN=self.username,
                PSW=self.password,
                FmDD=from_dt["DD"],
                FmMM=from_dt["MM"],
                FmYYYY=from_dt["YY"],
                ToDD=to_dt["DD"],
                ToMM=to_dt["MM"],
                ToYYYY=to_dt["YY"],
                CrewID=crew_id,
                PrimaryQualify=primary_qualify,
                GetAllQualsInPeriod=get_all_in_period
            )
            
            if response.ErrorExplanation:
                raise Exception(response.ErrorExplanation)
            
            return response.CrewQualList or []
            
        except Exception as e:
            logger.error(f"GetCrewQualifications failed: {e}")
            raise
    
    # =========================================================
    # Flight Related Methods
    # =========================================================
    
    def get_day_flights(self, flight_date: date) -> List[Dict[str, Any]]:
        """
        Get all flights for a specific day (Method #19: FetchDayFlights).
        
        Args:
            flight_date: Date to fetch flights for
            
        Returns:
            List of flights for the day.
        """
        self._ensure_connection()
        
        try:
            dt = self._format_date(flight_date)
            
            response = self.client.service.FetchDayFlights(
                UN=self.username,
                PSW=self.password,
                DD=dt["DD"],
                MM=dt["MM"],
                YY=dt["YY"]
            )
            
            flights = []
            if response and hasattr(response, 'FlightList'):
                for flight in response.FlightList:
                    flights.append({
                        "flight_date": flight_date.isoformat(),
                        "carrier_code": flight.CarrCode,
                        "flight_number": flight.FltNo,
                        "departure": flight.Dep,
                        "arrival": flight.Arr,
                        "aircraft_type": flight.ACType,
                        "aircraft_reg": flight.ACReg,
                    })
            
            logger.info(f"GetDayFlights returned {len(flights)} flights")
            return flights
            
        except Exception as e:
            logger.error(f"GetDayFlights failed: {e}")
            raise
    
    def get_flights_range(
        self,
        from_date: date,
        to_date: date,
        from_time: str = "00:00",
        to_time: str = "23:59"
    ) -> List[Dict[str, Any]]:
        """
        Get flights in date/time range (Method #20: FetchFlightsFrTo).
        
        Args:
            from_date: Start date
            to_date: End date
            from_time: Start time (HH:MM)
            to_time: End time (HH:MM)
            
        Returns:
            List of flights in the range.
        """
        self._ensure_connection()
        
        try:
            from_dt = self._format_date(from_date)
            to_dt = self._format_date(to_date)
            
            from_hh, from_mm = from_time.split(":")
            to_hh, to_mm = to_time.split(":")
            
            response = self.client.service.FetchFlightsFrTo(
                UN=self.username,
                PSW=self.password,
                FmDD=from_dt["DD"],
                FmMM=from_dt["MM"],
                FmYY=from_dt["YY"],
                FmHH=from_hh,
                FmMins=from_mm,
                ToDD=to_dt["DD"],
                ToMM=to_dt["MM"],
                ToYY=to_dt["YY"],
                ToHH=to_hh,
                ToMins=to_mm
            )
            
            return response or []
            
        except Exception as e:
            logger.error(f"GetFlightsRange failed: {e}")
            raise
    
    # =========================================================
    # Miscellaneous Methods
    # =========================================================
    
    def get_aircraft_list(self) -> List[Dict[str, Any]]:
        """
        Get list of aircraft (Method #27: FetchAircrafts).
        
        Returns:
            List of aircraft with registration and type.
        """
        self._ensure_connection()
        
        try:
            response = self.client.service.FetchAircrafts(
                UN=self.username,
                PSW=self.password
            )
            
            aircraft = []
            if response:
                for ac in response:
                    aircraft.append({
                        "aircraft_type": ac.cAcType,
                        "aircraft_reg": ac.cACReg,
                        "country": ac.cACCountry,
                    })
            
            return aircraft
            
        except Exception as e:
            logger.error(f"GetAircraftList failed: {e}")
            raise
    
    def get_airports(self) -> List[Dict[str, Any]]:
        """
        Get list of airports (Method #30: FetchAirports).
        
        Returns:
            List of airports with codes and details.
        """
        self._ensure_connection()
        
        try:
            response = self.client.service.FetchAirports(
                UN=self.username,
                PSW=self.password
            )
            
            airports = []
            if response:
                for ap in response:
                    airports.append({
                        "airport_code": ap.cAirportCode,
                        "airport_name": ap.cAirportName,
                        "country_code": ap.cCountryCode,
                        "latitude": ap.cLatitude,
                        "longitude": ap.cLongtitude,
                    })
            
            return airports
            
        except Exception as e:
            logger.error(f"GetAirports failed: {e}")
            raise


# =========================================================
# Test Connection Script
# =========================================================

def test_connection():
    """Test AIMS connection and print results."""
    print("="*60)
    print("AIMS SOAP Web Service - Connection Test")
    print("="*60)
    
    client = AIMSSoapClient()
    
    print(f"\n📡 WSDL URL: {client.wsdl_url or 'NOT SET'}")
    print(f"👤 Username: {client.username or 'NOT SET'}")
    print(f"🔑 Password: {'*' * len(client.password) if client.password else 'NOT SET'}")
    
    if not client.wsdl_url or not client.username:
        print("\n❌ Missing configuration. Check .env file.")
        return False
    
    print("\n🔌 Attempting connection...")
    
    if client.connect():
        print("✅ Connection successful!")
        
        # Try a test call
        try:
            today = date.today()
            print(f"\n📋 Testing GetCrewList for {today}...")
            crew = client.get_crew_list(today, today)
            print(f"✅ GetCrewList returned {len(crew)} records")
            return True
        except Exception as e:
            print(f"⚠️  API call failed: {e}")
            return False
    else:
        print("❌ Connection failed!")
        return False


if __name__ == "__main__":
    test_connection()
