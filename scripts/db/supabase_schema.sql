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

-- =====================================================
-- Table: users (for RBAC)
-- Stores dashboard user accounts
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer',  -- admin, manager, analyst, viewer
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- Row Level Security (RLS) - Optional
-- =====================================================
-- Enable RLS on tables
ALTER TABLE crew_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE crew_flight_hours ENABLE ROW LEVEL SECURITY;
ALTER TABLE flights ENABLE ROW LEVEL SECURITY;
ALTER TABLE standby_records ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read all data
CREATE POLICY "Allow read access for authenticated users" ON crew_members
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow read access for authenticated users" ON crew_flight_hours
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow read access for authenticated users" ON flights
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow read access for authenticated users" ON standby_records
    FOR SELECT USING (auth.role() = 'authenticated');

-- Allow service role to do everything (for API access)
CREATE POLICY "Allow all for service role" ON crew_members
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow all for service role" ON crew_flight_hours
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow all for service role" ON flights
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow all for service role" ON standby_records
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- Function: Update timestamp trigger
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables
CREATE TRIGGER update_crew_members_timestamp
    BEFORE UPDATE ON crew_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_crew_flight_hours_timestamp
    BEFORE UPDATE ON crew_flight_hours
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_flights_timestamp
    BEFORE UPDATE ON flights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_standby_records_timestamp
    BEFORE UPDATE ON standby_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =====================================================
-- Seed Data (Optional - for testing)
-- =====================================================
-- INSERT INTO crew_members (crew_id, crew_name, first_name, last_name, base, gender)
-- VALUES 
--     ('C001', 'Nguyen Van A', 'Van A', 'Nguyen', 'SGN', 'M'),
--     ('C002', 'Tran Thi B', 'Thi B', 'Tran', 'HAN', 'F'),
--     ('C003', 'Le Van C', 'Van C', 'Le', 'DAD', 'M');

COMMENT ON TABLE crew_members IS 'Crew member master data';
COMMENT ON TABLE crew_flight_hours IS 'FTL flight hours tracking';
COMMENT ON TABLE flights IS 'Flight schedule and status';
COMMENT ON TABLE standby_records IS 'Standby, sick leave, and other duty records';
COMMENT ON TABLE etl_jobs IS 'ETL job execution history';
COMMENT ON TABLE users IS 'Dashboard user accounts for RBAC';
