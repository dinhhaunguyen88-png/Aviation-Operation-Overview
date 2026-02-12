import requests

BASE = 'http://localhost:5000/api/dashboard/summary'

dates = {
    "TODAY (Feb 11)": "2026-02-11",
    "FUTURE (Feb 12)": "2026-02-12",
    "FUTURE (Feb 13)": "2026-02-13",
    "PAST (Feb 10)": "2026-02-10",
    "PAST (Feb 09)": "2026-02-09",
}

results = {}
for label, dt in dates.items():
    r = requests.get(f"{BASE}?date={dt}")
    d = r.json().get('data', {}) or {}
    tf = d.get('total_flights', '?')
    tc = d.get('total_completed_flights', '?')
    results[label] = (tf, tc)
    print(f"{label}: total_flights={tf}, completed={tc}")

print("\n--- VERIFICATION ---")
for label, (tf, tc) in results.items():
    if "FUTURE" in label:
        status = "PASS" if tc == 0 else "FAIL"
        print(f"  {status}: {label} completed should be 0, got {tc}")
    elif "PAST" in label:
        status = "PASS" if tf == tc else "FAIL"
        print(f"  {status}: {label} completed should equal total ({tf}), got {tc}")
    else:
        print(f"  INFO: {label} completed={tc} (real-time, expected > 0)")
