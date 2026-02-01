"""
Sync AIMS data to new database tables.
Syncs: daily_crew_status, aircraft, crew_qualifications
"""
import os
import sys
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from supabase import create_client
from aims_soap_client import AIMSSoapClient

# Initialize clients
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
aims = AIMSSoapClient()

def sync_day_members(target_date: date = None, sample_size: int = 50):
    """
    Sync crew daily status (SBY, SL, CSL, FLT, OFF, etc.) from AIMS.
    Uses CrewMemberRosterDetailsForPeriod API method for each crew.
    
    Note: AIMS requires individual crew IDs, not batch queries.
    """
    if target_date is None:
        target_date = date.today()
    
    print(f"\n{'='*60}")
    print(f"SYNCING DAILY CREW STATUS FOR {target_date}")
    print(f"{'='*60}")
    
    try:
        # Connect to AIMS
        if not aims.connect():
            print("[ERROR] Failed to connect to AIMS")
            return False
        
        print("[OK] Connected to AIMS")
        
        # Get crew list from database
        print("[INFO] Fetching crew list from database...")
        result = supabase.table("crew_members").select("crew_id, crew_name").limit(sample_size).execute()
        
        if not result.data:
            print("[ERROR] No crew members in database")
            return False
        
        crew_list = result.data
        print(f"[OK] Found {len(crew_list)} crew members to query")
        
        # Query roster for each crew  
        all_rosters = []
        success_count = 0
        error_count = 0
        
        import time
        delay_seconds = 0.5  # Delay between API calls to avoid WAF blocking
        
        for i, crew in enumerate(crew_list):
            crew_id = crew.get("crew_id")
            if not crew_id:
                continue
            
            # Rate limiting - prevent WAF blocking
            if i > 0:
                time.sleep(delay_seconds)
                
            try:
                schedules = aims.get_crew_schedule(
                    from_date=target_date,
                    to_date=target_date,
                    crew_id=str(crew_id)
                )
                
                if schedules:
                    for s in schedules:
                        s["crew_id"] = crew_id
                        s["crew_name"] = crew.get("crew_name", "")
                    all_rosters.extend(schedules)
                    success_count += 1
                    
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    print(f"[WARN] Crew {crew_id}: {str(e)[:50]}")
                # Increase delay if getting blocked
                if "blocked" in str(e).lower() or "500" in str(e):
                    delay_seconds = min(delay_seconds * 2, 5)
                    print(f"[INFO] Increasing delay to {delay_seconds}s")
            
            # Progress update
            if (i + 1) % 10 == 0:
                print(f"   Processed {i+1}/{len(crew_list)} crew...")
        
        print(f"[OK] Fetched {len(all_rosters)} roster records from {success_count} crew")
        
        if not all_rosters:
            print("[WARN] No roster data returned")
            return False
        
        # Count by activity code
        duty_counts = {}
        for m in all_rosters:
            code = m.get('activity_code', 'UNKNOWN')
            duty_counts[code] = duty_counts.get(code, 0) + 1
        
        print("\n[INFO] Activity Code Breakdown:")
        for code, count in sorted(duty_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"   {code}: {count}")
        
        # Upsert to Supabase
        print(f"\n[INFO] Upserting to daily_crew_status table...")
        
        inserted = 0
        errors = 0
        
        for member in all_rosters:
            try:
                # Parse date from start_dt (format: YYYY-MM-DDTHH:MM:SS)
                start_dt = member.get("start_dt", "")
                if start_dt:
                    status_date = start_dt.split("T")[0]
                else:
                    status_date = target_date.isoformat()
                
                data = {
                    "crew_id": member.get("crew_id", ""),
                    "crew_name": member.get("crew_name", ""),
                    "status_date": status_date,
                    "duty_code": member.get("activity_code", ""),
                    "duty_description": "",
                    "base": member.get("base", ""),
                    "flight_number": member.get("flight_number", ""),
                    "source": "AIMS"
                }
                
                # Skip if no duty_code
                if not data["duty_code"]:
                    continue
                
                supabase.table("daily_crew_status").upsert(
                    data,
                    on_conflict="crew_id,status_date,duty_code"
                ).execute()
                inserted += 1
                
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"[ERROR] {e}")
        
        print(f"[OK] Inserted/Updated: {inserted} records")
        if errors:
            print(f"[WARN] Errors: {errors}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def sync_aircraft():
    """
    Sync aircraft registry from AIMS.
    Uses FetchAircrafts API method (#27).
    """
    print(f"\n{'='*60}")
    print(f"SYNCING AIRCRAFT REGISTRY")
    print(f"{'='*60}")
    
    try:
        if not aims.is_connected:
            aims.connect()
        
        aircraft_list = aims.get_aircraft_list()
        print(f"[OK] Fetched {len(aircraft_list)} aircraft from AIMS")
        
        if not aircraft_list:
            print("[WARN] No aircraft data returned")
            return False
        
        inserted = 0
        for ac in aircraft_list:
            try:
                data = {
                    "ac_reg": ac.get("ac_reg", ""),
                    "ac_type": ac.get("ac_type", ""),
                    "ac_country": ac.get("ac_country", ""),
                    "status": "ACTIVE",
                    "source": "AIMS"
                }
                
                if data["ac_reg"]:
                    supabase.table("aircraft").upsert(
                        data,
                        on_conflict="ac_reg"
                    ).execute()
                    inserted += 1
                    
            except Exception as e:
                print(f"[ERROR] {e}")
        
        print(f"[OK] Synced {inserted} aircraft")
        return True
        
    except Exception as e:
        print(f"[ERROR] Aircraft sync failed: {e}")
        return False


def sync_day_flights(target_date: date = None):
    """
    Sync flight details for a specific day from AIMS.
    Uses FlightDetailsForPeriod API method.
    """
    if target_date is None:
        target_date = date.today()
    
    print(f"\n{'='*60}")
    print(f"SYNCING FLIGHTS FOR {target_date}")
    print(f"{'='*60}")
    
    try:
        if not aims.is_connected:
            aims.connect()
        
        flights = aims.get_day_flights(target_date)
        print(f"[OK] Fetched {len(flights)} flights from AIMS")
        
        if not flights:
            print("[WARN] No flight data returned")
            return False
        
        inserted = 0
        for flt in flights:
            try:
                # Skip flights without departure data
                if not flt.get("departure"):
                    continue
                    
                data = {
                    "flight_date": flt.get("flight_date"),
                    "carrier_code": flt.get("carrier_code", "VJ"),
                    "flight_number": flt.get("flight_number", ""),
                    # Use 'departure' and 'arrival' columns (NOT NULL)
                    "departure": flt.get("departure", ""),
                    "arrival": flt.get("arrival", ""),
                    "aircraft_type": flt.get("aircraft_type", ""),
                    "aircraft_reg": flt.get("aircraft_reg", ""),
                    "std": flt.get("std"),
                    "sta": flt.get("sta"),
                    "etd": flt.get("etd"),
                    "eta": flt.get("eta"),
                    "atd": flt.get("atd"),
                    "off_block": flt.get("off_block"),
                    "on_block": flt.get("on_block"),
                    "delay_code_1": flt.get("delay_code_1", ""),
                    "delay_time_1": flt.get("delay_time_1", 0),
                    "pax_total": flt.get("pax_total", 0),
                    "status": flt.get("flight_status", "SCHEDULED"),
                    "source": "AIMS"
                }
                
                supabase.table("flights").upsert(
                    data,
                    on_conflict="flight_date,flight_number"
                ).execute()
                inserted += 1
                
            except Exception as e:
                print(f"[ERROR] {e}")
        
        print(f"[OK] Synced {inserted} flights")
        return True
        
    except Exception as e:
        print(f"[ERROR] Flights sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_sync():
    """Verify sync results by checking table counts."""
    print(f"\n{'='*60}")
    print(f"VERIFICATION - TABLE COUNTS")
    print(f"{'='*60}")
    
    tables = [
        "daily_crew_status",
        "aircraft",
        "flights",
        "crew_members"
    ]
    
    for table in tables:
        try:
            result = supabase.table(table).select("*", count="exact").limit(0).execute()
            count = result.count or 0
            print(f"   {table}: {count} records")
        except Exception as e:
            print(f"   {table}: ERROR - {e}")
    
    # Check duty code breakdown
    print(f"\n[INFO] Daily Crew Status by Duty Code (today):")
    try:
        today = date.today().isoformat()
        result = supabase.table("daily_crew_status") \
            .select("duty_code") \
            .eq("status_date", today) \
            .execute()
        
        if result.data:
            duty_counts = {}
            for row in result.data:
                code = row.get("duty_code", "UNKNOWN")
                duty_counts[code] = duty_counts.get(code, 0) + 1
            
            for code, count in sorted(duty_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"   {code}: {count}")
        else:
            print("   No data for today")
    except Exception as e:
        print(f"   Error: {e}")


def main():
    """Main sync entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync AIMS data to database")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD)", default=None)
    parser.add_argument("--all", action="store_true", help="Sync all data types")
    parser.add_argument("--crew", action="store_true", help="Sync daily crew status")
    parser.add_argument("--aircraft", action="store_true", help="Sync aircraft")
    parser.add_argument("--flights", action="store_true", help="Sync flights")
    
    args = parser.parse_args()
    
    # Parse target date
    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = date.today()
    
    print(f"\nAIMS Data Sync - Target Date: {target_date}")
    
    # Determine what to sync
    sync_all = args.all or not (args.crew or args.aircraft or args.flights)
    
    if sync_all or args.crew:
        sync_day_members(target_date)
    
    if sync_all or args.aircraft:
        sync_aircraft()
    
    if sync_all or args.flights:
        sync_day_flights(target_date)
    
    # Verify
    verify_sync()
    
    print(f"\n{'='*60}")
    print("SYNC COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
