-- =====================================================
-- Aviation Operations Dashboard - RESET Schema
-- WARNING: This will DELETE existing data in these tables!
-- =====================================================

-- 1. Drop existing tables (to fix schema mismatches)
DROP TABLE IF EXISTS etl_jobs CASCADE;
DROP TABLE IF EXISTS fact_actuals CASCADE;
DROP TABLE IF EXISTS fact_roster CASCADE;
DROP TABLE IF EXISTS standby_records CASCADE;
DROP TABLE IF EXISTS flights CASCADE;
DROP TABLE IF EXISTS crew_flight_hours CASCADE;
DROP TABLE IF EXISTS crew_qualifications CASCADE;
DROP TABLE IF EXISTS crew_roster CASCADE; -- Old table name
DROP TABLE IF EXISTS crew_members CASCADE;

-- 2. Re-create tables with correct schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: crew_members
CREATE TABLE crew_members (
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

CREATE INDEX idx_crew_members_base ON crew_members(base);
CREATE INDEX idx_crew_members_crew_id ON crew_members(crew_id);

-- Table: crew_flight_hours
CREATE TABLE crew_flight_hours (
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

CREATE INDEX idx_crew_flight_hours_date ON crew_flight_hours(calculation_date);
CREATE INDEX idx_crew_flight_hours_warning ON crew_flight_hours(warning_level);

-- Table: flights
CREATE TABLE flights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flight_date DATE NOT NULL,
    carrier_code VARCHAR(3),
    flight_number VARCHAR(20) NOT NULL,
    departure VARCHAR(4) NOT NULL,
    arrival VARCHAR(4) NOT NULL,
    std TIME,
    sta TIME,
    atd TIME,
    ata TIME,
    aircraft_type VARCHAR(10),
    aircraft_reg VARCHAR(15),
    status VARCHAR(20) DEFAULT 'SCHEDULED',
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(flight_date, flight_number)
);

CREATE INDEX idx_flights_date ON flights(flight_date);
CREATE INDEX idx_flights_aircraft ON flights(aircraft_reg);
CREATE INDEX idx_flights_status ON flights(status);

-- Table: standby_records
CREATE TABLE standby_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id VARCHAR(50) NOT NULL,
    crew_name VARCHAR(200),
    status VARCHAR(10) NOT NULL,
    duty_start_date DATE NOT NULL,
    duty_end_date DATE NOT NULL,
    base VARCHAR(10),
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_standby_dates ON standby_records(duty_start_date, duty_end_date);
CREATE INDEX idx_standby_status ON standby_records(status);

-- Table: fact_roster
CREATE TABLE fact_roster (
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

CREATE INDEX idx_fact_roster_crew ON fact_roster(crew_id);
CREATE INDEX idx_fact_roster_start ON fact_roster(start_dt);

-- Table: fact_actuals
CREATE TABLE fact_actuals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id VARCHAR(50) NOT NULL,
    block_minutes INTEGER DEFAULT 0,
    dep_actual_dt TIMESTAMP WITH TIME ZONE,
    ac_reg VARCHAR(15),
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_fact_actuals_crew ON fact_actuals(crew_id);
CREATE INDEX idx_fact_actuals_date ON fact_actuals(dep_actual_dt);

-- Table: etl_jobs
CREATE TABLE etl_jobs (
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

CREATE INDEX idx_etl_jobs_status ON etl_jobs(status);

-- Function: update_updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
CREATE TRIGGER update_crew_members_timestamp BEFORE UPDATE ON crew_members FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER update_crew_flight_hours_timestamp BEFORE UPDATE ON crew_flight_hours FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER update_flights_timestamp BEFORE UPDATE ON flights FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER update_standby_records_timestamp BEFORE UPDATE ON standby_records FOR EACH ROW EXECUTE FUNCTION update_updated_at();

