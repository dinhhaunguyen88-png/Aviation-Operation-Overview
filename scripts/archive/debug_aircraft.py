from datetime import date
from data_processor import DataProcessor
import json

dp = DataProcessor()
target_date = date(2026, 2, 10)
summary = dp.get_aircraft_summary(target_date)

print(f"Total Aircraft in Summary: {len(summary.get('aircraft', []))}")
if summary.get('aircraft'):
    print("First aircraft:", summary['aircraft'][0]['reg'])
else:
    # Let's see why it's empty
    flights = dp.get_flights(target_date)
    print(f"Flights from get_flights: {len(flights)}")
    
    from data_processor import filter_operational_flights
    ops_flights = filter_operational_flights(flights, target_date, supabase=dp.supabase)
    print(f"Flights after re-filtering: {len(ops_flights)}")
    
    assignments = dp.get_roster_assignments(target_date)
    print(f"Assignments count: {len(assignments)}")
    
    if assignments:
        flights_with_crew = set()
        for c in assignments:
            fn = c.get("flight_no") or c.get("flight_number")
            if fn:
                flights_with_crew.add(str(fn).strip())
        print(f"Unique flights with crew: {len(flights_with_crew)}")
        
        import re
        test_ops = [f['flight_number'] for f in ops_flights[:20]]
        print(f"Testing matches for: {test_ops}")
        
        for fn in test_ops:
            base_match = re.search(r'(\d+)', fn)
            base_fn = base_match.group(1) if base_match else fn
            is_match = base_fn in flights_with_crew
            print(f"Flt: {fn} -> Base: {base_fn} -> In Crew List? {is_match}")
        
        final_flights = []
        for f in ops_flights:
            fn = f.get("flight_number", "")
            base_match = re.search(r'(\d+)', fn)
            base_fn = base_match.group(1) if base_match else fn
            if base_fn in flights_with_crew:
                final_flights.append(f)
                
        print(f"Final flights after normalized crew filter: {len(final_flights)}")
        
        if final_flights:
            regs = set(f.get("aircraft_reg") for f in final_flights)
            print(f"Unique Regs: {regs}")
