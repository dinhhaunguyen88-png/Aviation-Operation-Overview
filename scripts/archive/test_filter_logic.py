from datetime import date, datetime
from data_processor import filter_operational_flights

def test_logic():
    target_date = date.fromisoformat("2026-02-09")
    
    # Mock flight: 997 | HAN | DPS | 2026-02-10 | 03:15:00
    # This flight is Feb 10, 10:15 Local. 
    # It should be EXCLUDED from Feb 9th operational day.
    mock_flight = {
        "flight_number": "997",
        "departure": "HAN",
        "arrival": "DPS",
        "flight_date": "2026-02-10",
        "std": "03:15:00",
        "sta": "08:15:00"
    }
    
    print(f"Testing flight {mock_flight['flight_number']} for target date {target_date}")
    results = filter_operational_flights([mock_flight], target_date)
    
    if results:
        f = results[0]
        print(f"INCLUDED: {f.get('flight_date')} {f.get('local_std')}")
    else:
        print("EXCLUDED (Correct)")

    # Another mock: Feb 8 22:10 UTC = Feb 9 05:10 Local
    # Should be INCLUDED
    mock_flight_2 = {
        "flight_number": "185",
        "departure": "HAN",
        "arrival": "SGN",
        "flight_date": "2026-02-08",
        "std": "22:10:00"
    }
    print(f"\nTesting flight {mock_flight_2['flight_number']} for target date {target_date}")
    results = filter_operational_flights([mock_flight_2], target_date)
    if results:
        f = results[0]
        print(f"INCLUDED (Correct): {f.get('flight_date')} {f.get('local_std')}")
    else:
        print("EXCLUDED")

if __name__ == "__main__":
    test_logic()
