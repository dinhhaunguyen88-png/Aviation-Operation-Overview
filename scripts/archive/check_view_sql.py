import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("=== Checking View Definition: view_crew_status_summary ===")
try:
    # We can't directly get view definition from supabase-py easily,
    # but we can try to find the migration script or use RPC if exists.
    # Alternatively, I'll search the codebase for the SQL that created it.
    pass
except Exception as e:
    print(f"Error: {e}")
