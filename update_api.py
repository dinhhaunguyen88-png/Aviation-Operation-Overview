import os

file_path = "d:\\Aviation Dashboard Operation\\api_server.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

# Find boundaries
for i, line in enumerate(lines):
    if "def sync_aims_data():" in line:
        start_idx = i
    if "# Helper Functions" in line and start_idx != -1 and i > start_idx:
        end_idx = i
        break

# Backup just in case
if start_idx == -1 or end_idx == -1:
    print(f"Failed to find boundaries. Start: {start_idx}, End: {end_idx}")
    exit(1)

# Find exact end (before Helper Functions header)
# Helper functions block starts with header. We want to cut before that.
# Backtrack from end_idx to remove trailing newlines of previous function
actual_end = end_idx
while lines[actual_end-1].strip() == "":
    actual_end -= 1

print(f"Replacing lines {start_idx} to {actual_end}")

new_code = r'''def sync_aims_data():
    """
    Background job to sync data from AIMS.
    """
    if data_processor.data_source != "AIMS":
        logger.info("Skipping sync: Data source is not AIMS")
        return

    job_id = f"sync_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    logger.info(f"Starting AIMS sync job {job_id}...")

    try:
        # Create ETL job entry
        if data_processor.supabase:
            data_processor.supabase.table("etl_jobs").insert({
                "job_name": "AIMS Sync",
                "status": "RUNNING",
                "started_at": datetime.now().isoformat()
            }).execute()

        target_date = date.today()
        logger.info(f"Starting AIMS data sync for {target_date}")
        
        # 1. Sync Flights (Past 28 days for FTL Calculation)
        logger.info(f"Fetching flight history (28 days) for FTL calculation...")
        start_date = target_date - timedelta(days=28)
        end_date = target_date
        
        flight_block_map = {}
        
        current_start = start_date
        while current_start <= end_date:
            current_end = min(current_start + timedelta(days=6), end_date)
            try:
                batch = data_processor.aims_client.get_flights_range(current_start, current_end)
                for flt in batch:
                    f_date = flt.get("flight_date", "")
                    f_num = flt.get("flight_number", "")
                    blk = flt.get("block_time", "00:00")
                    
                    if f_date and f_num:
                        m = 0
                        if ":" in blk:
                            try:
                                parts = blk.split(":")
                                m = int(parts[0]) * 60 + int(parts[1])
                            except: pass
                        flight_block_map[(f_date, f_num)] = m
            except Exception as e:
                logger.error(f"Failed flight batch {current_start}: {e}")
            current_start += timedelta(days=7)

        # Sync Today's Flights for Display
        logger.info("Syncing today's flights for display...")
        today_flights = []
        try:
            today_flights = data_processor.aims_client.get_day_flights(target_date)
            if today_flights and data_processor.supabase:
                 flight_records = []
                 seen = set()
                 for flt in today_flights:
                     f_num = flt.get("flight_number", "")
                     key = (target_date.isoformat(), f_num)
                     if key not in seen:
                         seen.add(key)
                         flight_records.append({
                            "flight_date": target_date.isoformat(),
                            "flight_number": f_num,
                            "departure": flt.get("departure", ""),
                            "arrival": flt.get("arrival", ""),
                            "aircraft_reg": flt.get("aircraft_reg", ""),
                            "aircraft_type": flt.get("aircraft_type", ""),
                            "std": flt.get("std"),
                            "sta": flt.get("sta"),
                            "etd": flt.get("etd"),
                            "eta": flt.get("eta"),
                            "off_block": flt.get("off_block"),
                            "on_block": flt.get("on_block"),
                            "status": flt.get("flight_status") or "SCH",
                            "source": "AIMS"
                         })
                 if flight_records:
                      data_processor.supabase.table("flights").upsert(flight_records, on_conflict="flight_date,flight_number").execute()
                      logger.info(f"Upserted {len(flight_records)} flights for today")
        except Exception as e:
            logger.error(f"Failed today's flights: {e}")

        # 2. Get Candidate Crew List (CP, FO, PU, FA)
        positions = ["CP", "FO", "PU", "FA"]
        candidate_crew = []
        
        logger.info("Fetching candidate crew lists...")
        for pos in positions:
            try:
                clist = data_processor.aims_client.get_crew_list(target_date, target_date, position=pos)
                candidate_crew.extend(clist)
            except Exception as e:
                logger.error(f"Failed to fetch crew list for {pos}: {e}")
        
        logger.info(f"Found {len(candidate_crew)} candidate crew members. Checking duties via ThreadPool...")
        
        # 3. Parallel Check for Duty Today & FTL
        # Using a function to process each crew
        def process_crew(crew_meta):
            cid = crew_meta.get("crew_id")
            if not cid: return None
            
            try:
                # Fetch schedule for 28 days
                sched = data_processor.aims_client.get_crew_schedule(start_date, end_date, crew_id=cid)
                
                has_duty_today = False
                total_mins = 0
                today_iso = target_date.isoformat()
                
                roster_today = []
                
                for item in sched:
                    s_dt = item.get("start_dt", "")
                    f_num = item.get("flight_number", "")
                    
                    # Check Duty Today (Start Date matches Today)
                    if s_dt and s_dt.startswith(today_iso):
                        has_duty_today = True
                        roster_today.append(item)

                    # Calc FTL
                    if f_num:
                        d_str = s_dt.split("T")[0] if "T" in s_dt else s_dt
                        mins = flight_block_map.get((d_str, f_num), 0)
                        total_mins += mins
                
                if has_duty_today:
                    return {
                        "meta": crew_meta,
                        "roster": roster_today,
                        "ftl_mins": total_mins
                    }
            except Exception as e:
                # logger.warning(f"Error checking crew {cid}: {e}")
                return None
            return None

        results = []
        try:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(process_crew, c) for c in candidate_crew]
                for future in as_completed(futures):
                    res = future.result()
                    if res:
                        results.append(res)
        except Exception as e:
            logger.error(f"ThreadPoolExecutor failed: {e}")

        logger.info(f"Identified {len(results)} active crew with duties today.")
        
        # 4. Upsert Data
        if data_processor.supabase and results:
            crew_batch = []
            roster_batch = []
            ftl_batch = []
            
            for res in results:
                meta = res["meta"]
                cid = meta["crew_id"]
                
                # Crew
                crew_batch.append({
                    "crew_id": cid,
                    "crew_name": meta.get("crew_name", ""),
                    "base": "SGN", # Default
                    "source": "AIMS",
                    "updated_at": datetime.now().isoformat()
                })
                
                # Roster
                for r in res["roster"]:
                    roster_batch.append({
                        "crew_id": cid,
                        "activity_type": r.get("activity_code"),
                        "start_dt": r.get("start_dt"),
                        "end_dt": r.get("end_dt"),
                        "flight_no": r.get("flight_number") or "",
                        "source": "AIMS"
                    })
                    
                # FTL
                hours = round(res["ftl_mins"] / 60.0, 2)
                warn = "NORMAL"
                if hours > 95: warn = "CRITICAL"
                elif hours > 85: warn = "WARNING"
                
                ftl_batch.append({
                    "crew_id": cid,
                    "crew_name": meta.get("crew_name", ""),
                    "hours_28_day": hours,
                    "hours_12_month": 0,
                    "warning_level": warn,
                    "calculation_date": target_date.isoformat(),
                    "source": "AIMS_CALC"
                })
            
            # Upserts
            try:
                data_processor.supabase.table("crew_members").upsert(crew_batch).execute()
                logger.info(f"Upserted {len(crew_batch)} active crew")
                
                data_processor.supabase.table("fact_roster").upsert(roster_batch).execute()
                logger.info(f"Upserted {len(roster_batch)} roster items")
                
                data_processor.supabase.table("crew_flight_hours").upsert(ftl_batch).execute()
                logger.info(f"Upserted {len(ftl_batch)} FTL records")
                
            except Exception as e:
                logger.error(f"Upsert failed: {e}")

        # Success Log
        if data_processor.supabase:
            data_processor.supabase.table("etl_jobs").insert({
                "job_name": "AIMS Sync",
                "status": "SUCCESS",
                "records_processed": len(results),
                "completed_at": datetime.now().isoformat()
            }).execute()

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        try:
             if data_processor.supabase:
                data_processor.supabase.table("etl_jobs").insert({
                    "job_name": "AIMS Sync",
                    "status": "FAILED",
                    "error_message": str(e),
                    "started_at": datetime.now().isoformat()
                }).execute()
        except:
            pass
'''

# New content construction
final_content = lines[:start_idx] + [new_code + "\n\n"] + lines[actual_end:]

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(final_content)

print("Update complete.")
