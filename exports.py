"""
Export Module
Phase 4: Advanced Features

Handles data export to CSV, Excel, and PDF formats.
"""

import os
import io
import csv
import logging
from datetime import date, datetime
from typing import List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# =====================================================
# CSV Export
# =====================================================

def export_to_csv(data: List[Dict[str, Any]], filename: str = None) -> bytes:
    """
    Export data to CSV format.
    
    Args:
        data: List of dictionaries to export
        filename: Optional filename (not used, just for reference)
        
    Returns:
        CSV content as bytes
    """
    if not data:
        return b""
    
    output = io.StringIO()
    
    # Get headers from first row
    headers = list(data[0].keys())
    
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue().encode('utf-8-sig')


def export_crew_list(crew_data: List[Dict[str, Any]]) -> bytes:
    """
    Export crew list to CSV.
    
    Args:
        crew_data: Crew records
        
    Returns:
        CSV content as bytes
    """
    # Flatten and format data
    export_data = []
    
    for crew in crew_data:
        export_data.append({
            "Crew ID": crew.get("crew_id", ""),
            "Name": crew.get("crew_name", ""),
            "First Name": crew.get("first_name", ""),
            "Last Name": crew.get("last_name", ""),
            "Base": crew.get("base", ""),
            "Position": crew.get("position", ""),
            "Email": crew.get("email", ""),
            "Phone": crew.get("cell_phone", ""),
            "Status": crew.get("status", ""),
        })
    
    return export_to_csv(export_data)


def export_flight_hours(crew_hours: List[Dict[str, Any]]) -> bytes:
    """
    Export crew flight hours to CSV.
    
    Args:
        crew_hours: Crew flight hour records
        
    Returns:
        CSV content as bytes
    """
    export_data = []
    
    for crew in crew_hours:
        export_data.append({
            "Crew ID": crew.get("crew_id", ""),
            "Name": crew.get("crew_name", ""),
            "28-Day Hours": crew.get("hours_28_day", 0),
            "12-Month Hours": crew.get("hours_12_month", 0),
            "Warning Level": crew.get("warning_level", "NORMAL"),
            "Calculation Date": crew.get("calculation_date", ""),
        })
    
    return export_to_csv(export_data)


def export_flights(flight_data: List[Dict[str, Any]]) -> bytes:
    """
    Export flights to CSV.
    
    Args:
        flight_data: Flight records
        
    Returns:
        CSV content as bytes
    """
    export_data = []
    
    for flight in flight_data:
        export_data.append({
            "Flight Date": flight.get("flight_date", ""),
            "Carrier": flight.get("carrier_code", ""),
            "Flight Number": flight.get("flight_number", ""),
            "Departure": flight.get("departure", ""),
            "Arrival": flight.get("arrival", ""),
            "STD": flight.get("std", ""),
            "STA": flight.get("sta", ""),
            "Aircraft Type": flight.get("aircraft_type", ""),
            "Aircraft Reg": flight.get("aircraft_reg", ""),
            "Status": flight.get("status", ""),
        })
    
    return export_to_csv(export_data)


def export_standby(standby_data: List[Dict[str, Any]]) -> bytes:
    """
    Export standby records to CSV.
    
    Args:
        standby_data: Standby records
        
    Returns:
        CSV content as bytes
    """
    export_data = []
    
    for record in standby_data:
        export_data.append({
            "Crew ID": record.get("crew_id", ""),
            "Name": record.get("crew_name", ""),
            "Status": record.get("status", ""),
            "Start Date": record.get("duty_start_date", ""),
            "End Date": record.get("duty_end_date", ""),
            "Base": record.get("base", ""),
        })
    
    return export_to_csv(export_data)


def export_alerts(alerts: List[Dict[str, Any]]) -> bytes:
    """
    Export alerts to CSV.
    
    Args:
        alerts: Alert records
        
    Returns:
        CSV content as bytes
    """
    export_data = []
    
    for alert in alerts:
        export_data.append({
            "ID": alert.get("id", ""),
            "Type": alert.get("alert_type", ""),
            "Severity": alert.get("severity", ""),
            "Title": alert.get("title", ""),
            "Message": alert.get("message", ""),
            "Crew ID": alert.get("crew_id", ""),
            "Created At": alert.get("created_at", ""),
            "Acknowledged": alert.get("acknowledged", False),
        })
    
    return export_to_csv(export_data)


# =====================================================
# Excel Export
# =====================================================

def export_to_excel(
    sheets: Dict[str, List[Dict[str, Any]]],
    filename: str = None
) -> bytes:
    """
    Export data to Excel format with multiple sheets.
    
    Args:
        sheets: Dictionary of sheet_name -> data
        filename: Optional filename
        
    Returns:
        Excel file as bytes
    """
    try:
        import pandas as pd
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in sheets.items():
                if data:
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        
        return output.getvalue()
        
    except ImportError:
        logger.warning("pandas/openpyxl not installed, falling back to CSV")
        # Fallback to CSV for first sheet
        first_sheet = list(sheets.values())[0] if sheets else []
        return export_to_csv(first_sheet)


def export_dashboard_report(
    summary: Dict[str, Any],
    crew_hours: List[Dict[str, Any]],
    flights: List[Dict[str, Any]],
    standby: List[Dict[str, Any]]
) -> bytes:
    """
    Export complete dashboard report.
    
    Args:
        summary: Dashboard summary data
        crew_hours: Crew flight hours
        flights: Flight data
        standby: Standby records
        
    Returns:
        Excel file as bytes
    """
    # Prepare summary sheet
    summary_rows = [
        {"Metric": "Report Date", "Value": summary.get("date", "")},
        {"Metric": "Total Crew", "Value": summary.get("total_crew", 0)},
        {"Metric": "Total Flights", "Value": summary.get("total_flights", 0)},
        {"Metric": "Total Block Hours", "Value": summary.get("total_block_hours", 0)},
        {"Metric": "Aircraft Utilization", "Value": summary.get("aircraft_utilization", 0)},
        {"Metric": "Standby Available", "Value": summary.get("standby_available", 0)},
        {"Metric": "Sick Leave", "Value": summary.get("sick_leave", 0)},
        {"Metric": "Active Alerts", "Value": summary.get("alerts_count", 0)},
    ]
    
    # Add crew status breakdown
    if summary.get("crew_by_status"):
        for status, count in summary["crew_by_status"].items():
            summary_rows.append({"Metric": f"Crew - {status}", "Value": count})
    
    sheets = {
        "Summary": summary_rows,
        "Crew Flight Hours": crew_hours,
        "Flights": flights,
        "Standby": standby
    }
    
    return export_to_excel(sheets)


# =====================================================
# PDF Export (using reportlab)
# =====================================================

def export_to_pdf(
    title: str,
    data: List[Dict[str, Any]],
    filename: str = None
) -> bytes:
    """
    Export data to PDF format.
    
    Args:
        title: Report title
        data: Data to export
        filename: Optional filename
        
    Returns:
        PDF file as bytes
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        
        output = io.BytesIO()
        
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 20))
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated: {timestamp}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        if data:
            # Headers
            headers = list(data[0].keys())
            
            # Table data
            table_data = [headers]
            for row in data:
                table_data.append([str(row.get(h, "")) for h in headers])
            
            # Create table
            table = Table(table_data)
            
            # Style
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ])
            
            table.setStyle(style)
            elements.append(table)
        else:
            elements.append(Paragraph("No data available", styles['Normal']))
        
        doc.build(elements)
        return output.getvalue()
        
    except ImportError:
        logger.warning("reportlab not installed, PDF export not available")
        return b""


# =====================================================
# Export Service
# =====================================================

class ExportService:
    """
    Service for handling all exports.
    """
    
    def __init__(self):
        self._data_processor = None
    
    @property
    def data_processor(self):
        """Lazy load data processor."""
        if self._data_processor is None:
            from data_processor import DataProcessor
            self._data_processor = DataProcessor()
        return self._data_processor
    
    def export_crew_list(self, format: str = "csv") -> bytes:
        """Export crew list."""
        crew = self.data_processor.get_crew_hours()
        
        if format == "csv":
            return export_crew_list(crew)
        elif format == "xlsx":
            return export_to_excel({"Crew": crew})
        elif format == "pdf":
            return export_to_pdf("Crew List", crew)
        
        return b""
    
    def export_flight_hours(
        self,
        target_date: date = None,
        format: str = "csv"
    ) -> bytes:
        """Export crew flight hours."""
        crew_hours = self.data_processor.get_crew_hours(target_date)
        
        if format == "csv":
            return export_flight_hours(crew_hours)
        elif format == "xlsx":
            return export_to_excel({"Flight Hours": crew_hours})
        elif format == "pdf":
            return export_to_pdf("Crew Flight Hours", crew_hours)
        
        return b""
    
    def export_flights(
        self,
        target_date: date = None,
        format: str = "csv"
    ) -> bytes:
        """Export flights."""
        flights = self.data_processor.get_flights(target_date)
        
        if format == "csv":
            return export_flights(flights)
        elif format == "xlsx":
            return export_to_excel({"Flights": flights})
        elif format == "pdf":
            return export_to_pdf("Flights", flights)
        
        return b""
    
    def export_standby(
        self,
        target_date: date = None,
        format: str = "csv"
    ) -> bytes:
        """Export standby records."""
        standby = self.data_processor.get_standby_records(target_date)
        
        if format == "csv":
            return export_standby(standby)
        elif format == "xlsx":
            return export_to_excel({"Standby": standby})
        elif format == "pdf":
            return export_to_pdf("Standby Records", standby)
        
        return b""
    
    def export_full_report(
        self,
        target_date: date = None,
        format: str = "xlsx"
    ) -> bytes:
        """Export full dashboard report."""
        target_date = target_date or date.today()
        
        summary = self.data_processor.get_dashboard_summary(target_date)
        crew_hours = self.data_processor.get_crew_hours(target_date)
        flights = self.data_processor.get_flights(target_date)
        standby = self.data_processor.get_standby_records(target_date)
        
        if format == "xlsx":
            return export_dashboard_report(summary, crew_hours, flights, standby)
        elif format == "csv":
            return export_crew_list(crew_hours)
        
        return b""


# Singleton
export_service = ExportService()


# =====================================================
# Test
# =====================================================

if __name__ == "__main__":
    print("="*60)
    print("Export Module Test")
    print("="*60)
    
    # Test CSV export
    test_data = [
        {"id": 1, "name": "Test 1", "value": 100},
        {"id": 2, "name": "Test 2", "value": 200},
    ]
    
    csv_output = export_to_csv(test_data)
    print(f"\nCSV Output ({len(csv_output)} bytes):")
    print(csv_output.decode()[:200])
    
    print("\nExport module initialized successfully!")
