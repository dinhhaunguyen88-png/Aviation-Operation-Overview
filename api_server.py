"""
Flask API Server
Phase 2: Data Integration + Security Hardening

REST API endpoints for Aviation Operations Dashboard.
"""

import os
import logging
from datetime import date, datetime, timedelta
from functools import wraps
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import threading


from flask import Flask, jsonify, request, render_template, send_from_directory, Response
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from dotenv import load_dotenv
from decimal import Decimal
from alerts import FTL_WARNING_THRESHOLD, FTL_CRITICAL_THRESHOLD

# Load environment
dotenv_path = os.getenv("DOTENV_CONFIG_PATH", ".env")
load_dotenv(dotenv_path)

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Custom JSON Provider to handle Decimal and datetime
class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

# Create Flask app
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.json = CustomJSONProvider(app)

# Secret key - MUST be set in production
_secret_key = os.getenv("FLASK_SECRET_KEY")
if not _secret_key and os.getenv("FLASK_ENV") == "production":
    raise RuntimeError("FLASK_SECRET_KEY must be set in production environment!")
app.secret_key = _secret_key or "dev-secret-key-for-local-only"

# =========================================================
# CORS Configuration (Security Hardening)
# =========================================================

# CORS - Restricted by default (localhost only)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000").split(",")
CORS(app, resources={
    r"/api/*": {
        "origins": _cors_origins,
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "X-API-Key", "Authorization"]
    },
    r"/auth/*": {
        "origins": _cors_origins,
        "methods": ["POST"]
    }
})

# =========================================================
# Authentication (Security Hardening)
# =========================================================

_api_key = os.getenv("X_API_KEY") or os.getenv("SUPABASE_KEY")

def require_api_key(f):
    """Decorator to require X-API-Key header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return api_response(error="X-API-Key header missing", status=401)
        
        # In production, check against env
        if os.getenv("FLASK_ENV") == "production":
            if api_key != _api_key:
                return api_response(error="Invalid API Key", status=403)
        
        return f(*args, **kwargs)
    return decorated

# =========================================================
# Rate Limiting (Security Hardening)
# =========================================================

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["5000 per day", "1000 per hour"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
    logger.info("Rate limiting enabled: 5000/day, 1000/hour")
except ImportError:
    limiter = None
    logger.warning("Flask-Limiter not installed, rate limiting disabled")

# =========================================================
# Scheduler Configuration
# =========================================================

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    import atexit

    scheduler = BackgroundScheduler()
    logger.info("Scheduler initialized")
except ImportError:
    scheduler = None
    logger.error("APScheduler not installed. Run: pip install apscheduler")

# =========================================================
# Security Headers (Security Hardening)
# =========================================================

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # CSP for dashboard
    if request.path == '/' or request.path.startswith('/static'):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
        )
    
    return response


# =========================================================
# Initialize Data Processor
# =========================================================

from data_processor import DataProcessor, normalize_flight_id
from cache import cached

data_processor = DataProcessor(
    data_source=os.getenv("AIMS_SYNC_ENABLED", "true").lower() == "true" and "AIMS" or "CSV"
)

# Global lock for sync job
_sync_lock = threading.Lock()
_is_syncing = False

@app.context_processor
def inject_global_vars():
    """Inject API Key into all templates."""
    return dict(api_key=_api_key)

def _cleanup_stuck_jobs():
    """Mark stuck AIMS Sync jobs as FAILED on startup."""
    if not data_processor.supabase:
        return
        
    try:
        logger.info("Cleaning up stuck ETL jobs...")
        # Find all RUNNING AIMS Sync jobs
        result = data_processor.supabase.table("etl_jobs") \
            .select("id") \
            .eq("job_name", "AIMS Sync") \
            .eq("status", "RUNNING") \
            .execute()
            
        if result.data:
            job_ids = [r['id'] for r in result.data]
            logger.info(f"Marking {len(job_ids)} stuck jobs as FAILED")
            for jid in job_ids:
                data_processor.supabase.table("etl_jobs") \
                    .update({
                        "status": "FAILED",
                        "error_message": "System restart / Job hung",
                        "completed_at": datetime.now().isoformat()
                    }) \
                    .eq("id", jid) \
                    .execute()
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


# =========================================================
# Background Sync Job
# =========================================================

def sync_aims_data():
    """
    Background job to sync data from AIMS.
    Refactored to use modular helper functions.
    """
    if data_processor.data_source != "AIMS":
        logger.info("Skipping sync: Data source is not AIMS")
        return

    global _is_syncing
    if _is_syncing:
        logger.warning("Sync job already in progress, skipping...")
        return

    with _sync_lock:
        _is_syncing = True
        job_id = f"sync_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Starting AIMS sync job {job_id}...")

        try:
            if data_processor.supabase:
                data_processor.supabase.table("etl_jobs").insert({
                    "job_name": "AIMS Sync",
                    "status": "RUNNING",
                    "started_at": datetime.now().isoformat()
                }).execute()

            target_date = date.today()
            logger.info(f"Starting AIMS data sync for {target_date}")
            
            # 1. Sync 7-Day Flight Window (D-2 to D+4) for dashboard visibility
            sync_dates = [target_date + timedelta(days=d) for d in range(-2, 5)]  # 7 days
            _sync_daily_flights(sync_dates)
            
            # 2. Cleanup flights outside window
            _cleanup_old_flights(target_date)
            
            # 3. Comprehensive FTL Calculation (Rolling 28D + 12M)
            # This handles sync_flight_history, fetch_candidate_crew, process_crew_duties, and upsert_sync_results
            records_processed = data_processor.sync_and_calculate_ftl(target_date)
            
            # 4. Aircraft Swap Detection
            try:
                from aims_etl_manager import AIMSETLManager
                etl = AIMSETLManager(
                    aims_client=data_processor.aims_client,
                    supabase_client=data_processor.supabase
                )
                snap_count = etl._update_snapshots(target_date)
                swap_count = etl._detect_and_save_swaps(target_date)
                logger.info(f"Swap detection: {snap_count} snapshots, {swap_count} swaps detected")
            except Exception as swap_err:
                logger.warning(f"Swap detection failed (non-critical): {swap_err}")
            
            # Success Log
            if data_processor.supabase:
                data_processor.supabase.table("etl_jobs").insert({
                    "job_name": "AIMS Sync",
                    "status": "SUCCESS",
                    "records_processed": records_processed,
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
        finally:
            _is_syncing = False

def _sync_flight_history(target_date):
    """Fetch flight history for last 365 days for FTL calculation (28D + 12M)."""
    logger.info(f"Fetching flight history (365 days) for FTL calculation...")
    start_date_12m = target_date - timedelta(days=365)
    start_date_28d = target_date - timedelta(days=28)
    end_date = target_date
    
    flight_block_map_28d = {}  # Last 28 days only
    flight_block_map_12m = {}  # Last 365 days (includes 28d)
    
    current_start = start_date_12m
    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=6), end_date)
        try:
            batch = data_processor.aims_client.get_flights_range(current_start, current_end)
            for flt in batch:
                f_date = flt.get("flight_date", "")
                f_num_raw = flt.get("flight_number", "")
                f_num = normalize_flight_id(f_num_raw)
                blk = flt.get("block_time", "00:00")
                
                if f_date and f_num:
                    m = 0
                    if ":" in blk:
                        try:
                            parts = blk.split(":")
                            m = int(parts[0]) * 60 + int(parts[1])
                        except: pass
                    
                    flight_block_map_12m[(f_date, f_num)] = m
                    
                    # Also add to 28d map if within 28-day window
                    try:
                        from datetime import datetime as dt_cls
                        flt_date = dt_cls.strptime(f_date, "%Y-%m-%d").date() if isinstance(f_date, str) else f_date
                        if flt_date >= start_date_28d:
                            flight_block_map_28d[(f_date, f_num)] = m
                    except:
                        # If date parse fails, add to 28d map anyway (safe fallback)
                        flight_block_map_28d[(f_date, f_num)] = m
        except Exception as e:
            logger.error(f"Failed flight batch {current_start}: {e}")
        current_start += timedelta(days=7)
    
    logger.info(f"Flight history: {len(flight_block_map_28d)} flights (28D), {len(flight_block_map_12m)} flights (12M)")
    return flight_block_map_28d, flight_block_map_12m

# =========================================================
# Data Window Configuration
# =========================================================
DATA_WINDOW_PAST_DAYS = int(os.getenv("DATA_WINDOW_PAST_DAYS", 2))   # D-2
DATA_WINDOW_FUTURE_DAYS = int(os.getenv("DATA_WINDOW_FUTURE_DAYS", 4))  # D+4

def _sync_daily_flights(sync_dates):
    """Fetch and upsert flights for a list of dates (7-day window)."""
    logger.info(f"Syncing flights for {len(sync_dates)} dates: {[d.isoformat() for d in sync_dates]}")
    
    # Fetch dynamic cancellations once (shared across all dates)
    cancelled_keys = set()
    if data_processor.supabase:
        try:
            res = data_processor.supabase.table('aims_flight_mod_log') \
                .select('flight_date, flight_number, departure') \
                .eq('modification_type', 'DELETED') \
                .execute()
            if res.data:
                for log in res.data:
                    cancelled_keys.add((log['flight_date'], log['flight_number'], log['departure']))
            logger.info(f"Loaded {len(cancelled_keys)} cancellations from mod log")
        except Exception as e:
            logger.error(f"Failed to fetch cancellations for sync: {e}")

    total_upserted = 0
    
    for target_date in sync_dates:
        try:
            day_flights = data_processor.aims_client.get_day_flights(target_date)
            all_flights = list(day_flights) if day_flights else []
            
            if not all_flights:
                logger.info(f"  {target_date}: 0 flights from AIMS")
                continue
            
            # Clear old records for this date to ensure clean sync
            if data_processor.supabase:
                try:
                    data_processor.supabase.table("flights") \
                        .delete() \
                        .eq("flight_date", target_date.isoformat()) \
                        .execute()
                except Exception as e:
                    logger.error(f"Failed to clear flights for {target_date}: {e}")

            # Build flight records
            flight_records = []
            seen = set()
            
            for flt in all_flights:
                f_num_raw = flt.get("flight_number", "")
                f_num_norm = normalize_flight_id(f_num_raw)
                f_date = flt.get("flight_date", target_date.isoformat())
                
                if hasattr(f_date, 'isoformat'):
                    f_date = f_date.isoformat()
                elif not f_date:
                    f_date = target_date.isoformat()
                
                # Use normalized number for duplicate check key, but keep original for display if possible
                key = (f_date, f_num_norm, flt.get("departure", ""))
                if key not in seen:
                    seen.add(key)
                    display_flt_num = f"{f_num_raw}/{flt.get('departure', '')}"
                    flight_records.append({
                        "flight_date": f_date,
                        "flight_number": display_flt_num,
                        "carrier_code": flt.get("carrier_code") or "VJ",
                        "departure": flt.get("departure", ""),
                        "arrival": flt.get("arrival", ""),
                        "aircraft_reg": flt.get("aircraft_reg", ""),
                        "aircraft_type": flt.get("aircraft_type", ""),
                        "std": flt.get("std"),
                        "sta": flt.get("sta"),
                        "etd": flt.get("etd"),
                        "eta": flt.get("eta"),
                        "atd": flt.get("atd"),
                        "ata": flt.get("ata"),
                        "tkof": flt.get("tkof"),
                        "tdwn": flt.get("tdwn"),
                        "off_block": flt.get("off_block"),
                        "on_block": flt.get("on_block"),
                        "status": _calculate_flight_status(flt, is_cancelled=key in cancelled_keys),
                        "source": "AIMS"
                    })
            
            if flight_records and data_processor.supabase:
                data_processor.supabase.table("flights").upsert(
                    flight_records, 
                    on_conflict="flight_date,flight_number"
                ).execute()
                total_upserted += len(flight_records)
                logger.info(f"  {target_date}: Upserted {len(flight_records)} flights")
                
                # Only sync crew for today (too expensive for all 7 days)
                if target_date == date.today():
                    _sync_flight_crew(flight_records, target_date)
                
        except Exception as e:
            logger.error(f"Failed to sync flights for {target_date}: {e}")
            continue
    
    logger.info(f"7-Day sync complete: {total_upserted} total flights upserted")


def _cleanup_old_flights(today):
    """Remove flights outside the 7-day data window to keep DB clean."""
    if not data_processor.supabase:
        return
    
    # Keep buffer: D-3 to D+5 (1 extra day each side for get_flights prev/next day reads)
    min_date = (today - timedelta(days=DATA_WINDOW_PAST_DAYS + 1)).isoformat()
    max_date = (today + timedelta(days=DATA_WINDOW_FUTURE_DAYS + 1)).isoformat()
    
    try:
        # Delete flights older than window
        data_processor.supabase.table("flights") \
            .delete() \
            .lt("flight_date", min_date) \
            .execute()
        
        # Delete flights beyond future window
        data_processor.supabase.table("flights") \
            .delete() \
            .gt("flight_date", max_date) \
            .execute()
        
        logger.info(f"Cleanup: Removed flights outside [{min_date}, {max_date}]")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


def _sync_flight_crew(flight_records, target_date):
    """
    Sync crew assignments from leg_members API for each flight.
    Stores in flight_crew table for crew counting.
    """
    if not data_processor.supabase or not data_processor.aims_client:
        return
    
    logger.info(f"Syncing crew for {len(flight_records)} flights...")
    
    crew_records = []
    unique_crew_ids = set()
    
    # Process flights in batches or limited parallel to avoid WAF/TIMEOUT
    # Remove strict 50 limit to ensure we get all flights (e.g. 56+)
    sample_flights = flight_records 

    
    for flt in sample_flights:
        try:
            f_date_str = flt.get("flight_date", target_date.isoformat())
            f_num = flt.get("flight_number", "")
            dep = flt.get("departure", "")
            
            if not f_num or not dep:
                continue
            
            # Parse date
            if isinstance(f_date_str, str):
                f_date = datetime.strptime(f_date_str, "%Y-%m-%d").date()
            else:
                f_date = f_date_str
            
            # Get leg members
            time.sleep(0.3)  # Throttle API calls
            crew = data_processor.aims_client.get_leg_members(
                flight_date=f_date,
                flight_number=f_num,
                dep_airport=dep
            )
            
            for c in crew:
                crew_id = c.get("crew_id", "")
                if crew_id:
                    unique_crew_ids.add(crew_id)
                    crew_records.append({
                        "flight_date": f_date_str,
                        "flight_number": f_num,
                        "departure": dep,
                        "crew_id": crew_id,
                        "crew_name": c.get("crew_name", ""),
                        "position": c.get("position", ""),
                        "source": "AIMS"
                    })
                    
        except Exception as e:
            logger.warning(f"Failed leg_members for {flt.get('flight_number')}: {e}")
            continue

        # Batch upsert every 20 flights to avoid timeout/memory issues
        if len(crew_records) >= 20:
             try:
                data_processor.supabase.table("flight_crew").upsert(
                    crew_records,
                    on_conflict="flight_date,flight_number,departure,crew_id"
                ).execute()
                print(f"   >>> Batched sync: {len(crew_records)} records upserted.")
                crew_records = [] # Reset buffer
             except Exception as e:
                print(f"Failed to upsert batch: {e}")
    
    # Upsert remaining to flight_crew table
    if crew_records:
        try:
            data_processor.supabase.table("flight_crew").upsert(
                crew_records,
                on_conflict="flight_date,flight_number,departure,crew_id"
            ).execute()
            logger.info(f"Synced {len(crew_records)} crew assignments ({len(unique_crew_ids)} unique crew)")
            print(f"   >>> Final batch: {len(crew_records)} records upserted.")
        except Exception as e:
            logger.error(f"Failed to upsert flight_crew: {e}")

def _calculate_flight_status(flt, is_cancelled=False):
    """
    Calculate flight status more reliably than raw AIMS status.
    Fixes the bug where future flights are marked 'ARRIVED'.
    """
    if is_cancelled:
        return "CANCELLED"

    aims_status = flt.get("flight_status", "").upper()
    std_str = flt.get("std")
    sta_str = flt.get("sta")
    
    if not std_str:
        return aims_status or "SCH"
        
    try:
        # AIMS times are HH:MM, assume today's date context from target_date
        from airport_timezones import get_airport_timezone
        
        # AIMS times are in UTC? Or Local? 
        # Actually based on airport_timezones, we should add offset.
        # But for status calculation relative to "NOW" (which is VN LOCAL 10:00),
        # we need to compare apples to apples.
        
        # Step 1: Assume std_str is in UTC (common for AIMS)
        # Convert it to VN Local (UTC+7) or use absolute timestamps
        
        from datetime import timezone
        
        # Get VN current time (UTC+7)
        now_vn = datetime.now() # Already VN as confirmed by test
        
        # Build UTC datetime for STD/STA
        # We assume flight_date + std/sta is in UTC
        f_date = flt.get("flight_date", now_vn.date().isoformat())
        if hasattr(f_date, 'isoformat'): f_date = f_date.isoformat()
        
        # Parse STD/STA
        std_h, std_m = map(int, std_str.split(':'))
        sta_h, sta_m = map(int, sta_str.split(':'))

        # Get actual times for ATD/ATA/TKOF/TDWN
        atd_str = flt.get("atd")
        ata_str = flt.get("ata")
        tkof_str = flt.get("tkof")
        tdwn_str = flt.get("tdwn")
        
        try:
            from datetime import timedelta
            # Actually, standard AIMS integration uses UTC for STD/STA
            # and VN is UTC+7.
            
            # Simple conversion: add 7 hours to UTC to get VN
            std_vn_h = (std_h + 7) % 24
            sta_vn_h = (sta_h + 7) % 24
            
            std_dt = now_vn.replace(hour=std_vn_h, minute=std_m, second=0, microsecond=0)
            sta_dt = now_vn.replace(hour=sta_vn_h, minute=sta_m, second=0, microsecond=0)
            
            # Adjust day if rollover
            if std_vn_h < std_h: 
                 std_dt += timedelta(days=1)
            if sta_vn_h < sta_h:
                 sta_dt += timedelta(days=1)
        except:
            # Fallback to naive if error
            std_dt = now_vn.replace(hour=std_h, minute=std_m, second=0, microsecond=0)
            sta_dt = now_vn.replace(hour=sta_h, minute=sta_m, second=0, microsecond=0)

        # 1. ARRIVED (has ATA or now passed STA)
        if ata_str or tdwn_str:
            return "ARRIVED"
        
        if now_vn >= sta_dt:
            return "ARRIVED"

        # 2. DEPARTED (has ATD or now passed STD)
        if atd_str or tkof_str:
            return "DEPARTED"
            
        if now_vn >= std_dt:
            return "DEPARTED"

        # 3. CANCELLED / DELAYED (logic from AIMS status)
        aims_status = (flt.get("flight_status") or "").upper()
        if "CNX" in aims_status or "CANCEL" in aims_status:
            return "CANCELLED"
            
        if now_vn < std_dt:
            return "SCHEDULED"
            
        if now >= sta_dt:
            return "ARRIVED"
            
    except Exception as e:
        logger.warning(f"Status calculation failed for {flt.get('flight_number')}: {e}")
        
    return aims_status or "SCH"

def _fetch_candidate_crew(target_date):
    """Fetch candidate crew lists (CP, FO, PU, FA)."""
    positions = ["CP", "FO", "PU", "FA"]
    candidate_crew = []
    
    logger.info("Fetching candidate crew lists...")
    for pos in positions:
        try:
            clist = data_processor.aims_client.get_crew_list(target_date, target_date, position=pos)
            # Inject position since it's not always in the response
            for c in clist:
                c["position"] = pos
            candidate_crew.extend(clist)
        except Exception as e:
            logger.error(f"Failed to fetch crew list for {pos}: {e}")
    return candidate_crew

def _process_crew_duties(candidate_crew, flight_block_map_28d, flight_block_map_12m, target_date):
    """Check duties in parallel. Calculate both 28D and 12M FTL."""
    logger.info(f"Found {len(candidate_crew)} candidate crew members. Checking duties via ThreadPool...")
    
    # FTL calculation requires rolling windows: 28 days and 12 months.
    # We fetch the roster for the last 365 days to ensure 12M calculation is accurate.
    start_date = target_date - timedelta(days=365)
    end_date = target_date
    today_iso = target_date.isoformat()

    def process_crew(crew_meta):
        # time.sleep(0.5) # Reduced throttle
        cid = crew_meta.get("crew_id")
        if not cid: return None
        
        try:
            # Fetch schedule for 365 days (for 12M FTL calculation)
            sched = data_processor.aims_client.get_crew_schedule(start_date, end_date, crew_id=cid)
            
            has_duty_today = False
            total_mins_28d = 0
            total_mins_12m = 0
            
            roster_today = []
            
            for item in sched:
                s_dt = item.get("start_dt", "")
                f_num = item.get("flight_number", "")
                
                # Check Duty Today (Start Date matches Today)
                if s_dt and s_dt.startswith(today_iso):
                    has_duty_today = True
                    roster_today.append(item)

                # Calc FTL for both windows
                if f_num:
                    d_str = s_dt.split("T")[0] if "T" in s_dt else s_dt
                    f_num_norm = normalize_flight_id(f_num)
                    mins_28d = flight_block_map_28d.get((d_str, f_num_norm), 0)
                    mins_12m = flight_block_map_12m.get((d_str, f_num_norm), 0)
                    total_mins_28d += mins_28d
                    total_mins_12m += mins_12m
            
            if has_duty_today:
                return {
                    "meta": crew_meta,
                    "roster": roster_today,
                    "ftl_28d_mins": total_mins_28d,
                    "ftl_12m_mins": total_mins_12m
                }
        except Exception as e:
            return None
        return None

    results = []
    try:
        with ThreadPoolExecutor(max_workers=2) as executor: # Reduced for stability
            futures = [executor.submit(process_crew, c) for c in candidate_crew]
            for future in as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
    except Exception as e:
        logger.error(f"ThreadPoolExecutor failed: {e}")
        
    logger.info(f"Identified {len(results)} active crew with duties today.")
    return results

def _upsert_sync_results(results, target_date):
    """Upsert the filtered crew data to Supabase."""
    if not data_processor.supabase or not results:
        return

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
            "position": meta.get("position", ""),
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
            
        # FTL — use both 28D and 12M
        hours_28d = round(res.get("ftl_28d_mins", res.get("ftl_mins", 0)) / 60.0, 2)
        hours_12m = round(res.get("ftl_12m_mins", 0) / 60.0, 2)
        
        from data_processor import calculate_warning_level
        warn = calculate_warning_level(hours_28d, hours_12m)
        
        ftl_batch.append({
            "crew_id": cid,
            "crew_name": meta.get("crew_name", ""),
            "hours_28_day": hours_28d,
            "hours_12_month": hours_12m,
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


# Helper Functions
# =========================================================

def parse_date_param(date_str: str, default: date = None) -> date:
    """Parse date string from query parameter."""
    if not date_str:
        return default or date.today()
    
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"Invalid date format: {date_str}")
        return default or date.today()


def api_response(data=None, error=None, status=200):
    """Standard API response format."""
    response = {
        "success": error is None,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    if error:
        response["error"] = error
    return jsonify(response), status


# =========================================================
# Health & Status Endpoints
# =========================================================

@app.route('/chart-test')
def chart_test():
    """Chart.js test page for debugging."""
    return render_template('chart_test.html')

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return api_response({
        "status": "healthy",
        "service": "Aviation Operations Dashboard",
        "version": "1.0.0",
        "data_source": data_processor.data_source
    })


@app.route('/api/status')
def api_status():
    """API status endpoint."""
    checks = {
        "api": True,
        "database": False,
        "aims": False
    }
    
    # Check database connection
    try:
        if data_processor.supabase:
            data_processor.supabase.table("crew_members").select("count", count="exact").limit(1).execute()
            checks["database"] = True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
    
    # Check AIMS connection
    try:
        if data_processor.data_source == "AIMS" and data_processor.aims_client:
            checks["aims"] = data_processor.aims_client.is_connected
    except Exception as e:
        logger.error(f"AIMS check failed: {e}")
    
    overall_status = "healthy" if all(checks.values()) else "degraded"
    
    return api_response({
        "status": overall_status,
        "checks": checks,
        "data_source": data_processor.data_source
    })


# =========================================================
# Data Window Endpoint
# =========================================================

@app.route('/api/data-window')
def get_data_window():
    """Return the valid date range for the 7-day data window."""
    today = date.today()
    min_date = today - timedelta(days=DATA_WINDOW_PAST_DAYS)
    max_date = today + timedelta(days=DATA_WINDOW_FUTURE_DAYS)
    return api_response({
        "min_date": min_date.isoformat(),
        "max_date": max_date.isoformat(),
        "today": today.isoformat()
    })


# =========================================================
# Dashboard Endpoints
# =========================================================

@app.route('/api/dashboard/summary')
@require_api_key
def get_dashboard_summary():
    """
    Get dashboard summary with all KPIs.
    
    Query params:
        date: YYYY-MM-DD format (optional, defaults to today)
    """
    raw_date = request.args.get('date')
    target_date = parse_date_param(raw_date)
    logger.info(f"DASHBOARD REQUEST: raw_date='{raw_date}', parsed_date='{target_date}'")
    
    try:
        summary = data_processor.get_dashboard_summary(target_date)
        return api_response(summary)
    except Exception as e:
        logger.error(f"Dashboard summary failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/aircraft/daily-summary')
@require_api_key
def get_aircraft_daily_summary():
    """
    Get daily summary of all operating aircraft.
    
    Query params:
        date: YYYY-MM-DD format (optional, defaults to today)
    """
    target_date = parse_date_param(request.args.get('date'))
    
    try:
        summary = data_processor.get_aircraft_summary(target_date)
        return api_response(summary)
    except Exception as e:
        logger.error(f"Aircraft summary failed: {e}")
        return api_response(error=str(e), status=500)

@app.route('/api/flights/completed')
@require_api_key
def get_completed_flights():
    """
    Get completed flights with completion method for verification.
    
    Query params:
        date: YYYY-MM-DD format (optional, defaults to today)
    """
    target_date = parse_date_param(request.args.get('date'))
    
    try:
        from data_processor import get_completed_flights_detail
        flights = data_processor.get_flights(target_date)
        completed = get_completed_flights_detail(flights, target_date)
        return api_response({
            "completed_flights": completed,
            "total_completed": len(completed),
            "total_flights": len(flights),
            "date": target_date.isoformat()
        })
    except Exception as e:
        logger.error(f"Completed flights detail failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Crew Endpoints
# =========================================================

@app.route('/api/crew/top-stats')
@require_api_key
@cached(ttl=900, key_prefix="ftl_top")
def get_top_crew_stats():
    """
    Get top crew by flight hours (Bulk API).
    Solves N+1 problem by performing bulk calculation.
    
    Query params:
        days: Lookback period (default 28)
        limit: Number of crew (default 20)
        threshold: Warning limit (default 100)
    """
    days = request.args.get('days', 28, type=int)
    limit = request.args.get('limit', 20, type=int)
    threshold = request.args.get('threshold', 100.0, type=float)
    
    try:
        stats = data_processor.get_top_crew_stats(days=days, limit=limit, threshold=threshold)
        return api_response(stats)
    except Exception as e:
        logger.error(f"Bulk FTL stats failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/crew')
@require_api_key
def get_crew_list():
    """
    Get list of crew members with FTL data.
    
    Query params:
        date: YYYY-MM-DD format
        base: Filter by base code
        search: Search by crew_id or crew_name (partial match)
        level: Filter by warning_level (NORMAL, WARNING, CRITICAL)
        sort_by: Sort field (crew_id, crew_name, hours_28_day, hours_12_month)
        sort_order: asc or desc (default: desc)
        page: Page number (default 1)
        per_page: Items per page (default 50)
    """
    target_date = parse_date_param(request.args.get('date'))
    base = request.args.get('base', '').strip()
    search = request.args.get('search', '').strip()
    level = request.args.get('level', '').strip()
    sort_by = request.args.get('sort_by', 'hours_28_day').strip()
    sort_order = request.args.get('sort_order', 'desc').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    try:
        if data_processor.supabase:
            # --- Strategy ---
            # When sorting by FTL fields: query crew_flight_hours first (sorted+paginated in DB),
            # then join crew_members info for display.
            # When sorting by crew fields: query crew_members (sorted+paginated in DB),
            # then join FTL data for the page.
            
            is_ftl_sort = sort_by in ('hours_28_day', 'hours_12_month')
            calc_date = data_processor.get_best_ftl_date(target_date)
            
            if is_ftl_sort:
                # ============ FTL-FIRST STRATEGY ============
                # Query crew_flight_hours directly (sorted, paginated in DB)
                # When base/search filters active: over-fetch FTL, join crew_members, filter in Python
                
                if base or search:
                    # --- Cross-table filter: FTL sort + crew_members filter ---
                    # Can't do a JOIN in Supabase REST, so we over-fetch FTL records,
                    # join crew_members for base/name, filter out non-matching, accumulate results
                    
                    target_count = per_page
                    target_offset = (page - 1) * per_page
                    collected = []  # all matching records (for pagination)
                    batch_size = 200
                    ftl_offset = 0
                    safety_limit = 20  # max batches to prevent infinite loop
                    
                    while len(collected) < target_offset + target_count and safety_limit > 0:
                        safety_limit -= 1
                        
                        # Fetch a batch of FTL records sorted
                        ftl_q = data_processor.supabase.table("crew_flight_hours") \
                            .select("crew_id, crew_name, hours_28_day, hours_12_month, warning_level") \
                            .eq("calculation_date", calc_date) \
                            .order(sort_by, desc=(sort_order == 'desc'))
                        if level:
                            ftl_q = ftl_q.eq("warning_level", level)
                        ftl_q = ftl_q.range(ftl_offset, ftl_offset + batch_size - 1)
                        ftl_batch = ftl_q.execute()
                        batch_data = ftl_batch.data or []
                        
                        if not batch_data:
                            break  # No more FTL records
                        
                        # Join crew_members for base info
                        batch_cids = [r['crew_id'] for r in batch_data]
                        crew_info = data_processor.supabase.table("crew_members") \
                            .select("crew_id, crew_name, base") \
                            .in_("crew_id", batch_cids) \
                            .execute()
                        crew_map = {r['crew_id']: r for r in crew_info.data or []}
                        
                        # Filter and collect
                        for ftl in batch_data:
                            cid = ftl['crew_id']
                            crew = crew_map.get(cid, {})
                            crew_base = (crew.get('base', '') or '').strip()
                            crew_name_full = ftl.get('crew_name') or crew.get('crew_name', '')
                            
                            # Apply base filter
                            if base and not crew_base.upper().startswith(base.upper()):
                                continue
                            # Apply search filter
                            if search:
                                search_lower = search.lower()
                                if search_lower not in str(cid).lower() and search_lower not in crew_name_full.lower():
                                    continue
                            
                            collected.append({
                                'crew_id': cid,
                                'crew_name': crew_name_full,
                                'base': crew.get('base', ''),
                                'crew_flight_hours': [ftl]
                            })
                        
                        ftl_offset += batch_size
                        if len(batch_data) < batch_size:
                            break  # Last batch
                    
                    total_count = len(collected)
                    page_data = collected[target_offset:target_offset + target_count]
                    
                else:
                    # --- No cross-table filter needed: simple FTL query ---
                    ftl_count_q = data_processor.supabase.table("crew_flight_hours") \
                        .select("*", count="exact") \
                        .eq("calculation_date", calc_date)
                    if level:
                        ftl_count_q = ftl_count_q.eq("warning_level", level)
                    count_result = ftl_count_q.range(0, 0).execute()
                    total_count = count_result.count or 0
                    
                    # Fetch sorted FTL data
                    start = (page - 1) * per_page
                    ftl_q = data_processor.supabase.table("crew_flight_hours") \
                        .select("crew_id, crew_name, hours_28_day, hours_12_month, warning_level") \
                        .eq("calculation_date", calc_date) \
                        .order(sort_by, desc=(sort_order == 'desc'))
                    if level:
                        ftl_q = ftl_q.eq("warning_level", level)
                    ftl_q = ftl_q.range(start, start + per_page - 1)
                    ftl_result = ftl_q.execute()
                    ftl_rows = ftl_result.data or []
                    
                    # Join crew_members info
                    page_data = []
                    if ftl_rows:
                        page_crew_ids = [r['crew_id'] for r in ftl_rows]
                        crew_info = data_processor.supabase.table("crew_members") \
                            .select("crew_id, crew_name, base") \
                            .in_("crew_id", page_crew_ids) \
                            .execute()
                        crew_map = {r['crew_id']: r for r in crew_info.data or []}
                        
                        for ftl in ftl_rows:
                            cid = ftl['crew_id']
                            crew = crew_map.get(cid, {})
                            page_data.append({
                                'crew_id': cid,
                                'crew_name': ftl.get('crew_name') or crew.get('crew_name', ''),
                                'base': crew.get('base', ''),
                                'crew_flight_hours': [ftl]
                            })
                
                return api_response({
                    "crew": page_data,
                    "page": page,
                    "per_page": per_page,
                    "total": total_count
                })
            
            else:
                # ============ CREW-FIRST STRATEGY ============
                # Query crew_members (sorted, paginated in DB), join FTL for each page
                
                level_filtered_ids = None
                if level:
                    from data_processor import fetch_all_rows
                    ftl_filter_q = data_processor.supabase.table("crew_flight_hours") \
                        .select("crew_id") \
                        .eq("warning_level", level) \
                        .eq("calculation_date", calc_date)
                    level_filtered_rows = fetch_all_rows(ftl_filter_q)
                    level_filtered_ids = [r['crew_id'] for r in level_filtered_rows]
                    if not level_filtered_ids:
                        return api_response({"crew": [], "page": page, "per_page": per_page, "total": 0})
                
                # Count
                count_query = data_processor.supabase.table("crew_members").select("*", count="exact")
                count_query = count_query.neq("crew_id", "None")
                if base:
                    count_query = count_query.ilike("base", f"{base}%")
                if search:
                    count_query = count_query.or_(f"crew_id.ilike.%{search}%,crew_name.ilike.%{search}%")
                if level_filtered_ids is not None:
                    count_query = count_query.in_("crew_id", level_filtered_ids)
                count_result = count_query.range(0, 0).execute()
                total_count = count_result.count or 0
                
                # Fetch page
                query = data_processor.supabase.table("crew_members").select("*")
                query = query.neq("crew_id", "None")
                if base:
                    query = query.ilike("base", f"{base}%")
                if search:
                    query = query.or_(f"crew_id.ilike.%{search}%,crew_name.ilike.%{search}%")
                if level_filtered_ids is not None:
                    query = query.in_("crew_id", level_filtered_ids)
                if sort_by in ('crew_id', 'crew_name'):
                    query = query.order(sort_by, desc=(sort_order == 'desc'))
                
                start_idx = (page - 1) * per_page
                query = query.range(start_idx, start_idx + per_page - 1)
                result = query.execute()
                all_crew = result.data or []
                
                # Join FTL data for this page
                if all_crew:
                    crew_ids = [c['crew_id'] for c in all_crew if c['crew_id'] and c['crew_id'] != "None"]
                    if crew_ids:
                        ftl_result = data_processor.supabase.table("crew_flight_hours") \
                            .select("crew_id, crew_name, hours_28_day, hours_12_month, warning_level") \
                            .in_("crew_id", crew_ids) \
                            .eq("calculation_date", calc_date) \
                            .execute()
                        ftl_map = {r['crew_id']: r for r in ftl_result.data or []}
                        for c in all_crew:
                            ftl_data = ftl_map.get(c['crew_id'])
                            c['crew_flight_hours'] = [ftl_data] if ftl_data else []
                
                return api_response({
                    "crew": all_crew,
                    "page": page,
                    "per_page": per_page,
                    "total": total_count
                })
        else:
            return api_response({"crew": [], "page": 1, "per_page": 50, "total": 0})
            
    except Exception as e:
        logger.error(f"Get crew list failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/crew/<crew_id>')
def get_crew_detail(crew_id: str):
    """
    Get detailed crew information.
    
    Args:
        crew_id: Crew member ID
    """
    try:
        if data_processor.supabase:
            result = data_processor.supabase.table("crew_members") \
                .select("*") \
                .eq("crew_id", crew_id) \
                .single() \
                .execute()
            
            if result.data:
                return api_response(result.data)
            else:
                return api_response(error="Crew not found", status=404)
        else:
            return api_response(error="Database not available", status=503)
            
    except Exception as e:
        logger.error(f"Get crew detail failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/crew/<crew_id>/roster')
def get_crew_roster(crew_id: str):
    """
    Get crew roster for a period.
    
    Args:
        crew_id: Crew member ID
        
    Query params:
        from: Start date (YYYY-MM-DD)
        to: End date (YYYY-MM-DD)
    """
    from_date = parse_date_param(request.args.get('from'))
    to_date = parse_date_param(request.args.get('to'))
    
    try:
        if data_processor.supabase:
            result = data_processor.supabase.table("crew_roster") \
                .select("*") \
                .eq("crew_id", crew_id) \
                .gte("duty_date", from_date.isoformat()) \
                .lte("duty_date", to_date.isoformat()) \
                .order("duty_date") \
                .execute()
            
            return api_response({
                "crew_id": crew_id,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "roster": result.data or []
            })
        else:
            return api_response({"crew_id": crew_id, "roster": []})
            
    except Exception as e:
        logger.error(f"Get crew roster failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/crew/<crew_id>/flight-hours')
def get_crew_flight_hours(crew_id: str):
    """
    Get crew flight hours history.
    
    Args:
        crew_id: Crew member ID
    """
    try:
        if data_processor.supabase:
            result = data_processor.supabase.table("crew_flight_hours") \
                .select("*") \
                .eq("crew_id", crew_id) \
                .order("calculation_date", desc=True) \
                .limit(30) \
                .execute()
            
            return api_response({
                "crew_id": crew_id,
                "flight_hours": result.data or []
            })
        else:
            return api_response({"crew_id": crew_id, "flight_hours": []})
            
    except Exception as e:
        logger.error(f"Get flight hours failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Standby Endpoints
# =========================================================

@app.route('/api/standby')
def get_standby_list():
    """
    Get standby crew list (SBY, SL, CSL).
    
    Query params:
        date: YYYY-MM-DD format
        status: Filter by status (SBY, SL, CSL)
    """
    target_date = parse_date_param(request.args.get('date'))
    status_filter = request.args.get('status', '')
    
    try:
        standby = data_processor.get_standby_records(target_date)
        
        if status_filter:
            standby = [s for s in standby if s.get('status') == status_filter]
        
        # Group by status
        by_status = {}
        for record in standby:
            status = record.get('status', 'OTHER')
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(record)
        
        return api_response({
            "date": target_date.isoformat(),
            "total": len(standby),
            "by_status": {
                status: {"count": len(records), "crew": records}
                for status, records in by_status.items()
            },
            "standby": standby
        })
        
    except Exception as e:
        logger.error(f"Get standby failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Flight Endpoints
# =========================================================

@app.route('/api/flights')
@require_api_key
def get_flights():
    """
    Get flights for a date.
    
    Query params:
        date: YYYY-MM-DD format
        aircraft_type: Filter by AC type
    """
    target_date = parse_date_param(request.args.get('date'))
    aircraft_type = request.args.get('aircraft_type', '')
    
    try:
        flights = data_processor.get_flights(target_date)
        
        # Normalize aircraft types for consistent display/filtering
        from data_processor import normalize_ac_type
        for f in flights:
            f['aircraft_type'] = normalize_ac_type(f.get('aircraft_type'))
            
        if aircraft_type:
            # Use same normalization for comparison if input is "321" etc
            target_type = normalize_ac_type(aircraft_type)
            flights = [f for f in flights if f.get('aircraft_type') == target_type]
        
        return api_response({
            "date": target_date.isoformat(),
            "total": len(flights),
            "flights": flights
        })
        
    except Exception as e:
        logger.error(f"Get flights failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/flights/<flight_id>')
def get_flight_detail(flight_id: str):
    """
    Get flight detail with crew.
    
    Args:
        flight_id: Flight record ID
    """
    try:
        if data_processor.supabase:
            result = data_processor.supabase.table("flights") \
                .select("*") \
                .eq("id", flight_id) \
                .single() \
                .execute()
            
            if result.data:
                return api_response(result.data)
            else:
                return api_response(error="Flight not found", status=404)
        else:
            return api_response(error="Database not available", status=503)
            
    except Exception as e:
        logger.error(f"Get flight detail failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# FTL / Safety Endpoints
# =========================================================

@app.route('/api/ftl/summary')
@require_api_key
def get_ftl_summary():
    """
    Get FTL (Flight Time Limitations) summary.
    
    Query params:
        date: YYYY-MM-DD format
    """
    target_date = parse_date_param(request.args.get('date'))
    
    try:
        # Use fallback_to_latest to ensure consistency with the crew list
        crew_hours = data_processor.get_crew_hours(target_date, fallback_to_latest=True)
        
        # Fallback: If no pre-calculated hours exist, calculate them on-the-fly
        if not crew_hours and data_processor.supabase:
            logger.info(f"No pre-calculated crew hours for {target_date}, initiating dynamic fallback calculation...")
            # Get active crew members for this day from standby/actuals
            active_crew_ids = []
            try:
                # 1. Check standby records
                sby = data_processor.supabase.table("standby_records") \
                    .select("crew_id") \
                    .eq("duty_start_date", target_date.isoformat()) \
                    .execute()
                active_crew_ids.extend([r['crew_id'] for r in sby.data])
                
                # 2. Check today's flights
                flts = data_processor.supabase.table("flights") \
                    .select("flight_number") \
                    .eq("flight_date", target_date.isoformat()) \
                    .execute()
                # (Normally we'd join with pairings/roster, but for fallback we'll use unique SBY crew for now)
            except: pass
            
            # Remove duplicates
            unique_ids = list(set(active_crew_ids))
            
            # Calculate for top 50 active crew (limit for performance in dynamic calculation)
            if unique_ids:
                fallback_data = []
                for c_id in unique_ids[:50]:
                    hours = data_processor.calculate_28day_rolling_hours(c_id, target_date)
                    if hours > 0:
                        fallback_data.append({
                            "crew_id": c_id,
                            "crew_name": f"Crew {c_id}", # Fallback name
                            "hours_28_day": hours,
                            "hours_12_month": 0, # Cannot easily calc 12m on-the-fly without indexing
                            "warning_level": "NORMAL" if hours < 85 else ("WARNING" if hours < 95 else "CRITICAL"),
                            "calculation_date": target_date.isoformat()
                        })
                crew_hours = fallback_data

        # Count by warning level
        by_level = {"NORMAL": 0, "WARNING": 0, "CRITICAL": 0}
        for crew in crew_hours:
            level = crew.get("warning_level", "NORMAL")
            by_level[level] = by_level.get(level, 0) + 1
        
        # Get top 20 high intensity
        from data_processor import get_top_high_intensity_crew
        top_28d = get_top_high_intensity_crew(crew_hours, limit=20, sort_by="hours_28_day")
        top_12m = get_top_high_intensity_crew(crew_hours, limit=20, sort_by="hours_12_month")
        
        return api_response({
            "date": target_date.isoformat(),
            "total_crew": len(crew_hours),
            "by_level": by_level,
            "compliance_rate": round(
                (by_level["NORMAL"] / len(crew_hours) * 100) if crew_hours else 100, 1
            ),
            "top_20_28_day": top_28d,
            "top_20_12_month": top_12m
        })
        
    except Exception as e:
        logger.error(f"Get FTL summary failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/ftl/alerts')
def get_ftl_alerts():
    """
    Get active FTL alerts.
    
    Query params:
        date: YYYY-MM-DD format
        level: Filter by level (WARNING, CRITICAL)
    """
    target_date = parse_date_param(request.args.get('date'))
    level_filter = request.args.get('level', '')
    
    try:
        crew_hours = data_processor.get_crew_hours(target_date)
        
        alerts = []
        for crew in crew_hours:
            level = crew.get("warning_level", "NORMAL")
            if level in ["WARNING", "CRITICAL"]:
                if not level_filter or level == level_filter:
                    alerts.append({
                        "crew_id": crew.get("crew_id"),
                        "crew_name": crew.get("crew_name"),
                        "level": level,
                        "hours_28_day": crew.get("hours_28_day"),
                        "hours_12_month": crew.get("hours_12_month")
                    })
        
        # Sort by severity
        alerts.sort(key=lambda x: (0 if x["level"] == "CRITICAL" else 1, -x.get("hours_28_day", 0)))
        
        return api_response({
            "date": target_date.isoformat(),
            "total_alerts": len(alerts),
            "alerts": alerts
        })
        
    except Exception as e:
        logger.error(f"Get FTL alerts failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/ftl/export')
@require_api_key
def export_ftl_csv():
    """
    Export all crew FTL data as CSV.
    
    Query params:
        level: Filter by warning_level (optional)
    """
    level_filter = request.args.get('level', '').strip()
    
    try:
        if not data_processor.supabase:
            return api_response(error="Database not available", status=503)
        
        # Fetch all FTL data (paginated to bypass 1000-row limit)
        from data_processor import fetch_all_rows
        ftl_q = data_processor.supabase.table("crew_flight_hours") \
            .select("crew_id, crew_name, hours_28_day, hours_12_month, warning_level, calculation_date")
        
        if level_filter:
            ftl_q = ftl_q.eq("warning_level", level_filter)
        
        ftl_q = ftl_q.order("hours_28_day", desc=True)
        ftl_data = fetch_all_rows(ftl_q)
        
        # Fetch position/base from crew_members (in batches for large crew_ids lists)
        crew_map = {}
        if ftl_data:
            crew_ids = list(set(r['crew_id'] for r in ftl_data))
            # Batch in groups of 500 to avoid URL length limits with in_()
            for i in range(0, len(crew_ids), 500):
                batch_ids = crew_ids[i:i+500]
                crew_result = data_processor.supabase.table("crew_members") \
                    .select("crew_id, position, base") \
                    .in_("crew_id", batch_ids) \
                    .execute()
                for r in (crew_result.data or []):
                    crew_map[r['crew_id']] = r
        else:
            crew_map = {}
        
        # Build CSV
        import io
        output = io.StringIO()
        output.write("Crew ID,Name,Position,Base,28-Day Hours,12-Month Hours,Warning Level,Calc Date\n")
        
        for row in ftl_data:
            cid = row.get('crew_id', '')
            cm = crew_map.get(cid, {})
            output.write(
                f"{cid},"
                f"{row.get('crew_name', '')},"
                f"{cm.get('position', '')},"
                f"{cm.get('base', '')},"
                f"{row.get('hours_28_day', 0)},"
                f"{row.get('hours_12_month', 0)},"
                f"{row.get('warning_level', 'NORMAL')},"
                f"{row.get('calculation_date', '')}\n"
            )
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=ftl_report_{date.today().isoformat()}.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"FTL export failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/roster/heatmap')
def get_roster_heatmap():
    """
    Get roster data for heatmap visualization.
    """
    days = request.args.get('days', 7, type=int)
    
    try:
        data = data_processor.get_roster_heatmap_data(days)
        return api_response(data)
    except Exception as e:
        logger.error(f"Roster heatmap failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Data Source Configuration
# =========================================================

@app.route('/api/config/datasource', methods=['GET'])
def get_data_source():
    """Get current data source configuration."""
    return api_response({
        "data_source": data_processor.data_source,
        "aims_enabled": os.getenv("AIMS_SYNC_ENABLED", "true").lower() == "true"
    })


@app.route('/api/config/datasource', methods=['POST'])
def set_data_source():
    """
    Set data source.
    
    Body:
        source: "AIMS" or "CSV"
    """
    body = request.get_json() or {}
    source = body.get("source", "").upper()
    
    if source not in ["AIMS", "CSV"]:
        return api_response(error="Invalid source. Must be AIMS or CSV", status=400)
    
    data_processor.set_data_source(source)
    
    return api_response({
        "data_source": data_processor.data_source,
        "message": f"Data source set to {source}"
    })


# =========================================================
# CSV Upload Endpoint
# =========================================================

@app.route('/api/upload/csv', methods=['POST'])
def upload_csv():
    """
    Upload CSV file for processing.
    
    Form data:
        file: CSV file
        type: File type (crew_hours, flights, standby)
    """
    if 'file' not in request.files:
        return api_response(error="No file provided", status=400)
    
    file = request.files['file']
    file_type = request.form.get('type', 'crew_hours')
    
    if file.filename == '':
        return api_response(error="No file selected", status=400)
    
    if not file.filename.endswith('.csv'):
        return api_response(error="File must be CSV", status=400)
    
    try:
        # Save to temp location
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        # Parse based on type
        from data_processor import (
            parse_rol_cr_tot_report,
            parse_day_rep_report,
            parse_standby_report
        )
        
        if file_type == 'crew_hours':
            records = parse_rol_cr_tot_report(temp_path)
        elif file_type == 'flights':
            records = parse_day_rep_report(temp_path)
        elif file_type == 'standby':
            records = parse_standby_report(temp_path)
        else:
            return api_response(error=f"Unknown file type: {file_type}", status=400)
        
        # Save to database
        if data_processor.supabase and records:
            table_map = {
                'crew_hours': 'crew_flight_hours',
                'flights': 'flights',
                'standby': 'standby_records'
            }
            table = table_map.get(file_type)
            
            if table:
                # Upsert records
                data_processor.supabase.table(table).upsert(records).execute()
        
        # Clean up
        os.remove(temp_path)
        
        # Log success to ETL jobs
        try:
            if data_processor.supabase:
                data_processor.supabase.table("etl_jobs").insert({
                    "job_name": "CSV Upload",
                    "file_name": file.filename,
                    "file_type": file_type,
                    "records_processed": len(records),
                    "records_inserted": len(records),
                    "status": "SUCCESS",
                    "started_at": datetime.now().isoformat(),
                    "completed_at": datetime.now().isoformat()
                }).execute()
        except Exception as log_err:
            logger.error(f"Failed to log ETL job: {log_err}")

        return api_response({
            "message": f"Processed {len(records)} records",
            "file_type": file_type,
            "records_count": len(records)
        })
        
    except Exception as e:
        logger.error(f"CSV upload failed: {e}")
        # Log failure to ETL jobs
        try:
            if data_processor.supabase:
                data_processor.supabase.table("etl_jobs").insert({
                    "job_name": "CSV Upload",
                    "file_name": file.filename,
                    "file_type": file_type,
                    "status": "FAILED",
                    "error_message": str(e),
                    "started_at": datetime.now().isoformat()
                }).execute()
        except:
            pass
        return api_response(error=str(e), status=500)


@app.route('/api/etl/history')
def get_etl_history():
    """Get history of ETL jobs."""
    try:
        if data_processor.supabase:
            try:
                result = data_processor.supabase.table("etl_jobs") \
                    .select("*") \
                    .order("started_at", desc=True) \
                    .limit(10) \
                    .execute()
                return api_response(result.data or [])
            except Exception as db_err:
                logger.warning(f"etl_jobs table might be missing: {db_err}")
                return api_response([])
        else:
            return api_response([])
    except Exception as e:
        logger.error(f"Get ETL history failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/system/health')
def get_system_health():
    """Get system health metrics."""
    # In a real app, these would come from Prometheus/Redis/etc.
    import random
    return api_response({
        "api": {
            "status": "healthy",
            "latency_ms": random.randint(8, 25),
            "uptime": "14d 6h 22m"
        },
        "database": {
            "status": "connected",
            "pool_active": random.randint(5, 15),
            "pool_size": 20
        },
        "cache": {
            "status": "active",
            "hit_rate": f"{random.randint(85, 98)}%",
            "memory_used_mb": random.randint(120, 450)
        },
        "queue": {
            "status": "processing",
            "depth": random.randint(0, 50),
            "workers_active": 4
        }
    })


# =========================================================
# Aircraft Swap Analysis Endpoints
# =========================================================

def _parse_period_dates(period: str):
    """Convert period string to (from_date, to_date) tuple."""
    today = date.today()
    if period == '24h':
        return today, today
    elif period == '30d':
        return today - timedelta(days=30), today
    else:  # default 7d
        return today - timedelta(days=7), today


@app.route('/api/swap/summary')
@require_api_key
@cached(ttl=300, key_prefix="swap_summary")
def get_swap_summary():
    """
    Get swap analysis KPI summary.
    
    Query params:
        period: 24h|7d|30d (default 7d)
    """
    period = request.args.get('period', '7d')
    from_date, to_date = _parse_period_dates(period)
    
    try:
        if not data_processor.supabase:
            return api_response(error="Database not available", status=503)
        
        # Fetch swaps for period
        query = data_processor.supabase.table("aircraft_swaps") \
            .select("*") \
            .gte("flight_date", from_date.isoformat()) \
            .lte("flight_date", to_date.isoformat())
        result = query.execute()
        swaps = result.data or []
        
        # Get total flights for rate calculation
        flights_q = data_processor.supabase.table("aims_flights") \
            .select("id", count="exact") \
            .gte("flight_date", from_date.isoformat()) \
            .lte("flight_date", to_date.isoformat())
        flights_result = flights_q.execute()
        total_flights = flights_result.count or 0
        
        # Previous period for trend
        delta = (to_date - from_date).days or 1
        prev_from = from_date - timedelta(days=delta)
        prev_to = from_date - timedelta(days=1)
        prev_q = data_processor.supabase.table("aircraft_swaps") \
            .select("id", count="exact") \
            .gte("flight_date", prev_from.isoformat()) \
            .lte("flight_date", prev_to.isoformat())
        prev_result = prev_q.execute()
        prev_count = prev_result.count or 0
        
        # Calculate KPIs
        from swap_detector import calculate_swap_kpis
        kpis = calculate_swap_kpis(swaps, total_flights, prev_count)
        
        return api_response(kpis)
        
    except Exception as e:
        logger.error(f"Swap summary failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/swap/events')
@require_api_key
def get_swap_events():
    """
    Get swap event list with filtering and pagination.
    
    Query params:
        period: 24h|7d|30d
        page: int (default 1)
        per_page: int (default 10)
        category: MAINTENANCE|WEATHER|CREW|OPERATIONAL
    """
    period = request.args.get('period', '7d')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', '').strip().upper()
    
    from_date, to_date = _parse_period_dates(period)
    
    try:
        if not data_processor.supabase:
            return api_response(error="Database not available", status=503)
        
        # Count query
        count_q = data_processor.supabase.table("aircraft_swaps") \
            .select("*", count="exact") \
            .gte("flight_date", from_date.isoformat()) \
            .lte("flight_date", to_date.isoformat())
        if category:
            count_q = count_q.eq("swap_category", category)
        count_result = count_q.range(0, 0).execute()
        total = count_result.count or 0
        
        # Data query with pagination
        start = (page - 1) * per_page
        data_q = data_processor.supabase.table("aircraft_swaps") \
            .select("*") \
            .gte("flight_date", from_date.isoformat()) \
            .lte("flight_date", to_date.isoformat()) \
            .order("detected_at", desc=True)
        if category:
            data_q = data_q.eq("swap_category", category)
        data_q = data_q.range(start, start + per_page - 1)
        data_result = data_q.execute()
        
        return api_response({
            "events": data_result.data or [],
            "total": total,
            "page": page,
            "per_page": per_page
        })
        
    except Exception as e:
        logger.error(f"Swap events failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/swap/reasons')
@require_api_key
@cached(ttl=300, key_prefix="swap_reasons")
def get_swap_reasons():
    """
    Get swap reason breakdown for chart.
    
    Query params:
        period: 24h|7d|30d
    """
    period = request.args.get('period', '7d')
    from_date, to_date = _parse_period_dates(period)
    
    try:
        if not data_processor.supabase:
            return api_response(error="Database not available", status=503)
        
        result = data_processor.supabase.table("aircraft_swaps") \
            .select("swap_category") \
            .gte("flight_date", from_date.isoformat()) \
            .lte("flight_date", to_date.isoformat()) \
            .execute()
        
        swaps = result.data or []
        
        from swap_detector import get_reason_breakdown
        breakdown = get_reason_breakdown(swaps)
        
        return api_response({"reasons": breakdown})
        
    except Exception as e:
        logger.error(f"Swap reasons failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/swap/top-tails')
@require_api_key
@cached(ttl=300, key_prefix="swap_top_tails")
def get_swap_top_tails():
    """
    Get top impacted aircraft tail numbers.
    
    Query params:
        period: 24h|7d|30d
        limit: int (default 10)
    """
    period = request.args.get('period', '7d')
    limit = request.args.get('limit', 10, type=int)
    from_date, to_date = _parse_period_dates(period)
    
    try:
        if not data_processor.supabase:
            return api_response(error="Database not available", status=503)
        
        result = data_processor.supabase.table("aircraft_swaps") \
            .select("original_reg, swapped_reg, original_ac_type, swapped_ac_type, swap_category") \
            .gte("flight_date", from_date.isoformat()) \
            .lte("flight_date", to_date.isoformat()) \
            .execute()
        
        swaps = result.data or []
        
        from swap_detector import get_top_impacted_tails
        tails = get_top_impacted_tails(swaps, limit=limit)
        
        return api_response({"tails": tails})
        
    except Exception as e:
        logger.error(f"Swap top tails failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/swap/trend')
@require_api_key
@cached(ttl=300, key_prefix="swap_trend")
def get_swap_trend():
    """
    Get swap trend over time for timeline chart.
    
    Query params:
        period: 7d|30d (default 7d)
    """
    period = request.args.get('period', '7d')
    from_date, to_date = _parse_period_dates(period)
    
    try:
        if not data_processor.supabase:
            return api_response(error="Database not available", status=503)
        
        result = data_processor.supabase.table("aircraft_swaps") \
            .select("flight_date") \
            .gte("flight_date", from_date.isoformat()) \
            .lte("flight_date", to_date.isoformat()) \
            .execute()
        
        swaps = result.data or []
        
        # Build daily counts
        from collections import Counter
        day_counts = Counter(s["flight_date"] for s in swaps)
        
        labels = []
        values = []
        current = from_date
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        while current <= to_date:
            iso = current.isoformat()
            if period == '7d':
                labels.append(day_names[current.weekday()])
            else:
                labels.append(current.strftime('%d/%m'))
            values.append(day_counts.get(iso, 0))
            current += timedelta(days=1)
        
        return api_response({
            "labels": labels,
            "datasets": {"swaps": values}
        })
        
    except Exception as e:
        logger.error(f"Swap trend failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Frontend Routes
# =========================================================

@app.route('/')
def index():
    """Serve main dashboard page."""
    return render_template('crew_dashboard.html', active_page='dashboard')


@app.route('/operations')
def operations_overview():
    """Serve operations overview dashboard."""
    return render_template('operations_overview.html', active_page='operations')


@app.route('/fleet-health')
def fleet_health():
    """Serve fleet health dashboard."""
    return render_template('fleet_health.html', active_page='fleet')


@app.route('/crew-pairing')
def crew_pairing():
    """Serve crew pairing dashboard."""
    return render_template('crew_pairing.html', active_page='pairing')


@app.route('/aircraft-swap')
def aircraft_swap():
    """Serve aircraft swap analysis dashboard."""
    return render_template('aircraft_swap.html', active_page='swap')


@app.route('/ftl-list')
def ftl_list():
    """Serve FTL list page."""
    return render_template('ftl_list.html', active_page='ftl')


@app.route('/users')
def user_management():
    """Serve user management page."""
    return render_template('user_management.html', active_page='users')


@app.route('/data-etl')
def data_etl():
    """Serve data ETL monitoring page."""
    return render_template('data_etl.html', active_page='etl')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)


# =========================================================
# Export Endpoints
# =========================================================

@app.route('/api/export/<export_type>')
def export_data(export_type: str):
    """
    Export data in various formats.
    
    Args:
        export_type: Type of export (crew, flights, standby, hours, report)
        
    Query params:
        date: YYYY-MM-DD format
        format: csv, xlsx, pdf (default: csv)
    """
    target_date = parse_date_param(request.args.get('date'))
    export_format = request.args.get('format', 'csv').lower()
    
    try:
        from exports import export_service
        
        # Get data based on type
        if export_type == 'crew':
            data = export_service.export_crew_list(format=export_format)
            filename = f"crew_list_{target_date}.{export_format}"
        elif export_type == 'flights':
            data = export_service.export_flights(target_date, format=export_format)
            filename = f"flights_{target_date}.{export_format}"
        elif export_type == 'standby':
            data = export_service.export_standby(target_date, format=export_format)
            filename = f"standby_{target_date}.{export_format}"
        elif export_type == 'hours':
            data = export_service.export_flight_hours(target_date, format=export_format)
            filename = f"flight_hours_{target_date}.{export_format}"
        elif export_type == 'report':
            data = export_service.export_full_report(target_date, format='xlsx')
            filename = f"dashboard_report_{target_date}.xlsx"
            export_format = 'xlsx'
        else:
            return api_response(error=f"Unknown export type: {export_type}", status=400)
        
        # Set content type
        content_types = {
            'csv': 'text/csv',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf'
        }
        
        content_type = content_types.get(export_format, 'application/octet-stream')
        
        return Response(
            data,
            mimetype=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': len(data)
            }
        )
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Alert System Endpoints
# =========================================================

@app.route('/api/alerts')
def get_alerts():
    """
    Get active alerts.
    
    Query params:
        severity: Filter by severity (info, warning, critical)
        type: Filter by alert type
        limit: Max number of alerts (default 50)
    """
    severity = request.args.get('severity', '')
    alert_type = request.args.get('type', '')
    limit = request.args.get('limit', 50, type=int)
    
    try:
        from alerts import alert_manager, AlertSeverity, AlertType
        
        severity_filter = AlertSeverity(severity) if severity else None
        type_filter = AlertType(alert_type) if alert_type else None
        
        alerts = alert_manager.service.get_active_alerts(
            severity=severity_filter,
            alert_type=type_filter,
            limit=limit
        )
        
        return api_response({
            "total": len(alerts),
            "alerts": [a.to_dict() for a in alerts]
        })
        
    except ValueError as e:
        return api_response(error=f"Invalid filter: {e}", status=400)
    except Exception as e:
        logger.error(f"Get alerts failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/alerts/<alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id: str):
    """
    Acknowledge an alert.
    
    Args:
        alert_id: Alert ID to acknowledge
    """
    try:
        from alerts import alert_manager
        
        body = request.get_json() or {}
        user = body.get('user', 'system')
        
        success = alert_manager.service.acknowledge_alert(alert_id, user)
        
        if success:
            return api_response({"message": "Alert acknowledged", "alert_id": alert_id})
        else:
            return api_response(error="Alert not found", status=404)
            
    except Exception as e:
        logger.error(f"Acknowledge alert failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/alerts/summary')
def get_alerts_summary():
    """Get alert summary."""
    try:
        from alerts import alert_manager
        
        summary = alert_manager.get_summary()
        return api_response(summary)
        
    except Exception as e:
        logger.error(f"Get alert summary failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Cache Management Endpoints
# =========================================================

@app.route('/api/cache/status')
def get_cache_status():
    """Get cache status."""
    try:
        from cache import cache
        return api_response(cache.status())
    except Exception as e:
        return api_response(error=str(e), status=500)


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all cache."""
    try:
        from cache import cache
        cache.clear()
        return api_response({"message": "Cache cleared"})
    except Exception as e:
        logger.error(f"Clear cache failed: {e}")
        return api_response(error=str(e), status=500)


@app.route('/api/admin/sync-force')
@require_api_key
def force_sync_now():
    """Manually trigger AIMS sync in background with cooldown."""
    if _is_syncing:
        return api_response(error="Sync already in progress", status=429)
        
    try:
        # 15-minute cooldown for manual force sync to protect AIMS
        if data_processor.supabase:
            last_sync = data_processor.supabase.table("etl_jobs") \
                .select("completed_at") \
                .eq("job_name", "AIMS Sync") \
                .eq("status", "SUCCESS") \
                .order("completed_at", desc=True) \
                .limit(1) \
                .execute()
            
            if last_sync.data:
                last_time = datetime.fromisoformat(last_sync.data[0]["completed_at"])
                if datetime.now() - last_time < timedelta(minutes=15):
                    return api_response(error="Force sync cooldown active (15m)", status=429)

        # Run in background thread to avoid blocking request
        thread = threading.Thread(target=sync_aims_data)
        thread.daemon = True
        thread.start()
        return api_response({"message": "Sync job initiated in background"})
    except Exception as e:
        logger.error(f"Force sync failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Error Handlers
# =========================================================

@app.errorhandler(404)
def not_found(e):
    return api_response(error="Not found", status=404)


@app.errorhandler(500)
def server_error(e):
    return api_response(error="Internal server error", status=500)


@app.errorhandler(429)
def rate_limit_error(e):
    return api_response(error="Too many requests. Please try again later.", status=429)


# =========================================================
# Main Entry Point
# =========================================================

# Background task initialization
def start_background_tasks():
    """Initialize background jobs and cleanup."""
    # Clean up stuck jobs
    _cleanup_stuck_jobs()
    
    # Start Scheduler
    if scheduler:
        # Sync interval
        interval = int(os.getenv("SYNC_INTERVAL_MINUTES", 5))
        try:
            # Check if job already exists to avoid duplicates on reload
            if not scheduler.get_job('aims_sync_job'):
                scheduler.add_job(
                    func=sync_aims_data,
                    trigger=IntervalTrigger(minutes=interval),
                    id='aims_sync_job',
                    name='Sync AIMS Data',
                    replace_existing=True
                )
            
            if not scheduler.running:
                scheduler.start()
                logger.info(f"Scheduler started with {interval}m interval")
                # Shut down scheduler when exiting the app
                atexit.register(lambda: scheduler.shutdown())
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

# Call startup tasks immediately upon import/load in background
# Use thread to avoid blocking server startup if cleanup is slow
startup_thread = threading.Thread(target=start_background_tasks)
startup_thread.daemon = True
startup_thread.start()

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    
    print("="*60)
    print("Aviation Operations Dashboard - API Server")
    print("="*60)
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Data Source: {data_processor.data_source}")
    print("="*60)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
