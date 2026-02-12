"""
Database Setup Script
Sets up Supabase tables using the Python client.
"""

import os
import sys
from datetime import date, datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def setup_database():
    """Setup database tables and insert sample data."""
    from supabase import create_client
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("[ERROR] SUPABASE_URL or SUPABASE_KEY not set in .env")
        return False
    
    print("="*60)
    print("Database Setup Script")
    print("="*60)
    print(f"[*] Supabase URL: {url}")
    
    try:
        supabase = create_client(url, key)
        print("[OK] Connected to Supabase")
        
        # Test connection - check existing tables
        tables_ok = True
        
        # Check 'crew' table (existing)
        try:
            result = supabase.table("crew").select("*").limit(1).execute()
            print("[OK] 'crew' table exists")
        except:
            print("[WARN] 'crew' table does not exist")
            tables_ok = False
            
        # Check other required tables
        for table in ["crew_flight_hours", "flights", "standby_records", "fact_roster", "fact_actuals"]:
            try:
                result = supabase.table(table).select("*").limit(1).execute()
                print(f"[OK] '{table}' table exists")
            except:
                print(f"[WARN] '{table}' table does not exist")
                tables_ok = False
        
        if not tables_ok:
            print("\n[>] Some tables are missing. Run the following in Supabase SQL Editor:")
            print("""
CREATE TABLE IF NOT EXISTS public.fact_roster (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id TEXT NOT NULL,
    activity_type TEXT,
    start_dt TIMESTAMPTZ,
    end_dt TIMESTAMPTZ,
    flight_no TEXT,
    source TEXT DEFAULT 'AIMS',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.fact_actuals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id TEXT NOT NULL,
    block_minutes INTEGER,
    dep_actual_dt TIMESTAMPTZ,
    ac_reg TEXT,
    source TEXT DEFAULT 'AIMS',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
            """)
            return False
            
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False
    
    # Insert sample data
    print("\n[*] Inserting sample data...")
    
    try:
        # Sample crew members
        crew_data = [
            {"crew_id": "C001", "crew_name": "Nguyen Van A", "first_name": "Van A", "last_name": "Nguyen", "base": "SGN", "gender": "M", "source": "SAMPLE"},
            {"crew_id": "C002", "crew_name": "Tran Thi B", "first_name": "Thi B", "last_name": "Tran", "base": "HAN", "gender": "F", "source": "SAMPLE"},
            {"crew_id": "C003", "crew_name": "Le Van C", "first_name": "Van C", "last_name": "Le", "base": "DAD", "gender": "M", "source": "SAMPLE"},
            {"crew_id": "C004", "crew_name": "Pham Thi D", "first_name": "Thi D", "last_name": "Pham", "base": "SGN", "gender": "F", "source": "SAMPLE"},
            {"crew_id": "C005", "crew_name": "Hoang Van E", "first_name": "Van E", "last_name": "Hoang", "base": "HAN", "gender": "M", "source": "SAMPLE"},
        ]
        
        supabase.table("crew_members").upsert(crew_data, on_conflict="crew_id").execute()
        print(f"[OK] Inserted {len(crew_data)} crew members")
        
        # Sample flight hours
        today = date.today()
        hours_data = [
            {"crew_id": "C001", "crew_name": "Nguyen Van A", "hours_28_day": 75.5, "hours_12_month": 650.0, "warning_level": "NORMAL", "calculation_date": today.isoformat(), "source": "SAMPLE"},
            {"crew_id": "C002", "crew_name": "Tran Thi B", "hours_28_day": 92.0, "hours_12_month": 880.0, "warning_level": "WARNING", "calculation_date": today.isoformat(), "source": "SAMPLE"},
            {"crew_id": "C003", "crew_name": "Le Van C", "hours_28_day": 98.5, "hours_12_month": 920.0, "warning_level": "CRITICAL", "calculation_date": today.isoformat(), "source": "SAMPLE"},
            {"crew_id": "C004", "crew_name": "Pham Thi D", "hours_28_day": 45.0, "hours_12_month": 400.0, "warning_level": "NORMAL", "calculation_date": today.isoformat(), "source": "SAMPLE"},
            {"crew_id": "C005", "crew_name": "Hoang Van E", "hours_28_day": 88.0, "hours_12_month": 780.0, "warning_level": "WARNING", "calculation_date": today.isoformat(), "source": "SAMPLE"},
        ]
        
        supabase.table("crew_flight_hours").upsert(hours_data, on_conflict="crew_id,calculation_date").execute()
        print(f"[OK] Inserted {len(hours_data)} flight hour records")
        
        # Sample flights
        flights_data = [
            {"flight_date": today.isoformat(), "carrier_code": "VJ", "flight_number": "VJ123", "departure": "SGN", "arrival": "HAN", "aircraft_type": "A321", "aircraft_reg": "VN-A321", "status": "SCHEDULED", "source": "SAMPLE"},
            {"flight_date": today.isoformat(), "carrier_code": "VJ", "flight_number": "VJ124", "departure": "HAN", "arrival": "SGN", "aircraft_type": "A321", "aircraft_reg": "VN-A321", "status": "EN_ROUTE", "source": "SAMPLE"},
            {"flight_date": today.isoformat(), "carrier_code": "VJ", "flight_number": "VJ456", "departure": "SGN", "arrival": "DAD", "aircraft_type": "A320", "aircraft_reg": "VN-A320", "status": "SCHEDULED", "source": "SAMPLE"},
            {"flight_date": today.isoformat(), "carrier_code": "VJ", "flight_number": "VJ789", "departure": "DAD", "arrival": "HAN", "aircraft_type": "A320", "aircraft_reg": "VN-A322", "status": "LANDED", "source": "SAMPLE"},
        ]
        
        supabase.table("flights").upsert(flights_data, on_conflict="flight_date,flight_number").execute()
        print(f"[OK] Inserted {len(flights_data)} flights")
        
        # Sample standby records
        standby_data = [
            {"crew_id": "C001", "crew_name": "Nguyen Van A", "status": "FLY", "duty_start_date": today.isoformat(), "duty_end_date": today.isoformat(), "base": "SGN", "source": "SAMPLE"},
            {"crew_id": "C002", "crew_name": "Tran Thi B", "status": "SBY", "duty_start_date": today.isoformat(), "duty_end_date": today.isoformat(), "base": "HAN", "source": "SAMPLE"},
            {"crew_id": "C003", "crew_name": "Le Van C", "status": "SL", "duty_start_date": today.isoformat(), "duty_end_date": (today + timedelta(days=2)).isoformat(), "base": "DAD", "source": "SAMPLE"},
            {"crew_id": "C004", "crew_name": "Pham Thi D", "status": "OFF", "duty_start_date": today.isoformat(), "duty_end_date": today.isoformat(), "base": "SGN", "source": "SAMPLE"},
            {"crew_id": "C005", "crew_name": "Hoang Van E", "status": "TRN", "duty_start_date": today.isoformat(), "duty_end_date": today.isoformat(), "base": "HAN", "source": "SAMPLE"},
        ]
        
        supabase.table("standby_records").upsert(standby_data).execute()
        print(f"[OK] Inserted {len(standby_data)} standby records")
        
        print("\n" + "="*60)
        print("[SUCCESS] Sample data inserted successfully!")
        print("="*60)
        print("\nYou can now test the dashboard at http://localhost:5000")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to insert data: {e}")
        return False


if __name__ == "__main__":
    setup_database()
