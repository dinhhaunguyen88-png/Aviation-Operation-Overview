"""
Execute SQL schema to add new AIMS tables to Supabase
Run this script to create the new database tables.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# For direct SQL execution, we need the service role key or use REST API
# Since we can't execute raw SQL via REST, we'll create tables individually

def create_tables_via_rest():
    """Create tables using Supabase REST API by inserting data first"""
    from supabase import create_client
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Tables we need to create are defined in add_aims_tables.sql
    # Supabase REST API doesn't support DDL, so we need to:
    # 1. Run SQL via Supabase Dashboard, OR
    # 2. Use supabase-py with admin privileges
    
    print("=" * 60)
    print("SUPABASE TABLE CREATION GUIDE")
    print("=" * 60)
    print("""
Since Supabase REST API doesn't support CREATE TABLE, 
please run the SQL manually:

1. Open Supabase Dashboard: https://supabase.com/dashboard
2. Go to your project
3. Click "SQL Editor" in the left sidebar
4. Copy and paste the contents of: scripts/add_aims_tables.sql
5. Click "Run" to execute

Alternatively, use the psql command if available:
psql "<your-database-url>" -f scripts/add_aims_tables.sql
""")
    
    # Verify if tables exist
    print("\n" + "=" * 60)
    print("CHECKING EXISTING TABLES...")
    print("=" * 60)
    
    tables_to_check = [
        'aircraft',
        'aircraft_types', 
        'airports',
        'crew_qualifications',
        'daily_crew_status',
        'flight_crew',
        'crew_members',
        'flights',
        'fact_roster'
    ]
    
    for table in tables_to_check:
        try:
            result = supabase.table(table).select("*", count="exact").limit(0).execute()
            count = result.count if result.count else 0
            print(f"✅ {table}: exists ({count} records)")
        except Exception as e:
            if "does not exist" in str(e).lower() or "42P01" in str(e):
                print(f"❌ {table}: NOT FOUND - needs creation")
            else:
                print(f"⚠️ {table}: {e}")

if __name__ == "__main__":
    create_tables_via_rest()
