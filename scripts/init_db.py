"""
Database Initialization Script
Phase 1: Foundation Setup

Creates all required tables in Supabase for the Aviation Operations Dashboard.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_supabase_client() -> Client:
    """Create and return Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# Table definitions (for documentation - actual creation done in Supabase dashboard)
TABLE_DEFINITIONS = """
-- =====================================================
-- Aviation Operations Dashboard - Database Schema
-- Run these in Supabase SQL Editor
-- =====================================================

-- 1. Crew Members
CREATE TABLE IF NOT EXISTS crew_members (
    id SERIAL PRIMARY KEY,
    crew_id VARCHAR(20) UNIQUE NOT NULL,
    crew_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    three_letter_code VARCHAR(3),
    gender CHAR(1),
    base VARCHAR(10),
    email VARCHAR(100),
    cell_phone VARCHAR(20),
    employment_begin DATE,
    employment_end DATE,
    updated_at TIMESTAMP DEFAULT NOW(),
    source VARCHAR(10) DEFAULT 'AIMS'
);

-- 2. Crew Qualifications
CREATE TABLE IF NOT EXISTS crew_qualifications (
    id SERIAL PRIMARY KEY,
    crew_id VARCHAR(20) REFERENCES crew_members(crew_id) ON DELETE CASCADE,
    qual_base VARCHAR(10),
    qual_aircraft VARCHAR(10),
    qual_position VARCHAR(10),
    roster_group SMALLINT,
    qual_begin_date DATE,
    qual_end_date DATE,
    is_primary BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. Crew Roster/Schedule
CREATE TABLE IF NOT EXISTS crew_roster (
    id SERIAL PRIMARY KEY,
    crew_id VARCHAR(20),
    duty_date DATE NOT NULL,
    duty_code VARCHAR(10),
    duty_description VARCHAR(100),
    start_time TIME,
    end_time TIME,
    flight_number VARCHAR(10),
    departure VARCHAR(5),
    arrival VARCHAR(5),
    aircraft_type VARCHAR(10),
    aircraft_reg VARCHAR(10),
    source VARCHAR(10) DEFAULT 'AIMS',
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. Standby Records (SBY, SL, CSL)
CREATE TABLE IF NOT EXISTS standby_records (
    id SERIAL PRIMARY KEY,
    crew_id VARCHAR(20),
    crew_name VARCHAR(100),
    duty_start_date DATE,
    duty_end_date DATE,
    status VARCHAR(10),  -- SBY, SL, CSL
    base VARCHAR(10),
    source VARCHAR(10) DEFAULT 'AIMS',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. Flights
CREATE TABLE IF NOT EXISTS flights (
    id SERIAL PRIMARY KEY,
    flight_date DATE NOT NULL,
    carrier_code VARCHAR(3),
    flight_number INTEGER,
    leg_code VARCHAR(5),
    departure VARCHAR(5),
    arrival VARCHAR(5),
    std TIME,
    sta TIME,
    etd TIME,
    eta TIME,
    atd TIME,
    ata TIME,
    aircraft_reg VARCHAR(10),
    aircraft_type VARCHAR(10),
    status VARCHAR(20),
    delay_code VARCHAR(10),
    delay_minutes INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 6. Crew Flight Hours (FTL Tracking)
CREATE TABLE IF NOT EXISTS crew_flight_hours (
    id SERIAL PRIMARY KEY,
    crew_id VARCHAR(20),
    calculation_date DATE,
    hours_28_day DECIMAL(6,2) DEFAULT 0,
    hours_12_month DECIMAL(8,2) DEFAULT 0,
    warning_level VARCHAR(20) DEFAULT 'NORMAL',  -- NORMAL, WARNING, CRITICAL
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(crew_id, calculation_date)
);

-- 7. Sync Log (for monitoring)
CREATE TABLE IF NOT EXISTS sync_log (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50),
    status VARCHAR(20),
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_crew_roster_date ON crew_roster(duty_date);
CREATE INDEX IF NOT EXISTS idx_crew_roster_crew_id ON crew_roster(crew_id);
CREATE INDEX IF NOT EXISTS idx_flights_date ON flights(flight_date);
CREATE INDEX IF NOT EXISTS idx_standby_dates ON standby_records(duty_start_date, duty_end_date);
CREATE INDEX IF NOT EXISTS idx_flight_hours_crew ON crew_flight_hours(crew_id);
"""


def verify_connection():
    """Verify Supabase connection."""
    try:
        client = get_supabase_client()
        # Try a simple query
        result = client.table("crew_members").select("count", count="exact").execute()
        print("✅ Supabase connection successful!")
        print(f"   crew_members table exists with {result.count or 0} records")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def print_schema():
    """Print the SQL schema for manual creation."""
    print("\n" + "="*60)
    print("DATABASE SCHEMA - Run in Supabase SQL Editor:")
    print("="*60)
    print(TABLE_DEFINITIONS)


def main():
    """Main initialization function."""
    print("="*60)
    print("Aviation Operations Dashboard - Database Initialization")
    print("="*60)
    
    # Check environment
    print("\n📋 Checking environment variables...")
    if SUPABASE_URL:
        print(f"   SUPABASE_URL: {SUPABASE_URL[:30]}...")
    else:
        print("   ❌ SUPABASE_URL not set!")
        
    if SUPABASE_KEY:
        print(f"   SUPABASE_KEY: {SUPABASE_KEY[:20]}...")
    else:
        print("   ❌ SUPABASE_KEY not set!")
    
    # Verify connection
    print("\n🔌 Testing Supabase connection...")
    if verify_connection():
        print("\n✅ Database ready!")
    else:
        print("\n⚠️  Please configure Supabase and create tables manually.")
        print_schema()


if __name__ == "__main__":
    main()
