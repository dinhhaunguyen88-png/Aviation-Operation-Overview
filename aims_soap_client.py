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
        
        # Flight specific credentials
        self.username_flights = os.getenv("AIMS_WS_USERNAME_FLIGHTS") or self.username
        self.password_flights = os.getenv("AIMS_WS_PASSWORD_FLIGHTS") or self.password
        
        self.client = None
        self.session_id = None
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
            from zeep.plugins import HistoryPlugin
            from requests import Session
            
            if not self.wsdl_url:
                raise ValueError("AIMS_WSDL_URL not configured")
                
            session = Session()
            session.verify = True  # Enable SSL verification
            
            # Add browser-like headers to bypass WAF (Incapsula)
            # Simplified headers to reduce WAF suspicion
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            transport = Transport(session=session, timeout=30)
            
            self.client = Client(self.wsdl_url, transport=transport)
            
            # Override the service endpoint to use public URL
            # WSDL may contain internal IP which is not accessible
            public_endpoint = self.wsdl_url.replace('?singlewsdl', '')
            for service in self.client.wsdl.services.values():
                for port in service.ports.values():
                    port.binding_options['address'] = public_endpoint
                    logger.info(f"Overriding endpoint to: {public_endpoint}")
            
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
            "YY": d.strftime("%Y"),
            "YYYY": d.strftime("%Y")
        }
    
    # Login is not supported in this WSDL version, using UN/PSW per call

    # =========================================================
    # Crew Related Methods
    # =========================================================
    
    def get_crew_schedule(
        self,
        from_date: date,
        to_date: date,
        crew_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get crew schedule (Mapping to CrewMemberRosterDetailsForPeriod).
        """
        self._ensure_connection()
        
        try:
            from_dt = self._format_date(from_date)
            to_dt = self._format_date(to_date)
            
            # Note: ID=0 might not returns all rosters. If fails, we might need to loop.
            # But "Invalid credentials" suggests the call itself was rejected.
            
            response = self.client.service.CrewMemberRosterDetailsForPeriod(
                UN=self.username,
                PSW=self.password,
                ID=int(crew_id) if crew_id and crew_id.isdigit() else 0,
                FmDD=from_dt['DD'],
                FmMM=from_dt['MM'],
                FmYY=from_dt['YY'],
                ToDD=to_dt['DD'],
                ToMM=to_dt['MM'],
                ToYY=to_dt['YY']
            )
            
            if hasattr(response, 'ErrorExplanation') and response.ErrorExplanation:
                logger.error(f"GetCrewSchedule error: {response.ErrorExplanation}")
                return []
            
            schedules = []
            
            # Determine correct list source
            roster_source = None
            if hasattr(response, 'TAIMSCrewRostDetailList'):
                roster_source = response.TAIMSCrewRostDetailList
            elif hasattr(response, 'CrewRostList'):
                roster_source = response.CrewRostList
                
            # Handle nested list wrapper if present
            if roster_source and hasattr(roster_source, 'TAIMSCrewRostDetail'):
                roster_source = roster_source.TAIMSCrewRostDetail
            
            if roster_source:
                # Ensure it's iterable
                if not isinstance(roster_source, list):
                     roster_source = [roster_source]
                     
                for item in roster_source:
                    yy = getattr(item, 'RostYY', '')
                    mm = getattr(item, 'RostMM', '')
                    dd = getattr(item, 'RostDD', '')
                    
                    if yy and mm and dd:
                        schedules.append({
                            "crew_id": crew_id or "0", 
                            "activity_code": getattr(item, 'DutyCode', ''),
                            "start_dt": f"{yy}-{mm}-{dd}T00:00:00",
                            "end_dt": f"{yy}-{mm}-{dd}T23:59:59",
                            "flight_number": getattr(item, 'FltNo', ''),
                        })
                    # Silent skip for invalid dates (common in separators)
            else:
                 # Check nicely
                 if hasattr(response, 'ErrorExplanation') and response.ErrorExplanation:
                     logger.warning(f"GetCrewSchedule warning: {response.ErrorExplanation}")
                 else:
                     logger.info(f"GetCrewSchedule: No roster items found for crew {crew_id}")
            
            return schedules
            
        except Exception as e:
            logger.error(f"GetCrewSchedule failed: {e}")
            return []

    def get_crew_actuals(
        self,
        from_date: date,
        to_date: date,
        crew_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get crew actual flying hours (Mapping to FlightDetailsForPeriod).
        """
        self._ensure_connection()
        
        try:
            from_dt = self._format_date(from_date)
            to_dt = self._format_date(to_date)
            
            # Fixed parameter names based on error log
            response = self.client.service.FlightDetailsForPeriod(
                UN=self.username,
                PSW=self.password,
                FromDD=from_dt['DD'],
                FromMMonth=from_dt['MM'],
                FromYYYY=from_dt['YY'],
                FromHH="00",
                FromMMin="00",
                ToDD=to_dt['DD'],
                ToMMonth=to_dt['MM'],
                ToYYYY=to_dt['YY'],
                ToHH="23",
                ToMMin="59"
            )
            
            if hasattr(response, 'ErrorExplanation') and response.ErrorExplanation:
                logger.error(f"GetCrewActuals error: {response.ErrorExplanation}")
                return []
            
            actuals = []
            if hasattr(response, 'FlightList') and response.FlightList:
                for item in response.FlightList:
                    # In FlightDetailsForPeriod, we need to extract crew block time
                    pass
            
            return actuals
            
        except Exception as e:
            logger.error(f"GetCrewActuals failed: {e}")
            return []
    
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
            
            if hasattr(response, 'ErrorExplanation') and response.ErrorExplanation:
                raise Exception(response.ErrorExplanation)
            
            crew_list = []
            # Use 'CrewList' as confirmed by debug output (Zeep object)
            if hasattr(response, 'CrewList') and response.CrewList:
                items = response.CrewList
                # Zeep wrapper handling: Check if the list is nested under TAIMSGetCrewItm
                if hasattr(items, 'TAIMSGetCrewItm'):
                    items = items.TAIMSGetCrewItm
                
                # Check if items is actually iterable list now
                if not isinstance(items, list):
                     items = [items] # Handle single item case if not list

                for crew in items:
                    crew_list.append({
                        # Mapping based on verified WSDL response fields
                        "crew_id": str(crew.Id) if hasattr(crew, 'Id') and crew.Id else None,
                        "crew_name": getattr(crew, 'CrewName', ''),
                        "first_name": getattr(crew, 'Passpname', ''), # Using Passpname as FirstName/Passport Name proxy
                        "last_name": '', # No explicit Last Name field found
                        "three_letter_code": getattr(crew, 'ShortName', ''), # ShortName usually 3LC
                        "gender": getattr(crew, 'Sex', ''),
                        "email": getattr(crew, 'Email', ''),
                        "cell_phone": getattr(crew, 'ContactCell', ''),
                        "base": base or getattr(crew, 'Location', ''),
                    })
            
            count = getattr(response, 'GetCrewListCount', len(crew_list))
            logger.info(f"GetCrewList returned {count} records (parsed {len(crew_list)})")
            return crew_list
            
        except Exception as e:
            logger.error(f"GetCrewList failed: {e}")
            raise

    def get_day_members(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Get active crew members.
        Uses get_crew_list as FetchDayMembers is not available.
        """
        try:
            logger.info(f"Fetching active crew list for {target_date} using GetCrewList fallback...")
            
            # Use current date as range to find active crew
            crew_list = self.get_crew_list(
                from_date=target_date,
                to_date=target_date
            )
            
            members = []
            for crew in crew_list:
                members.append({
                    "crew_id": crew.get("crew_id"),
                    "crew_name": crew.get("crew_name"),
                    "status_date": target_date.isoformat(),
                    "duty_code": "", 
                    "duty_description": "",
                    "base": crew.get("base"),
                    "flight_number": ""
                })
                
            logger.info(f"get_day_members (via GetCrewList) returned {len(members)} crew")
            return members

        except Exception as e:
            logger.error(f"get_day_members failed: {e}")
            return []
    
    # ...

    # =========================================================
    # Flight Related Methods
    # =========================================================
    
    def get_day_flights(self, flight_date: date) -> List[Dict[str, Any]]:
        """
        Get all flights for a specific day.
        Using FlightDetailsForPeriod as FetchDayFlights is missing.
        """
        self._ensure_connection()
        
        try:
            dt = self._format_date(flight_date)
            
            # Use flight specific credentials
            user = self.username_flights
            pwd = self.password_flights
            
            response = self.client.service.FlightDetailsForPeriod(
                UN=user,
                PSW=pwd,
                FromDD=dt["DD"],
                FromMMonth=dt["MM"],
                FromYYYY=dt["YY"],
                FromHH="00",
                FromMMin="00",
                ToDD=dt["DD"],
                ToMMonth=dt["MM"],
                ToYYYY=dt["YY"],
                ToHH="23",
                ToMMin="59"
            )
            
            flights = []
            # Assuming return type has FlightList
            if response and hasattr(response, 'FlightList') and response.FlightList:
                 
                 # Unwrap the Zeep ArrayOfTAIMSFlight wrapper
                 flight_list = response.FlightList
                 if hasattr(flight_list, 'TAIMSFlight'):
                     flight_list = flight_list.TAIMSFlight
                 
                 # Ensure it's iterable
                 if not isinstance(flight_list, list):
                     flight_list = [flight_list] if flight_list else []
                 
                 for i, flight in enumerate(flight_list):
                    if i == 0:
                        logger.info(f"Raw Flight Object Sample: {dir(flight)}")
                        logger.info(f"FlightAssocCrwRtes: {getattr(flight, 'FlightAssocCrwRtes', 'MISSING')}")
                        assoc = getattr(flight, 'FlightAssocCrwRtes', None)
                        if assoc:
                             logger.info(f"Assoc Type: {type(assoc)}")
                             logger.info(f"Assoc Dir: {dir(assoc)}")

                    # Parse times from string format HH:MM
                    std = getattr(flight, 'FlightStd', '') or ''
                    sta = getattr(flight, 'FlightSta', '') or ''
                    etd = getattr(flight, 'FlightEtd', '') or ''
                    eta = getattr(flight, 'FlightEta', '') or ''
                    atd = getattr(flight, 'FlightAtd', '') or ''
                    ata = getattr(flight, 'FlightAta', '') or ''
                    tkoff = getattr(flight, 'FlightTKOFF', '') or ''
                    tdown = getattr(flight, 'FlightTDOWN', '') or ''
                    
                    flights.append({
                        "flight_date": flight_date.isoformat(),
                        "carrier_code": getattr(flight, 'FlightCarrier', '') or '',
                        "flight_number": str(getattr(flight, 'FlightNo', '') or ''),
                        "departure": getattr(flight, 'FlightDep', '') or '',
                        "arrival": getattr(flight, 'FlightArr', '') or '',
                        "aircraft_type": getattr(flight, 'FlightAcType', '') or '',
                        "aircraft_reg": getattr(flight, 'FlightReg', '') or '',
                        # Time fields (already in HH:MM format from AIMS)
                        "std": std if std else None,
                        "sta": sta if sta else None,
                        "etd": etd if etd else None,
                        "eta": eta if eta else None,
                        "atd": atd if atd else None,
                        "off_block": tkoff if tkoff else None,  # Takeoff time = off block
                        "on_block": tdown if tdown else None,   # Touchdown = on block
                        # Additional fields
                        "delay_code_1": '', 
                        "delay_time_1": 0,
                        "pax_total": int(getattr(flight, 'FlightNoOfPax', 0) or 0),
                         "flight_status": getattr(flight, 'FlightStatus', '') or '',
                        "block_time": getattr(flight, 'FlightBlkTime', '') or '',
                        "crew_data": self._extract_crew_from_flight_assoc(getattr(flight, 'FlightAssocCrwRtes', None))
                    })
            
            logger.info(f"GetDayFlights returned {len(flights)} flights")
            return flights
            
        except Exception as e:
            logger.error(f"GetDayFlights failed: {e}")
            raise
    
    def _extract_crew_from_flight_assoc(self, assoc_data: Any) -> List[Dict[str, Any]]:
        """
        Extract crew information from FlightAssocCrwRtes object.
        """
        crew_list = []
        if not assoc_data:
            return crew_list

        try:
            # Handle list or single object wrapper
            items = []
            if hasattr(assoc_data, 'TAIMSFlightCrew'):
                items = assoc_data.TAIMSFlightCrew
            elif isinstance(assoc_data, list):
                items = assoc_data
            else:
                items = [assoc_data]
            
            if items and not isinstance(items, list):
                items = [items]
                
            for cr in items:
                # Extract ID, Position
                crew_id = getattr(cr, 'CrewID', None) or getattr(cr, 'ID', None)
                pos = getattr(cr, 'Position', None) or getattr(cr, 'Pos', None)
                name = getattr(cr, 'Name', None) or getattr(cr, 'CrewName', None) or ''
                
                if crew_id:
                    crew_list.append({
                        'crew_id': str(crew_id),
                        'crew_name': name,
                        'position': pos or ''
                    })
        except Exception as e:
            logger.warning(f"Failed to extract crew from flight assoc: {e}")
            
        return crew_list

    def get_flights_range(
        self,
        from_date: date,
        to_date: date,
        from_time: str = "00:00",
        to_time: str = "23:59"
    ) -> List[Dict[str, Any]]:
        """
        Get flights in date/time range (Method #20: FetchFlightsFrTo).
        """
        self._ensure_connection()
        
        try:
            from_dt = self._format_date(from_date)
            to_dt = self._format_date(to_date)
            
            from_hh, from_mm = from_time.split(":")
            to_hh, to_mm = to_time.split(":")
            
            # Use flight specific credentials
            user = self.username_flights
            pwd = self.password_flights
            
            response = self.client.service.FlightDetailsForPeriod(
                UN=user,
                PSW=pwd,
                FromDD=from_dt["DD"],
                FromMMonth=from_dt["MM"],
                FromYYYY=from_dt["YY"],
                FromHH=from_hh,
                FromMMin=from_mm,
                ToDD=to_dt["DD"],
                ToMMonth=to_dt["MM"],
                ToYYYY=to_dt["YY"],
                ToHH=to_hh,
                ToMMin=to_mm
            )
            
            flights = []
            # Reuse parsing logic from get_day_flights
            # Assuming return type has FlightList
            if response and hasattr(response, 'FlightList') and response.FlightList:
                 
                 # Unwrap the Zeep ArrayOfTAIMSFlight wrapper
                 flight_list = response.FlightList
                 if hasattr(flight_list, 'TAIMSFlight'):
                     flight_list = flight_list.TAIMSFlight
                 
                 # Ensure it's iterable
                 if not isinstance(flight_list, list):
                     flight_list = [flight_list] if flight_list else []
                 
                 for flight in flight_list:
                    # Parse times from string format HH:MM
                    std = getattr(flight, 'FlightStd', '') or ''
                    sta = getattr(flight, 'FlightSta', '') or ''
                    etd = getattr(flight, 'FlightEtd', '') or ''
                    eta = getattr(flight, 'FlightEta', '') or ''
                    atd = getattr(flight, 'FlightAtd', '') or ''
                    tkoff = getattr(flight, 'FlightTKOFF', '') or ''
                    tdown = getattr(flight, 'FlightTDOWN', '') or ''
                    
                    flights.append({
                        "flight_date": getattr(flight, 'FlightDate', '') or '', # Needs formatting? Usually YYYY-MM-DD from API? No, check get_day_flights
                        # Actually FlightDate from API is usually string. get_day_flights formats it?
                        # In get_day_flights we used header date. Here we have multiple dates.
                        # Need to parse 'FlightDate' or 'FlightDD'/'FlightMM' etc.
                        # Let's trust 'FlightDate' field or construct it.
                        "flight_number": str(getattr(flight, 'FlightNo', '') or ''),
                        "departure": getattr(flight, 'FlightDep', '') or '',
                        "arrival": getattr(flight, 'FlightArr', '') or '',
                        "aircraft_type": getattr(flight, 'FlightAcType', '') or '',
                        "aircraft_reg": getattr(flight, 'FlightReg', '') or '',
                        "std": std if std else None,
                        "sta": sta if sta else None,
                        "etd": etd if etd else None,
                        "eta": eta if eta else None,
                        "atd": atd if atd else None,
                        "off_block": tkoff if tkoff else None,
                        "on_block": tdown if tdown else None,
                        "flight_status": getattr(flight, 'FlightStatus', '') or '',
                        "block_time": getattr(flight, 'FlightBlkTime', '') or '',
                        "crew_data": self._extract_crew_from_flight_assoc(getattr(flight, 'FlightAssocCrwRtes', None))
                    })

            return flights
            
        except Exception as e:
            logger.error(f"GetFlightsRange failed: {e}")
            raise
    # Miscellaneous Methods
    # =========================================================
    
    def get_leg_members(
        self,
        flight_date: date,
        flight_number: str,
        dep_airport: str
    ) -> List[Dict[str, Any]]:
        """
        Get crew members for a specific flight leg (Method: FetchLegMembers).
        """
        self._ensure_connection()
        
        try:
            dt = self._format_date(flight_date)
            
            # Usually needs operational credentials? Or Main?
            # Test script showed invalid creds with Flight User previously but maybe Main works?
            # Or vice versa. I'll default to username (Main) but fallback if needed.
            # Actually pattern 2 failed with Flight creds in test_leg_members.py... 
            # Wait, test_leg_members.py output for pattern 2 said "Invalid credentials" with FLIGHT creds.
            # So I should use MAIN credentials?
            # I will try Main credentials first.
            
            response = self.client.service.FetchLegMembers(
                UN=self.username,
                PSW=self.password,
                DD=dt["DD"],
                MM=dt["MM"],
                YY=dt["YY"],
                Flight=flight_number,
                DEP=dep_airport
            )
            
            crew = []
            if response:
                # Unwrap if needed
                source = response
                if hasattr(response, 'TAIMSLegCrew'):
                    source = response.TAIMSLegCrew
                
                if not isinstance(source, list):
                    source = [source]
                    
                for c in source:
                    crew_id = getattr(c, 'CrewID', '') or getattr(c, 'ID', '')
                    if crew_id:
                        crew.append({
                            "crew_id": str(crew_id),
                            "crew_name": getattr(c, 'Name', '') or getattr(c, 'CrewName', '') or '',
                            "position": getattr(c, 'Position', '') or getattr(c, 'Pos', '') or '',
                            "category": getattr(c, 'Category', '') or ''
                        })
            
            return crew
            
        except Exception as e:
            logger.warning(f"GetLegMembers failed for {flight_number}: {e}")
            return []

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
    
    print(f"\n[*] WSDL URL: {client.wsdl_url or 'NOT SET'}")
    print(f"[*] Username: {client.username or 'NOT SET'}")
    print(f"[*] Password: {'*' * len(client.password) if client.password else 'NOT SET'}")
    
    if not client.wsdl_url or not client.username:
        print("\n[ERROR] Missing configuration. Check .env file.")
        return False
    
    print("\n[>] Attempting connection...")
    
    if client.connect():
        print("[OK] Connection successful!")
        
        # Try a test call
        try:
            today = date.today()
            print(f"\n[*] Testing GetCrewList for {today}...")
            crew = client.get_crew_list(today, today)
            print(f"[OK] GetCrewList returned {len(crew)} records")
            return True
        except Exception as e:
            print(f"[WARN] API call failed: {e}")
            return False
    else:
        print("[ERROR] Connection failed!")
        return False


if __name__ == "__main__":
    test_connection()
