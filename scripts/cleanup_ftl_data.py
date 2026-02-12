"""Clean up fake crew and zero-value FTL records."""
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# 1. Delete fake C001-C005 crew from crew_members and crew_flight_hours
fake_ids = ['C001', 'C002', 'C003', 'C004', 'C005']
for fid in fake_ids:
    sb.table('crew_members').delete().eq('crew_id', fid).execute()
    sb.table('crew_flight_hours').delete().eq('crew_id', fid).execute()
print("Deleted 5 fake crew (C001-C005) from crew_members and crew_flight_hours")

# 2. Delete zero-value FTL records from AIMS sync (these are invalid)
result = sb.table('crew_flight_hours').delete().eq('source', 'AIMS_SYNC_OPT').eq('hours_28_day', 0).eq('hours_12_month', 0).execute()
deleted_count = len(result.data or [])
print(f"Deleted {deleted_count} zero-value AIMS_SYNC_OPT FTL records")

# 3. Also delete PLACEHOLDER_COPY records with 0 values
result2 = sb.table('crew_flight_hours').delete().eq('source', 'PLACEHOLDER_COPY').eq('hours_28_day', 0).eq('hours_12_month', 0).execute()
deleted_count2 = len(result2.data or [])
print(f"Deleted {deleted_count2} zero-value PLACEHOLDER_COPY FTL records")

# 4. Verify remaining data
remaining = sb.table('crew_flight_hours').select('crew_id', count='exact').execute()
print(f"\nRemaining FTL records: {remaining.count}")

nz = sb.table('crew_flight_hours').select('crew_id', count='exact').gt('hours_28_day', 0).execute()
print(f"Records with hours > 0: {nz.count}")

crew_count = sb.table('crew_members').select('crew_id', count='exact').execute()
print(f"Total crew_members after cleanup: {crew_count.count}")

# Check dates
sample = sb.table('crew_flight_hours').select('calculation_date, source, hours_28_day').order('hours_28_day', desc=True).limit(5).execute()
print("\nTop 5 records by hours:")
for d in sample.data:
    print(f"  date={d['calculation_date']} src={d.get('source', '?')} hrs={d['hours_28_day']}")
