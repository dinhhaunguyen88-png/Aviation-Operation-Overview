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
-- Aviation Operations Dashboard - Supabase Schema
-- Run this in Supabase SQL Editor
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- Table: crew_members
-- Stores crew member information
-- =====================================================
CREATE TABLE IF NOT EXISTS crew_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id VARCHAR(50) UNIQUE NOT NULL,
    crew_name VARCHAR(200) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    three_letter_code VARCHAR(3),
    gender VARCHAR(1) CHECK (gender IN ('M', 'F')),
    email VARCHAR(255),
    cell_phone VARCHAR(50),
    base VARCHAR(10),
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_crew_members_base ON crew_members(base);
CREATE INDEX IF NOT EXISTS idx_crew_members_crew_id ON crew_members(crew_id);

-- =====================================================
-- Table: crew_flight_hours
-- Stores crew flight hours for FTL calculations
-- =====================================================
CREATE TABLE IF NOT EXISTS crew_flight_hours (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id VARCHAR(50) NOT NULL,
    crew_name VARCHAR(200),
    hours_28_day DECIMAL(10, 2) DEFAULT 0,
    hours_12_month DECIMAL(10, 2) DEFAULT 0,
    warning_level VARCHAR(20) DEFAULT 'NORMAL',
    calculation_date DATE NOT NULL,
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(crew_id, calculation_date)
);

-- Index for date queries
CREATE INDEX IF NOT EXISTS idx_crew_flight_hours_date ON crew_flight_hours(calculation_date);
CREATE INDEX IF NOT EXISTS idx_crew_flight_hours_warning ON crew_flight_hours(warning_level);

-- =====================================================
-- Table: flights
-- Stores flight information
-- =====================================================
CREATE TABLE IF NOT EXISTS flights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flight_date DATE NOT NULL,
    carrier_code VARCHAR(3),
    flight_number VARCHAR(20) NOT NULL,
    departure VARCHAR(4) NOT NULL,
    arrival VARCHAR(4) NOT NULL,
    std TIME,  -- Scheduled Time of Departure
    sta TIME,  -- Scheduled Time of Arrival
    atd TIME,  -- Actual Time of Departure
    ata TIME,  -- Actual Time of Arrival
    aircraft_type VARCHAR(10),
    aircraft_reg VARCHAR(15),
    status VARCHAR(20) DEFAULT 'SCHEDULED',
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(flight_date, flight_number)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_flights_date ON flights(flight_date);
CREATE INDEX IF NOT EXISTS idx_flights_aircraft ON flights(aircraft_reg);
CREATE INDEX IF NOT EXISTS idx_flights_status ON flights(status);

-- =====================================================
-- Table: standby_records
-- Stores standby duty records
-- =====================================================
CREATE TABLE IF NOT EXISTS standby_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id VARCHAR(50) NOT NULL,
    crew_name VARCHAR(200),
    status VARCHAR(10) NOT NULL,  -- SBY, SL, CSL, OFF, TRN, LVE
    duty_start_date DATE NOT NULL,
    duty_end_date DATE NOT NULL,
    base VARCHAR(10),
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_standby_dates ON standby_records(duty_start_date, duty_end_date);
CREATE INDEX IF NOT EXISTS idx_standby_status ON standby_records(status);

-- =====================================================
-- Table: fact_roster
-- Stores detailed crew roster (activities/flights)
-- =====================================================
CREATE TABLE IF NOT EXISTS fact_roster (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id VARCHAR(50) NOT NULL,
    activity_type VARCHAR(20),
    start_dt TIMESTAMP WITH TIME ZONE,
    end_dt TIMESTAMP WITH TIME ZONE,
    flight_no VARCHAR(20),
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_roster_crew ON fact_roster(crew_id);
CREATE INDEX IF NOT EXISTS idx_fact_roster_start ON fact_roster(start_dt);

-- =====================================================
-- Table: fact_actuals
-- Stores actual block hours for FTL
-- =====================================================
CREATE TABLE IF NOT EXISTS fact_actuals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id VARCHAR(50) NOT NULL,
    block_minutes INTEGER DEFAULT 0,
    dep_actual_dt TIMESTAMP WITH TIME ZONE,
    ac_reg VARCHAR(15),
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_actuals_crew ON fact_actuals(crew_id);
CREATE INDEX IF NOT EXISTS idx_fact_actuals_date ON fact_actuals(dep_actual_dt);

-- =====================================================
-- Table: etl_jobs
-- Tracks ETL job history
-- =====================================================
CREATE TABLE IF NOT EXISTS etl_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name VARCHAR(100) NOT NULL,
    file_name VARCHAR(255),
    file_type VARCHAR(50),
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Index
CREATE INDEX IF NOT EXISTS idx_etl_jobs_status ON etl_jobs(status);
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
