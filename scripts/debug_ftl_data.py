"""Debug: Check crew_members base data and FTL overlap (no position column)."""
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# 1. Check base data distribution
print("=== BASE DATA ===")
all_crew = sb.table('crew_members').select('base').limit(500).execute()
bases = {}
for c in all_crew.data:
    base = c.get('base') or 'NULL/EMPTY'
    bases[base] = bases.get(base, 0) + 1
print(f"Base distribution (sample 500): {bases}")

# Count crew with non-null base
has_base = sb.table('crew_members').select('crew_id', count='exact').not_.is_('base', 'null').neq('base', '').execute()
print(f"Crew with non-empty base: {has_base.count}")

# Total crew
total = sb.table('crew_members').select('crew_id', count='exact').execute()
print(f"Total crew: {total.count}")

# 2. Sample crew records (all columns)
print("\n=== SAMPLE CREW RECORDS ===")
sample = sb.table('crew_members').select('*').limit(5).execute()
for c in sample.data:
    print(f"  id={c.get('crew_id')} | name={c.get('crew_name')} | base={c.get('base')} | src={c.get('source')}")

# 3. FTL ↔ CREW overlap
print("\n=== FTL ↔ CREW OVERLAP ===")
ftl_ids = sb.table('crew_flight_hours').select('crew_id').gt('hours_28_day', 0).limit(10).execute()
ftl_sample_ids = [r['crew_id'] for r in ftl_ids.data]
print(f"Sample FTL crew_ids with hours > 0: {ftl_sample_ids}")

if ftl_sample_ids:
    match = sb.table('crew_members').select('crew_id, crew_name, base').in_('crew_id', ftl_sample_ids).execute()
    print(f"Matching in crew_members: {len(match.data)}/{len(ftl_sample_ids)}")
    for m in match.data[:5]:
        print(f"  {m['crew_id']:>8} | name={m.get('crew_name','')} | base={m.get('base','')}")

# 4. Check what crew_flight_hours table columns look like
print("\n=== CREW_FLIGHT_HOURS COLUMNS ===")
ftl_sample = sb.table('crew_flight_hours').select('*').limit(1).execute()
if ftl_sample.data:
    print(list(ftl_sample.data[0].keys()))
    print(ftl_sample.data[0])
