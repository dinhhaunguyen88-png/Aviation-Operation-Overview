"""
Quick validation tests for swap_detector module.
Run: python tests/test_swap_quick.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swap_detector import (
    detect_swaps, classify_swap_reason, calculate_swap_kpis,
    get_reason_breakdown, get_top_impacted_tails, generate_swap_event_id
)

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name} {detail}")
    else:
        failed += 1
        print(f"  FAIL: {name} {detail}")

print("=" * 60)
print("Swap Detector - Quick Validation Tests")
print("=" * 60)

# 1. Reason Classification
print("\n[1] classify_swap_reason")
cat1, r1 = classify_swap_reason("MEL DEFECT on engine", "")
test("Maintenance keyword", cat1 == "MAINTENANCE", f"-> {cat1}")

cat2, r2 = classify_swap_reason("Weather delay due to fog", "")
test("Weather keyword", cat2 == "WEATHER", f"-> {cat2}")

cat3, r3 = classify_swap_reason("Crew sick leave", "")
test("Crew keyword", cat3 == "CREW", f"-> {cat3}")

cat4, r4 = classify_swap_reason("Schedule change OPS", "")
test("Operational keyword", cat4 == "OPERATIONAL", f"-> {cat4}")

cat5, r5 = classify_swap_reason("", "")
test("Empty -> UNKNOWN", cat5 == "UNKNOWN", f"-> {cat5}")

# 2. Swap Detection
print("\n[2] detect_swaps")
snaps = {
    "2026-02-12|VN100|SGN": {"first_seen_reg": "VN-A888", "first_seen_ac_type": "A350"}
}

# No swap
flights_same = [{
    "flight_number": "VN100", "flight_date": "2026-02-12",
    "departure": "SGN", "aircraft_reg": "VN-A888", "aircraft_type": "A350"
}]
r = detect_swaps(flights_same, snaps)
test("No swap when same reg", len(r) == 0, f"swaps={len(r)}")

# Swap detected
flights_diff = [{
    "flight_number": "VN100", "flight_date": "2026-02-12",
    "departure": "SGN", "arrival": "HAN",
    "aircraft_reg": "VN-A899", "aircraft_type": "A350",
    "flight_status": "ARRIVED", "std": "08:00", "atd": "08:45"
}]
r2 = detect_swaps(flights_diff, snaps)
test("Swap detected when reg differs", len(r2) == 1, f"swaps={len(r2)}")
if r2:
    test("Original reg correct", r2[0]["original_reg"] == "VN-A888")
    test("Swapped reg correct", r2[0]["swapped_reg"] == "VN-A899")
    test("Delay calculated", r2[0]["delay_minutes"] == 45, f"delay={r2[0]['delay_minutes']}min")
    test("Recovery status", r2[0]["recovery_status"] == "DELAYED", f"status={r2[0]['recovery_status']}")

# No snapshot = no swap
flights_no_snap = [{
    "flight_number": "VN200", "flight_date": "2026-02-12",
    "departure": "HAN", "aircraft_reg": "VN-A999", "aircraft_type": "A321"
}]
r3 = detect_swaps(flights_no_snap, snaps)
test("No swap when no snapshot exists", len(r3) == 0)

# 3. Event ID Generation
print("\n[3] generate_swap_event_id")
eid = generate_swap_event_id(23)
test("Event ID format", eid == "SW-0024", f"-> {eid}")
eid2 = generate_swap_event_id(0)
test("First event ID", eid2 == "SW-0001", f"-> {eid2}")

# 4. KPIs
print("\n[4] calculate_swap_kpis")
if r2:
    kpis = calculate_swap_kpis(r2, total_flights=100, previous_period_swaps=2)
    test("Total swaps", kpis["total_swaps"] == 1)
    test("Swap rate", kpis["swap_rate"] == 1.0, f"-> {kpis['swap_rate']}%")
    test("Trend calc", kpis["trend_vs_last_period"] == -50.0, f"-> {kpis['trend_vs_last_period']}%")

# Empty swaps
kpis_empty = calculate_swap_kpis([], total_flights=100)
test("Empty KPIs", kpis_empty["total_swaps"] == 0)
test("Empty recovery rate", kpis_empty["recovery_rate"] == 100.0)

# 5. Breakdown & Top Tails
print("\n[5] get_reason_breakdown & get_top_impacted_tails")
if r2:
    breakdown = get_reason_breakdown(r2)
    test("Breakdown not empty", len(breakdown) > 0, f"categories={len(breakdown)}")
    
    tails = get_top_impacted_tails(r2, limit=5)
    test("Top tails not empty", len(tails) > 0, f"tails={len(tails)}")

# Summary
print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("ALL TESTS PASSED!")
    sys.exit(0)
