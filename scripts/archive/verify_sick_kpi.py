import requests

r = requests.get('http://localhost:5000/api/dashboard/summary?date=2026-02-11')
d = r.json().get('data', {})
print(f"crew_sick_total: {d.get('crew_sick_total', 'MISSING')}")
print(f"crew_sick_by_position: {d.get('crew_sick_by_position', 'MISSING')}")
print(f"sick_leave (legacy): {d.get('sick_leave', 'MISSING')}")
print(f"total_crew (legacy): {d.get('total_crew', 'MISSING')}")
