import os
import sys
import logging
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

def manual_sync():
    """Manually sync data from AIMS to Supabase."""
    logger.info("Initializing DataProcessor...")
    processor = DataProcessor(data_source="AIMS")
    
    # Explicitly connect first
    logger.info("Connecting to AIMS...")
    if not processor.aims_client.connect():
        logger.error("Failed to connect to AIMS. Check credentials (WSDL/User/Pass).")
        return

    logger.info("Connected to AIMS. Starting sync...")

    try:
        # Define date range
        target_date = date.today()
        # For testing, ensure we get some data (AIMS test env might have data in specific ranges)
        # Using today ± 7 days as standard
        from_date = target_date - timedelta(days=7)
        to_date = target_date + timedelta(days=7)

        # 1. Sync Crew List (Basic Info)
        logger.info(f"Syncing Crew List ({from_date} to {to_date})...")
        try:
            crew_list = processor.aims_client.get_crew_list(from_date, to_date)
            if crew_list:
                 logger.info(f"Got {len(crew_list)} crew members. Deduplicating and upserting 'crew_members'...")
                 
                 from data_processor import transform_aims_crew_to_db
                 
                 # Deduplicate by crew_id
                 unique_crew = {}
                 for c in crew_list:
                     c_id = c.get('crew_id')
                     if c_id:
                         unique_crew[c_id] = c
                 
                 deduplicated_list = list(unique_crew.values())
                 logger.info(f"Unique crew count: {len(deduplicated_list)}")

                 db_records = [transform_aims_crew_to_db(c) for c in deduplicated_list]
                 
                 processor.supabase.table("crew_members").upsert(db_records, on_conflict="crew_id").execute()
                 logger.info(f"Upserted {len(db_records)} crew members.")
        except Exception as e:
            logger.error(f"Error syncing crew list: {e}")

        # 2. Roster/Schedule
        logger.info(f"Fetching Crew Schedule ({from_date} to {to_date})...")
        try:
             # AIMS doesn't support ID=0 for roster, must loop.
             # Use the deduplicated list from step 1, or fetch if needed.
             target_crew_ids = [c.get('crew_id') for c in deduplicated_list] if 'deduplicated_list' in locals() else []
             
             # Limit to 50 for testing speed (User can remove limit later)
             test_limit = 50
             logger.info(f"Syncing rosters for top {test_limit} crew members (Testing mode)...")
             
             all_rosters = []
             for c_id in target_crew_ids[:test_limit]:
                 if not c_id: continue
                 
                 schedules = processor.aims_client.get_crew_schedule(from_date, to_date, crew_id=c_id)
                 if schedules:
                     all_rosters.extend(schedules)
             
             if all_rosters:
                logger.info(f"Got {len(all_rosters)} roster records. Upserting to 'fact_roster'...")
                roster_records = []
                for item in all_rosters:
                    roster_records.append({
                        "crew_id": item["crew_id"],
                        "activity_type": item["activity_code"],
                        "start_dt": item["start_dt"],
                        "end_dt": item["end_dt"],
                        "flight_no": item["flight_number"],
                        "source": "AIMS"
                    })
                processor.supabase.table("fact_roster").upsert(roster_records).execute()
                logger.info("Roster sync complete.")
             else:
                logger.warning("No schedule records found for tested crew.")
        except Exception as e:
            logger.error(f"Error syncing roster: {e}")

        # 2. Actuals
        logger.info("Skipping separate Crew Actuals sync (integrated into Roster check pending implementation)...")
        # logger.info(f"Fetching Crew Actuals ({from_date} to {target_date})...")
        # try:
        #     actuals = processor.aims_client.get_crew_actuals(from_date, target_date)
        #     if actuals:
        #         logger.info(f"Got {len(actuals)} actual records. Upserting to 'fact_actuals'...")
        #         actual_records = []
        #         for item in actuals:
        #             actual_records.append({
        #                 "crew_id": item["crew_id"],
        #                 "block_minutes": item["block_minutes"],
        #                 "dep_actual_dt": item["dep_actual_dt"],
        #                 "ac_reg": item["ac_reg"],
        #                 "source": "AIMS"
        #             })
        #         processor.supabase.table("fact_actuals").upsert(actual_records).execute()
        #         logger.info("Actuals sync complete.")
        #         
        #         # Recalculate FTL
        #         logger.info("Recalculating FTL hours...")
        #         processed_crew = set(item["crew_id"] for item in actuals)
        #         recalc_records = []
        #         for c_id in processed_crew:
        #             hours = processor.calculate_28day_rolling_hours(c_id, target_date)
        #             level = processor.get_crew_alert_status(hours)
        #             recalc_records.append({
        #                 "crew_id": c_id,
        #                 "calculation_date": target_date.isoformat(),
        #                 "hours_28_day": hours,
        #                 "warning_level": level,
        #                 "source": "AIMS"
        #             })
        #         if recalc_records:
        #             processor.supabase.table("crew_flight_hours").upsert(recalc_records, on_conflict="crew_id,calculation_date").execute()
        #             logger.info(f"FTL updated for {len(recalc_records)} crew.")
        #     else:
        #         logger.warning("No actuals records found.")
        # except Exception as e:
        #     logger.error(f"Error syncing actuals: {e}")

        # 3. Flights (DayFlights)
        logger.info(f"Syncing Flights for {target_date}...")
        try:
             flights = processor.aims_client.get_day_flights(target_date)
             if flights:
                 logger.info(f"Got {len(flights)} flights. Upserting to 'flights'...")
                 from data_processor import transform_aims_flight_to_db
                 db_records = [transform_aims_flight_to_db(f) for f in flights]
                 processor.supabase.table("flights").upsert(db_records, on_conflict="flight_date,flight_number").execute()
                 logger.info(f"Upserted {len(db_records)} flights.")
             else:
                 logger.warning("No flights found.")
        except Exception as e:
             logger.error(f"Error syncing flights: {e}")

    except Exception as e:
        logger.error(f"Sync process failed: {e}")

if __name__ == "__main__":
    manual_sync()
