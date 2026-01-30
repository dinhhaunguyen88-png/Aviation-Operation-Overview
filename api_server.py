"""
Flask API Server
Phase 2: Data Integration + Security Hardening

REST API endpoints for Aviation Operations Dashboard.
"""

import os
import logging
from datetime import date, datetime
from functools import wraps

from flask import Flask, jsonify, request, render_template, send_from_directory, Response
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Secret key
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# =========================================================
# CORS Configuration (Security Hardening)
# =========================================================

CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv("CORS_ORIGINS", "*").split(","),
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "X-API-Key", "Authorization"]
    }
})

# =========================================================
# Rate Limiting (Security Hardening)
# =========================================================

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=os.getenv("REDIS_URL", "memory://"),
        strategy="fixed-window"
    )
    logger.info("Rate limiting enabled")
except ImportError:
    limiter = None
    logger.warning("Flask-Limiter not installed, rate limiting disabled")

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

from data_processor import DataProcessor

data_processor = DataProcessor(
    data_source=os.getenv("AIMS_SYNC_ENABLED", "true").lower() == "true" and "AIMS" or "CSV"
)


# =========================================================
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
# Dashboard Endpoints
# =========================================================

@app.route('/api/dashboard/summary')
def get_dashboard_summary():
    """
    Get dashboard summary with all KPIs.
    
    Query params:
        date: YYYY-MM-DD format (optional, defaults to today)
    """
    target_date = parse_date_param(request.args.get('date'))
    
    try:
        summary = data_processor.get_dashboard_summary(target_date)
        return api_response(summary)
    except Exception as e:
        logger.error(f"Dashboard summary failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Crew Endpoints
# =========================================================

@app.route('/api/crew')
def get_crew_list():
    """
    Get list of crew members.
    
    Query params:
        date: YYYY-MM-DD format
        base: Filter by base code
        status: Filter by status (SBY, SL, CSL, etc.)
        page: Page number (default 1)
        per_page: Items per page (default 50)
    """
    target_date = parse_date_param(request.args.get('date'))
    base = request.args.get('base', '')
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    try:
        if data_processor.supabase:
            query = data_processor.supabase.table("crew_members").select("*")
            
            if base:
                query = query.eq("base", base)
            
            # Pagination
            start = (page - 1) * per_page
            query = query.range(start, start + per_page - 1)
            
            result = query.execute()
            
            return api_response({
                "crew": result.data or [],
                "page": page,
                "per_page": per_page,
                "total": len(result.data or [])
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
        
        if aircraft_type:
            flights = [f for f in flights if f.get('aircraft_type') == aircraft_type]
        
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
def get_ftl_summary():
    """
    Get FTL (Flight Time Limitations) summary.
    
    Query params:
        date: YYYY-MM-DD format
    """
    target_date = parse_date_param(request.args.get('date'))
    
    try:
        crew_hours = data_processor.get_crew_hours(target_date)
        
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
        
        return api_response({
            "message": f"Processed {len(records)} records",
            "file_type": file_type,
            "records_count": len(records)
        })
        
    except Exception as e:
        logger.error(f"CSV upload failed: {e}")
        return api_response(error=str(e), status=500)


# =========================================================
# Frontend Routes
# =========================================================

@app.route('/')
def index():
    """Serve main dashboard page."""
    return render_template('crew_dashboard.html')


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


# =========================================================
# Error Handlers
# =========================================================

@app.errorhandler(404)
def not_found(e):
    return api_response(error="Not found", status=404)


@app.errorhandler(500)
def server_error(e):
    return api_response(error="Internal server error", status=500)


# =========================================================
# Main Entry Point
# =========================================================

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
