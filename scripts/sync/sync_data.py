"""
Data Sync Scheduler
Phase 2: Data Integration

Automated sync of data from AIMS API to database.
Uses APScheduler for job scheduling.
"""

import os
import logging
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_MINUTES", 5))
ROSTER_DAYS_RANGE = int(os.getenv("ROSTER_DAYS_RANGE", 7))


class DataSyncService:
    """
    Service for syncing data from AIMS to database.
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._aims_client = None
        self._supabase = None
        self._is_running = False
    
    @property
    def aims_client(self):
        """Lazy load AIMS client."""
        if self._aims_client is None:
            from aims_soap_client import AIMSSoapClient
            self._aims_client = AIMSSoapClient()
        return self._aims_client
    
    @property
    def supabase(self):
        """Lazy load Supabase client."""
        if self._supabase is None:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                self._supabase = create_client(url, key)
        return self._supabase
    
    def log_sync(self, sync_type: str, status: str, records: int = 0, error: str = None):
        """Log sync operation to database."""
        if self.supabase:
            try:
                self.supabase.table("sync_log").insert({
                    "sync_type": sync_type,
                    "status": status,
                    "records_processed": records,
                    "error_message": error,
                    "completed_at": datetime.now().isoformat() if status != "started" else None
                }).execute()
            except Exception as e:
                logger.error(f"Failed to log sync: {e}")
    
    def sync_crew_data(self):
        """
        Sync crew data from AIMS.
        
        Fetches crew list and stores in database.
        """
        logger.info("Starting crew data sync...")
        self.log_sync("crew", "started")
        
        try:
            if not self.aims_client.connect():
                raise ConnectionError("Failed to connect to AIMS")
            
            # Fetch crew for today +/- ROSTER_DAYS_RANGE
            today = date.today()
            from_date = today - timedelta(days=ROSTER_DAYS_RANGE)
            to_date = today + timedelta(days=ROSTER_DAYS_RANGE)
            
            crew_list = self.aims_client.get_crew_list(from_date, to_date)
            
            if not crew_list:
                logger.warning("No crew data returned from AIMS")
                self.log_sync("crew", "completed", 0)
                return
            
            # Transform and upsert to database
            from data_processor import transform_aims_crew_to_db
            
            records = [transform_aims_crew_to_db(crew) for crew in crew_list]
            
            if self.supabase and records:
                self.supabase.table("crew_members").upsert(
                    records,
                    on_conflict="crew_id"
                ).execute()
            
            logger.info(f"Synced {len(records)} crew records")
            self.log_sync("crew", "completed", len(records))
            
        except Exception as e:
            logger.error(f"Crew sync failed: {e}")
            self.log_sync("crew", "failed", 0, str(e))
    
    def sync_flight_data(self):
        """
        Sync flight data from AIMS.
        
        Fetches today's flights and stores in database.
        """
        logger.info("Starting flight data sync...")
        self.log_sync("flights", "started")
        
        try:
            if not self.aims_client.connect():
                raise ConnectionError("Failed to connect to AIMS")
            
            # Fetch today's flights
            today = date.today()
            flights = self.aims_client.get_day_flights(today)
            
            if not flights:
                logger.info("No flights for today")
                self.log_sync("flights", "completed", 0)
                return
            
            # Transform and upsert to database
            from data_processor import transform_aims_flight_to_db
            
            records = [transform_aims_flight_to_db(flight) for flight in flights]
            
            if self.supabase and records:
                self.supabase.table("flights").upsert(records).execute()
            
            logger.info(f"Synced {len(records)} flight records")
            self.log_sync("flights", "completed", len(records))
            
        except Exception as e:
            logger.error(f"Flight sync failed: {e}")
            self.log_sync("flights", "failed", 0, str(e))
    
    def sync_crew_roster(self):
        """
        Sync crew roster data.
        
        Fetches roster for each crew member.
        """
        logger.info("Starting roster sync...")
        self.log_sync("roster", "started")
        
        try:
            if not self.supabase:
                raise ConnectionError("Database not available")
            
            # Get crew list from database
            result = self.supabase.table("crew_members") \
                .select("crew_id") \
                .limit(100) \
                .execute()
            
            if not result.data:
                logger.info("No crew members in database")
                self.log_sync("roster", "completed", 0)
                return
            
            # Connect to AIMS
            if not self.aims_client.connect():
                raise ConnectionError("Failed to connect to AIMS")
            
            today = date.today()
            from_date = today - timedelta(days=ROSTER_DAYS_RANGE)
            to_date = today + timedelta(days=ROSTER_DAYS_RANGE)
            
            total_records = 0
            
            for crew in result.data:
                crew_id = int(crew["crew_id"])
                
                try:
                    roster = self.aims_client.get_crew_roster(crew_id, from_date, to_date)
                    
                    if roster:
                        # Transform roster items
                        records = []
                        for item in roster:
                            records.append({
                                "crew_id": str(crew_id),
                                "duty_date": item.get("duty_date"),
                                "duty_code": item.get("duty_code"),
                                "flight_number": item.get("flight_number"),
                                "departure": item.get("departure"),
                                "arrival": item.get("arrival"),
                                "aircraft_type": item.get("aircraft_type"),
                                "source": "AIMS",
                                "updated_at": datetime.now().isoformat()
                            })
                        
                        if records:
                            self.supabase.table("crew_roster").upsert(records).execute()
                            total_records += len(records)
                            
                except Exception as e:
                    logger.warning(f"Failed to sync roster for crew {crew_id}: {e}")
            
            logger.info(f"Synced {total_records} roster records")
            self.log_sync("roster", "completed", total_records)
            
        except Exception as e:
            logger.error(f"Roster sync failed: {e}")
            self.log_sync("roster", "failed", 0, str(e))
    
    def calculate_ftl_hours(self):
        """
        Calculate FTL (Flight Time Limitations) for all crew.
        
        Updates crew_flight_hours table with 28-day and 12-month rolling totals.
        Uses real-time data from AIMS and historical flight records.
        """
        logger.info("Starting FTL calculation...")
        self.log_sync("ftl_calc", "started")
        
        try:
            from data_processor import DataProcessor
            processor = DataProcessor()
            # Shared clients
            processor.aims_client = self.aims_client
            processor.supabase = self.supabase
            
            # Execute comprehensive calculation and persistence
            records_count = processor.sync_and_calculate_ftl()
            
            logger.info(f"Successfully calculated and updated FTL for {records_count} crew")
            self.log_sync("ftl_calc", "completed", records_count)
            
        except Exception as e:
            logger.error(f"FTL calculation failed: {e}")
            self.log_sync("ftl_calc", "failed", 0, str(e))
    
    def sync_static_data(self):
        """
        Sync static data (airports, aircraft types).
        
        Usually run once daily.
        """
        logger.info("Starting static data sync...")
        
        try:
            if not self.aims_client.connect():
                raise ConnectionError("Failed to connect to AIMS")
            
            # Sync aircraft
            aircraft = self.aims_client.get_aircraft_list()
            logger.info(f"Fetched {len(aircraft)} aircraft")
            
            # Sync airports
            airports = self.aims_client.get_airports()
            logger.info(f"Fetched {len(airports)} airports")
            
        except Exception as e:
            logger.error(f"Static data sync failed: {e}")
    
    def setup_jobs(self):
        """Configure scheduled jobs."""
        # Crew sync - every 5 minutes
        self.scheduler.add_job(
            func=self.sync_crew_data,
            trigger=IntervalTrigger(minutes=SYNC_INTERVAL),
            id='crew_sync',
            name='Sync crew data from AIMS',
            replace_existing=True
        )
        
        # Flight sync - every 5 minutes
        self.scheduler.add_job(
            func=self.sync_flight_data,
            trigger=IntervalTrigger(minutes=SYNC_INTERVAL),
            id='flight_sync',
            name='Sync flight data from AIMS',
            replace_existing=True
        )
        
        # FTL calculation - every 120 minutes (2 hours) to respect AIMS limits
        self.scheduler.add_job(
            func=self.calculate_ftl_hours,
            trigger=IntervalTrigger(minutes=120),
            id='ftl_calc',
            name='Calculate FTL hours',
            replace_existing=True,
            max_instances=1
        )
        
        # Roster sync - every 30 minutes
        self.scheduler.add_job(
            func=self.sync_crew_roster,
            trigger=IntervalTrigger(minutes=30),
            id='roster_sync',
            name='Sync crew roster',
            replace_existing=True
        )
        
        # Static data sync - daily at 02:00
        self.scheduler.add_job(
            func=self.sync_static_data,
            trigger=CronTrigger(hour=2, minute=0),
            id='static_sync',
            name='Daily static data sync',
            replace_existing=True
        )
        
        logger.info("Scheduled jobs configured")
    
    def start(self):
        """Start the scheduler."""
        if self._is_running:
            logger.warning("Scheduler already running")
            return
        
        self.setup_jobs()
        self.scheduler.start()
        self._is_running = True
        logger.info("Data sync scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if not self._is_running:
            return
        
        self.scheduler.shutdown()
        self._is_running = False
        logger.info("Data sync scheduler stopped")
    
    def run_once(self, job_name: str):
        """
        Run a specific job immediately.
        
        Args:
            job_name: Name of job to run (crew, flights, roster, ftl, static)
        """
        job_map = {
            "crew": self.sync_crew_data,
            "flights": self.sync_flight_data,
            "roster": self.sync_crew_roster,
            "ftl": self.calculate_ftl_hours,
            "static": self.sync_static_data
        }
        
        job = job_map.get(job_name)
        if job:
            job()
        else:
            logger.error(f"Unknown job: {job_name}")


# Singleton instance
sync_service = DataSyncService()


# =========================================================
# CLI Interface
# =========================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Sync Service")
    parser.add_argument(
        "--run",
        choices=["crew", "flights", "roster", "ftl", "static", "all"],
        help="Run a specific sync job"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon with scheduled jobs"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("Aviation Operations Dashboard - Data Sync Service")
    print("="*60)
    
    if args.run:
        if args.run == "all":
            print("Running all sync jobs...")
            sync_service.run_once("crew")
            sync_service.run_once("flights")
            sync_service.run_once("ftl")
        else:
            print(f"Running {args.run} sync...")
            sync_service.run_once(args.run)
    elif args.daemon:
        print("Starting sync daemon...")
        print(f"Sync interval: {SYNC_INTERVAL} minutes")
        sync_service.start()
        
        try:
            # Keep running
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopping...")
            sync_service.stop()
    else:
        parser.print_help()
