import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("=== Checking aims_leg_members for duty_code ===")
try:
    res = supabase.table("aims_leg_members").select("duty_code").execute()
    if res.data:
        unique_duty_codes = sorted(list(set(str(row.get("duty_code")).strip() for row in res.data if row.get("duty_code"))))
        print(f"Unique duty_codes: {unique_duty_codes}")
    else:
        print("No data in aims_leg_members.")
except Exception as e:
    print(f"Error: {e}")
