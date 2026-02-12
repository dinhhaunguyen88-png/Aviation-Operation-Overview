"""
AIMS ETL Manager
Handles data synchronization from AIMS SOAP Web Service to Supabase.

Separates sync logic from API client for better maintainability.
Supports:
- Reference Data Sync (Aircraft, Airports, Countries) - Weekly
- Operational Data Sync (Flights, Crew) - Every 5 mins
- Full Sync - On Demand
"""

import os
import logging
import time
import threading
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Lazy import for swap detector (avoid circular import at module level)
_swap_detector = None
def _get_swap_detector():
    global _swap_detector
    if _swap_detector is None:
        import swap_detector as sd
        _swap_detector = sd
    return _swap_detector


class AIMSETLManager:
    """
    ETL Manager for AIMS data synchronization.
    
    Responsibilities:
    - Coordinate data fetching from AIMS
    - Transform data to match database schema
    - Upsert data into Supabase tables
    - Track sync job status
    """
    
    def __init__(self, aims_client=None, supabase_client=None):
        """
        Initialize ETL Manager.
        
        Args:
            aims_client: AIMSSoapClient instance (will create if not provided)
            supabase_client: Supabase client instance (will create if not provided)
        """
        # Lazy import to avoid circular dependencies
        if aims_client is None:
            from aims_soap_client import AIMSSoapClient
            self.aims = AIMSSoapClient()
        else:
            self.aims = aims_client
            
        if supabase_client is None:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                self.supabase = create_client(url, key)
            else:
                self.supabase = None
                logger.warning("Supabase credentials not found")
        else:
            self.supabase = supabase_client
            
        self.current_job_id = None
        
        # Rate Limiting Configuration
        self.max_concurrent = int(os.getenv("AIMS_MAX_CONCURRENT_REQUESTS", "5"))
        self.request_delay = float(os.getenv("AIMS_REQUEST_DELAY", "0.5"))
        self.semaphore = threading.Semaphore(self.max_concurrent)
        
        logger.info(f"ETL Manager initialized (Throttle: {self.max_concurrent} concurrent, {self.request_delay}s delay)")
    
    def _throttled_call(self, func, *args, **kwargs):
        """Execute a function while respecting concurrency limits and delays."""
        with self.semaphore:
            if self.request_delay > 0:
                time.sleep(self.request_delay)
            return func(*args, **kwargs)
    
    # =========================================================
    # Job Tracking
    # =========================================================
    
    def _start_job(self, job_type: str) -> str:
        """Start a new sync job and return job ID."""
        job_id = f"{job_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.current_job_id = job_id
        
        if self.supabase:
            try:
                self.supabase.table("aims_sync_jobs").insert({
                    "job_id": job_id,
                    "job_type": job_type,
                    "status": "RUNNING",
                    "started_at": datetime.now().isoformat()
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log job start: {e}")
                
        logger.info(f"Started sync job: {job_id}")
        return job_id
    
    def _complete_job(self, job_id: str, records_processed: int = 0, error: str = None):
        """Mark a sync job as completed."""
        status = "FAILED" if error else "COMPLETED"
        
        if self.supabase:
            try:
                self.supabase.table("aims_sync_jobs").update({
                    "status": status,
                    "completed_at": datetime.now().isoformat(),
                    "records_processed": records_processed,
                    "error_message": error
                }).eq("job_id", job_id).execute()
            except Exception as e:
                logger.warning(f"Failed to log job completion: {e}")
                
        logger.info(f"Completed sync job: {job_id} - Status: {status}, Records: {records_processed}")
    
    # =========================================================
    # Reference Data Sync (Weekly)
    # =========================================================
    
    def sync_reference_data(self) -> Dict[str, int]:
        """
        Sync all reference data tables.
        Should be run weekly or on-demand.
        
        Returns:
            Dict with count of records synced per table.
        """
        job_id = self._start_job("REFERENCE")
        results = {}
        total_records = 0
        
        try:
            # Sync Aircraft
            count = self._sync_aircraft()
            results["aims_aircraft"] = count
            total_records += count
            
            # Sync Airports
            count = self._sync_airports()
            results["aims_airports"] = count
            total_records += count
            
            # Sync Countries
            count = self._sync_countries()
            results["aims_countries"] = count
            total_records += count
            
            self._complete_job(job_id, total_records)
            
        except Exception as e:
            logger.error(f"Reference data sync failed: {e}")
            self._complete_job(job_id, total_records, str(e))
            
        return results
    
    def _sync_aircraft(self) -> int:
        """Sync aircraft list from FetchAircraft."""
        logger.info("Syncing aircraft...")
        
        try:
            aircraft_list = self._throttled_call(self.aims.get_aircraft_list)
            
            if not aircraft_list:
                logger.warning("No aircraft returned from AIMS")
                return 0
                
            # Transform to DB schema
            records = []
            for ac in aircraft_list:
                records.append({
                    "aircraft_reg": ac.get("aircraft_reg"),
                    "aircraft_type": ac.get("aircraft_type"),
                    "country": ac.get("country"),
                    "status": "ACTIVE",
                    "last_synced_at": datetime.now().isoformat()
                })
            
            # Upsert to DB
            if self.supabase and records:
                self.supabase.table("aims_aircraft").upsert(
                    records,
                    on_conflict="aircraft_reg"
                ).execute()
                
            logger.info(f"Synced {len(records)} aircraft")
            return len(records)
            
        except Exception as e:
            logger.error(f"Aircraft sync failed: {e}")
            return 0
    
    def _sync_airports(self) -> int:
        """Sync airports from FetchAirports."""
        logger.info("Syncing airports...")
        
        try:
            airports = self._throttled_call(self.aims.get_airports)
            
            if not airports:
                logger.warning("No airports returned from AIMS")
                return 0
                
            records = []
            for ap in airports:
                records.append({
                    "airport_code": ap.get("airport_code"),
                    "airport_name": ap.get("airport_name"),
                    "country_code": ap.get("country_code"),
                    "latitude": ap.get("latitude"),
                    "longitude": ap.get("longitude"),
                    "last_synced_at": datetime.now().isoformat()
                })
            
            if self.supabase and records:
                self.supabase.table("aims_airports").upsert(
                    records,
                    on_conflict="airport_code"
                ).execute()
                
            logger.info(f"Synced {len(records)} airports")
            return len(records)
            
        except Exception as e:
            logger.error(f"Airports sync failed: {e}")
            return 0
    
    def _sync_countries(self) -> int:
        """Sync countries from FetchCountries."""
        logger.info("Syncing countries...")
        
        try:
            # FetchCountries may need country code parameter
            # For now, we'll skip or implement later
            logger.info("Countries sync: Not implemented yet")
            return 0
            
        except Exception as e:
            logger.error(f"Countries sync failed: {e}")
            return 0
    
    # =========================================================
    # Operational Data Sync (Every 5 mins)
    # =========================================================
    
    def sync_operational_data(self, target_date: date = None) -> Dict[str, int]:
        """
        Sync operational data for a specific date.
        Should be run every 5 minutes.
        
        Args:
            target_date: Date to sync (defaults to today)
            
        Returns:
            Dict with count of records synced per table.
        """
        target_date = target_date or date.today()
        job_id = self._start_job("OPERATIONAL")
        results = {}
        total_records = 0
        
        try:
            # Sync Flights
            count = self._sync_flights(target_date)
            results["aims_flights"] = count
            total_records += count
            
            # Sync Leg Members (Crew Assignments)
            count = self._sync_leg_members(target_date)
            results["aims_leg_members"] = count
            total_records += count
            
            # Sync Crew Roster
            count = self._sync_crew_roster(target_date)
            results["aims_crew_roster"] = count
            total_records += count
            
            # Sync Flight Modification Log
            count = self._sync_flight_mod_log(target_date)
            results["aims_flight_mod_log"] = count
            total_records += count
            
            # Aircraft Swap Detection
            snap_count = self._update_snapshots(target_date)
            results["aircraft_swap_snapshots"] = snap_count
            total_records += snap_count
            
            swap_count = self._detect_and_save_swaps(target_date)
            results["aircraft_swaps"] = swap_count
            total_records += swap_count
            
            self._complete_job(job_id, total_records)
            
        except Exception as e:
            logger.error(f"Operational data sync failed: {e}")
            self._complete_job(job_id, total_records, str(e))
            
        return results
    
    def _sync_flights(self, target_date: date) -> int:
        """Sync flights from FlightDetailsForPeriod."""
        logger.info(f"Syncing flights for {target_date}...")
        
        try:
            flights = self._throttled_call(self.aims.get_day_flights, target_date)
            
            if not flights:
                logger.warning(f"No flights returned for {target_date}")
                return 0
            
            # Build records with deduplication
            # Key: (flight_date, flight_number, departure) - keep latest record
            records_map = {}
            
            for flt in flights:
                # Parse block time to minutes
                block_time = flt.get("block_time", "")
                block_mins = 0
                if block_time and ":" in block_time:
                    parts = block_time.split(":")
                    if len(parts) >= 2:
                        try:
                            block_mins = int(parts[0]) * 60 + int(parts[1])
                        except ValueError:
                            pass
                
                # Create unique key (matches DB constraint)
                key = (
                    flt.get("flight_date"),
                    flt.get("flight_number"),
                    flt.get("departure")
                )
                
                # Store record (later records overwrite earlier ones)
                records_map[key] = {
                    "flight_date": flt.get("flight_date"),
                    "flight_number": flt.get("flight_number"),
                    "carrier_code": flt.get("carrier_code"),
                    "departure": flt.get("departure"),
                    "arrival": flt.get("arrival"),
                    "aircraft_type": flt.get("aircraft_type"),
                    "aircraft_reg": flt.get("aircraft_reg"),
                    "std": flt.get("std"),
                    "sta": flt.get("sta"),
                    "etd": flt.get("etd"),
                    "eta": flt.get("eta"),
                    "atd": flt.get("atd"),
                    "ata": flt.get("ata"),
                    "tkof": flt.get("tkof"),
                    "tdwn": flt.get("tdwn"),
                    "off_block": flt.get("off_block"),
                    "on_block": flt.get("on_block"),
                    "block_time_minutes": block_mins,
                    "flight_status": flt.get("flight_status"),
                    "pax_total": flt.get("pax_total", 0),
                    "source": "AIMS",
                    "last_synced_at": datetime.now().isoformat()
                }
            
            records = list(records_map.values())
            logger.info(f"Deduped {len(flights)} raw flights to {len(records)} unique records")
            
            if self.supabase and records:
                # Batch upsert in chunks to avoid timeout
                chunk_size = 200
                for i in range(0, len(records), chunk_size):
                    chunk = records[i:i+chunk_size]
                    self.supabase.table("aims_flights").upsert(
                        chunk,
                        on_conflict="flight_date,flight_number,departure"
                    ).execute()
                
            logger.info(f"Synced {len(records)} flights")
            return len(records)
            
        except Exception as e:
            logger.error(f"Flights sync failed: {e}")
            return 0
    
    def _sync_leg_members(self, target_date: date) -> int:
        """Sync leg members from FetchLegMembersPerDay (bulk) with fallback to individual."""
        logger.info(f"Syncing leg members for {target_date}...")
        
        try:
            # 1. Try bulk method first
            all_members = self._throttled_call(self.aims.fetch_leg_members_per_day, target_date)
            
            # 2. If bulk fails or returns nothing, fallback to individual calls
            if not all_members:
                logger.warning(f"No leg members from bulk API for {target_date}. Falling back to individual calls...")
                
                # Fetch flights from DB to know what legs to sync
                # We use aims_flights table which was just synced
                flights = self.supabase.table("aims_flights") \
                    .select("flight_number, departure") \
                    .eq("flight_date", target_date.isoformat()) \
                    .execute()
                
                if not flights.data:
                    logger.warning(f"No flights in DB for {target_date}, cannot fallback sync leg members")
                    return 0
                
                logger.info(f"Syncing {len(flights.data)} flights individually...")
                all_members = []
                
                # Use ThreadPool with throttling
                with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                    futures = {
                        executor.submit(
                            self._throttled_call,
                            self.aims.get_leg_members,
                            target_date, f["flight_number"], f["departure"]
                        ): f for f in flights.data
                    }
                    
                    for future in as_completed(futures):
                        f = futures[future]
                        try:
                            res = future.result()
                            if res:
                                all_members.extend(res)
                                logger.info(f"  Flight {f['flight_number']} ({f['departure']}): Found {len(res)} crew")
                        except Exception as e:
                            logger.error(f"Error in individual leg member sync for {f['flight_number']}: {e}")
            
            if not all_members:
                logger.warning(f"Leg members sync produced 0 records for {target_date}")
                return 0
            
            # Add sync timestamp
            now_iso = datetime.now().isoformat()
            for m in all_members:
                m["last_synced_at"] = now_iso
            
            if self.supabase and all_members:
                # Batch upsert in chunks
                chunk_size = 500
                for i in range(0, len(all_members), chunk_size):
                    chunk = all_members[i:i+chunk_size]
                    self.supabase.table("aims_leg_members").upsert(
                        chunk,
                        on_conflict="flight_date,flight_number,departure,crew_id"
                    ).execute()
                    
            logger.info(f"Synced {len(all_members)} leg members")
            return len(all_members)
            
        except Exception as e:
            logger.error(f"Leg members sync failed: {e}")
            return 0
    
    def _sync_crew_roster(self, target_date: date) -> int:
        """Sync crew roster from CrewMemberRosterDetailsForPeriod."""
        logger.info(f"Syncing crew roster for {target_date}...")
        
        try:
            # Get crew list first
            crew_list = self._throttled_call(self.aims.get_crew_list, target_date, target_date)
            
            if not crew_list:
                return 0
            
            all_rosters = []
            
            # Get roster for each crew member (parallel with throttling)
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                futures = {}
                for crew in crew_list:
                    crew_id = crew.get("crew_id")
                    if crew_id:
                        future = executor.submit(
                            self._throttled_call,
                            self.aims.get_crew_schedule,
                            target_date, target_date, crew_id
                        )
                        futures[future] = crew_id
                
                for future in as_completed(futures):
                    crew_id = futures[future]
                    try:
                        schedules = future.result()
                        for s in schedules:
                            all_rosters.append({
                                "crew_id": crew_id,
                                "roster_date": target_date.isoformat(),
                                "duty_code": s.get("activity_code"),
                                "flight_number": s.get("flight_number"),
                                "activity_type": self._classify_duty(s.get("activity_code")),
                                "last_synced_at": datetime.now().isoformat()
                            })
                    except Exception as e:
                        logger.warning(f"Failed to get roster for crew {crew_id}: {e}")
            
            if self.supabase and all_rosters:
                chunk_size = 500
                for i in range(0, len(all_rosters), chunk_size):
                    chunk = all_rosters[i:i+chunk_size]
                    self.supabase.table("aims_crew_roster").upsert(
                        chunk,
                        on_conflict="crew_id,roster_date,duty_code,flight_number"
                    ).execute()
                    
            logger.info(f"Synced {len(all_rosters)} roster entries")
            return len(all_rosters)
            
        except Exception as e:
            logger.error(f"Crew roster sync failed: {e}")
            return 0
    
    def _sync_flight_mod_log(self, target_date: date) -> int:
        """Sync flight modification log from FlightScheduleModificationLog."""
        logger.info(f"Syncing flight mod log for {target_date}...")
        
        try:
            logs = self._throttled_call(self.aims.fetch_flight_mod_log, target_date, target_date)
            
            if not logs:
                return 0
            
            records = []
            for log in logs:
                records.append({
                    "flight_date": target_date.isoformat(),
                    "flight_number": log.get("flight_number"),
                    "departure": log.get("departure"),
                    "arrival": log.get("arrival"),
                    "modification_type": self._classify_mod_status(log.get("status_desc")),
                    "status_description": log.get("status_desc"),
                    "field_changed": log.get("field_changed", ""),
                    "old_value": log.get("old_value", ""),
                    "new_value": log.get("new_value", ""),
                    "modified_by": log.get("modified_by", ""),
                    "last_synced_at": datetime.now().isoformat()
                })
            
            if self.supabase and records:
                self.supabase.table("aims_flight_mod_log").insert(records).execute()
                
            logger.info(f"Synced {len(records)} mod log entries")
            return len(records)
            
        except Exception as e:
            logger.error(f"Mod log sync failed: {e}")
            return 0
    
    # =========================================================
    # Aircraft Swap Detection
    # =========================================================
    
    def _update_snapshots(self, target_date: date) -> int:
        """
        Save first-seen aircraft registration for each flight.
        Only creates a snapshot if one doesn't exist yet for the flight.
        """
        logger.info(f"Updating aircraft swap snapshots for {target_date}...")
        
        try:
            if not self.supabase:
                return 0
            
            # Fetch current flights from DB
            response = self.supabase.table("aims_flights") \
                .select("flight_date, flight_number, departure, aircraft_reg, aircraft_type") \
                .eq("flight_date", target_date.isoformat()) \
                .execute()
            
            if not response.data:
                return 0
            
            # Build snapshot records for flights that don't have one yet
            now_iso = datetime.now().isoformat()
            records = []
            
            for flt in response.data:
                reg = (flt.get("aircraft_reg") or "").strip()
                if not reg:
                    continue
                
                records.append({
                    "flight_date": flt["flight_date"],
                    "flight_number": flt["flight_number"],
                    "departure": flt["departure"],
                    "first_seen_reg": reg,
                    "first_seen_ac_type": flt.get("aircraft_type", ""),
                    "first_seen_at": now_iso,
                })
            
            if records:
                # Upsert with on_conflict = ignore (only insert if not exists)
                # Using upsert with ignoreDuplicates to not overwrite existing snapshots
                self.supabase.table("aircraft_swap_snapshots").upsert(
                    records,
                    on_conflict="flight_date,flight_number,departure",
                    ignore_duplicates=True
                ).execute()
            
            logger.info(f"Snapshot check: {len(records)} flights processed")
            return len(records)
            
        except Exception as e:
            logger.error(f"Snapshot update failed: {e}")
            return 0
    
    def _detect_and_save_swaps(self, target_date: date) -> int:
        """
        Compare current flight registrations against snapshots to detect swaps.
        Saves detected swaps to aircraft_swaps table.
        """
        logger.info(f"Running swap detection for {target_date}...")
        
        try:
            if not self.supabase:
                return 0
            
            sd = _get_swap_detector()
            
            # 1. Fetch current flights
            flights_resp = self.supabase.table("aims_flights") \
                .select("*") \
                .eq("flight_date", target_date.isoformat()) \
                .execute()
            
            if not flights_resp.data:
                return 0
            
            # 2. Fetch snapshots
            snap_resp = self.supabase.table("aircraft_swap_snapshots") \
                .select("*") \
                .eq("flight_date", target_date.isoformat()) \
                .execute()
            
            # Build snapshot index
            snapshots = {}
            for snap in (snap_resp.data or []):
                key = f"{snap['flight_date']}|{snap['flight_number']}|{snap['departure']}"
                snapshots[key] = snap
            
            # 3. Fetch mod logs for reason context
            mod_resp = self.supabase.table("aims_flight_mod_log") \
                .select("*") \
                .eq("flight_date", target_date.isoformat()) \
                .execute()
            
            # 4. Detect swaps
            new_swaps = sd.detect_swaps(
                current_flights=flights_resp.data,
                snapshots=snapshots,
                mod_logs=mod_resp.data or []
            )
            
            if not new_swaps:
                logger.info("No new swaps detected")
                return 0
            
            # 5. Get existing swap count for event ID generation
            count_resp = self.supabase.table("aircraft_swaps") \
                .select("id", count="exact") \
                .execute()
            existing_count = count_resp.count or 0
            
            # 6. Generate event IDs and prepare for insert
            now_iso = datetime.now().isoformat()
            records = []
            
            for i, swap in enumerate(new_swaps):
                event_id = sd.generate_swap_event_id(existing_count + i)
                
                records.append({
                    "swap_event_id": event_id,
                    "flight_date": swap["flight_date"],
                    "flight_number": swap["flight_number"],
                    "departure": swap.get("departure", ""),
                    "arrival": swap.get("arrival", ""),
                    "original_reg": swap["original_reg"],
                    "swapped_reg": swap["swapped_reg"],
                    "original_ac_type": swap.get("original_ac_type", ""),
                    "swapped_ac_type": swap.get("swapped_ac_type", ""),
                    "swap_reason": swap.get("swap_reason", ""),
                    "swap_category": swap.get("swap_category", "UNKNOWN"),
                    "delay_minutes": swap.get("delay_minutes", 0),
                    "recovery_status": swap.get("recovery_status", "PENDING"),
                    "detected_at": now_iso,
                    "mod_log_ref": swap.get("mod_log_ref", ""),
                })
            
            # 7. Upsert to avoid duplicates (same flight+date = same swap)
            if records:
                self.supabase.table("aircraft_swaps").upsert(
                    records,
                    on_conflict="swap_event_id"
                ).execute()
            
            logger.info(f"Detected and saved {len(records)} swap events")
            return len(records)
            
        except Exception as e:
            logger.error(f"Swap detection failed: {e}")
            return 0
    
    # =========================================================
    # Helper Methods
    # =========================================================
    
    def _classify_duty(self, duty_code: str) -> str:
        """Classify duty code into activity type."""
        if not duty_code:
            return "UNKNOWN"
            
        duty_upper = duty_code.upper()
        
        if duty_upper in ["SBY", "STANDBY"]:
            return "STANDBY"
        elif duty_upper in ["SL", "SICK", "SCL"]:
            return "SL"
        elif duty_upper in ["CSL", "CSICK", "NS", "NOSHOW"]:
            return "CSL"
        elif duty_upper in ["OFF", "DO", "R"]:
            return "OFF"
        elif duty_upper in ["TRN", "SIM", "GRD"]:
            return "TRAINING"
        elif duty_upper.isdigit() or duty_upper.startswith("VJ"):
            return "FLIGHT"
        else:
            return "OTHER"
    
    def _classify_mod_status(self, status_desc: str) -> str:
        """Classify modification status."""
        if not status_desc:
            return "UNKNOWN"
            
        status_upper = status_desc.upper()
        
        if "DELETE" in status_upper or "CANCEL" in status_upper:
            return "DELETED"
        elif "CREATE" in status_upper or "NEW" in status_upper:
            return "CREATED"
        elif "MODIFY" in status_upper or "CHANGE" in status_upper:
            return "MODIFIED"
        else:
            return "OTHER"
    
    # =========================================================
    # Full Sync
    # =========================================================
    
    def sync_all(self, target_date: date = None) -> Dict[str, Any]:
        """
        Run full sync of all data.
        
        Args:
            target_date: Date to sync operational data for
            
        Returns:
            Combined results from all sync operations.
        """
        target_date = target_date or date.today()
        
        logger.info(f"Starting full AIMS sync for {target_date}")
        
        results = {
            "reference": {},
            "operational": {},
            "success": True
        }
        
        try:
            results["reference"] = self.sync_reference_data()
            results["operational"] = self.sync_operational_data(target_date)
        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            results["success"] = False
            results["error"] = str(e)
            
        return results


# =========================================================
# Convenience Functions
# =========================================================

def run_reference_sync():
    """Run reference data sync (standalone)."""
    manager = AIMSETLManager()
    return manager.sync_reference_data()


def run_operational_sync(target_date: date = None):
    """Run operational data sync (standalone)."""
    manager = AIMSETLManager()
    return manager.sync_operational_data(target_date)


def run_full_sync(target_date: date = None):
    """Run full sync (standalone)."""
    manager = AIMSETLManager()
    return manager.sync_all(target_date)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    print("=" * 60)
    print("AIMS ETL Manager - Manual Sync")
    print("=" * 60)
    
    # Run full sync
    results = run_full_sync()
    
    print("\nSync Results:")
    print(f"  Reference Data: {results.get('reference', {})}")
    print(f"  Operational Data: {results.get('operational', {})}")
    print(f"  Success: {results.get('success', False)}")
