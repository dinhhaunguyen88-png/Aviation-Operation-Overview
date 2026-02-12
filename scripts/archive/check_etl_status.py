import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

print("--- Recent ETL Jobs ---")
try:
    res = sb.table("etl_jobs").select("*").order("created_at", ascending=False).limit(10).execute()
    for r in res.data:
        print(f"Job: {r.get('job_type')} | Status: {r.get('status')} | Created: {r.get('created_at')} | Error: {r.get('error_message')}")
except Exception as e:
    print(f"Error: {e}")
