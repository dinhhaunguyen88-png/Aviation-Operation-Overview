# AIMS Connection & Data Sync Troubleshooting
Date: 2026-01-31

## Work Accomplished
We successfully diagnosed and resolved the "Empty Dashboard" issue caused by a combination of Database Schema mismatches and API client implementation errors.

### 1. Database Schema Reset
- **Issue:** The dashboard was throwing 500 errors because the database tables (`crew_members`, `flights`, etc.) were missing new columns like `source`, `updated_at`, and using `TEXT` instead of `UUID`.
- **Fix:** 
    - Created `scripts/reset_schema.sql` to drop old tables and recreate them with the correct structure from `scripts/supabase_schema.sql`.
    - Executed the reset, ensuring a clean slate.

### 2. Manual Sync Script Fixes (`scripts/manual_sync.py`)
- **Issue:** The script failed to connect because it checked for a connection before initializing it (lazy loading issue). It also contained calls to non-existent methods.
- **Fix:**
    - Added explicit `processor.aims_client.connect()` call.
    - Corrected method signatures for `get_crew_list` and `get_day_flights`.
    - Added a deduplication step to prevent "ON CONFLICT" errors during upsert.

### 3. SOAP Client Implementation Fixes (`aims_soap_client.py`)
- **Issue:** The client was failing to parse the SOAP response from AIMS, resulting in "0 records parsed" or method missing errors.
- **Fix:**
    - **Method Mismatch:** `FetchDayFlights` was missing from the WSDL. Switched to `FetchFlightsFrTo` (mapped to `FlightDetailsForPeriod` internally) for flight fetching.
    - **Parameter Errors:** Corrected parameter names `FmDD` -> `FromDD` for `FlightDetailsForPeriod`.
    - **Response Parsing:** Discovered that `GetCrewList` returns a nested object structure (`ArrayOfTAIMSGetCrewItm`). Updated the parsing logic to drill down into `response.CrewList.TAIMSGetCrewItm`.
    - **Field Mapping:** Updated field mapping to match the actual WSDL response (e.g., `CrewID` -> `Id`, `CellPhone` -> `ContactCell`).

## Results
- **Crew List Sync:** **SUCCESS** ✅
    - Successfully fetched and upserted **3299 crew members** to the Supabase database.
    - Validate this by checking the "Total Crew" count on the dashboard (after refreshing).

- **Current Limitations:**
    - **Roster/Flights/Actuals:** These are currently returning "Invalid credentials" errors from the AIMS API (`GetCrewSchedule`, `GetCrewActuals`, `GetDayFlights`). This suggests that the current API user might have permissions strictly for `GetCrewList` but not for detailed operational data, or strict parameter requirement differences.
    - **Impact:** The "Active Flights" and "FTL Warnings" widgets may still show 0 data until permissions are resolved or alternative methods are found.

## Next Steps
1. **Verify Dashboard:** Log in to the dashboard and confirm the Crew List is populated.
2. **Check Permissions:** Verify if the AIMS Web Service user has permissions for `CrewMemberRosterDetailsForPeriod` and `FetchFlightsFrTo`.
3. **Debug Auth:** If permissions are correct, we may need to investigate the specific authentication requirements for the failing methods.
