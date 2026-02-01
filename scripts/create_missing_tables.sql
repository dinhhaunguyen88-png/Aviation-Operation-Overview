-- =====================================================
-- Aviation Dashboard - Create Missing Tables & Fix RLS
-- Run this in Supabase SQL Editor
-- =====================================================

-- 1. Create Tables
-- -----------------------------------------------------

-- Table: crew_members
CREATE TABLE IF NOT EXISTS crew_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

CREATE INDEX IF NOT EXISTS idx_crew_members_base ON crew_members(base);
CREATE INDEX IF NOT EXISTS idx_crew_members_crew_id ON crew_members(crew_id);

-- Table: crew_flight_hours  
CREATE TABLE IF NOT EXISTS crew_flight_hours (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

CREATE INDEX IF NOT EXISTS idx_crew_flight_hours_date ON crew_flight_hours(calculation_date);
CREATE INDEX IF NOT EXISTS idx_crew_flight_hours_warning ON crew_flight_hours(warning_level);

-- Table: standby_records
CREATE TABLE IF NOT EXISTS standby_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

CREATE INDEX IF NOT EXISTS idx_standby_dates ON standby_records(duty_start_date, duty_end_date);
CREATE INDEX IF NOT EXISTS idx_standby_status ON standby_records(status);

-- Table: etl_jobs
CREATE TABLE IF NOT EXISTS etl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

CREATE INDEX IF NOT EXISTS idx_etl_jobs_status ON etl_jobs(status);

-- 2. Enable Row Level Security (RLS)
-- -----------------------------------------------------
ALTER TABLE crew_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE crew_flight_hours ENABLE ROW LEVEL SECURITY;
ALTER TABLE standby_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE etl_jobs ENABLE ROW LEVEL SECURITY;

-- 3. Drop Existing Policies (to avoid conflicts)
-- -----------------------------------------------------
DROP POLICY IF EXISTS "anon_select_crew_members" ON crew_members;
DROP POLICY IF EXISTS "anon_insert_crew_members" ON crew_members;
DROP POLICY IF EXISTS "anon_update_crew_members" ON crew_members;

DROP POLICY IF EXISTS "anon_select_crew_flight_hours" ON crew_flight_hours;
DROP POLICY IF EXISTS "anon_insert_crew_flight_hours" ON crew_flight_hours;
DROP POLICY IF EXISTS "anon_update_crew_flight_hours" ON crew_flight_hours;

DROP POLICY IF EXISTS "anon_select_standby_records" ON standby_records;
DROP POLICY IF EXISTS "anon_insert_standby_records" ON standby_records;
DROP POLICY IF EXISTS "anon_update_standby_records" ON standby_records;

DROP POLICY IF EXISTS "anon_select_etl_jobs" ON etl_jobs;
DROP POLICY IF EXISTS "anon_insert_etl_jobs" ON etl_jobs;
DROP POLICY IF EXISTS "anon_update_etl_jobs" ON etl_jobs;

-- 4. Create Policies (public access for development)
-- -----------------------------------------------------
-- crew_members
CREATE POLICY "anon_select_crew_members" ON crew_members FOR SELECT USING (true);
CREATE POLICY "anon_insert_crew_members" ON crew_members FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_update_crew_members" ON crew_members FOR UPDATE USING (true);

-- crew_flight_hours
CREATE POLICY "anon_select_crew_flight_hours" ON crew_flight_hours FOR SELECT USING (true);
CREATE POLICY "anon_insert_crew_flight_hours" ON crew_flight_hours FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_update_crew_flight_hours" ON crew_flight_hours FOR UPDATE USING (true);

-- standby_records
CREATE POLICY "anon_select_standby_records" ON standby_records FOR SELECT USING (true);
CREATE POLICY "anon_insert_standby_records" ON standby_records FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_update_standby_records" ON standby_records FOR UPDATE USING (true);

-- etl_jobs
CREATE POLICY "anon_select_etl_jobs" ON etl_jobs FOR SELECT USING (true);
CREATE POLICY "anon_insert_etl_jobs" ON etl_jobs FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_update_etl_jobs" ON etl_jobs FOR UPDATE USING (true);

-- 5. Insert Sample Data
-- -----------------------------------------------------

-- crew_members
INSERT INTO crew_members (crew_id, crew_name, first_name, last_name, base, gender, source)
VALUES 
    ('C001', 'Nguyen Van A', 'Van A', 'Nguyen', 'SGN', 'M', 'SAMPLE'),
    ('C002', 'Tran Thi B', 'Thi B', 'Tran', 'HAN', 'F', 'SAMPLE'),
    ('C003', 'Le Van C', 'Van C', 'Le', 'DAD', 'M', 'SAMPLE'),
    ('C004', 'Pham Thi D', 'Thi D', 'Pham', 'SGN', 'F', 'SAMPLE'),
    ('C005', 'Hoang Van E', 'Van E', 'Hoang', 'HAN', 'M', 'SAMPLE')
ON CONFLICT (crew_id) DO NOTHING;

-- crew_flight_hours
INSERT INTO crew_flight_hours (crew_id, crew_name, hours_28_day, hours_12_month, warning_level, calculation_date, source)
VALUES 
    ('C001', 'Nguyen Van A', 75.5, 650.0, 'NORMAL', CURRENT_DATE, 'SAMPLE'),
    ('C002', 'Tran Thi B', 92.0, 880.0, 'WARNING', CURRENT_DATE, 'SAMPLE'),
    ('C003', 'Le Van C', 98.5, 920.0, 'CRITICAL', CURRENT_DATE, 'SAMPLE'),
    ('C004', 'Pham Thi D', 45.0, 400.0, 'NORMAL', CURRENT_DATE, 'SAMPLE'),
    ('C005', 'Hoang Van E', 88.0, 780.0, 'WARNING', CURRENT_DATE, 'SAMPLE')
ON CONFLICT (crew_id, calculation_date) DO NOTHING;

-- standby_records
INSERT INTO standby_records (crew_id, crew_name, status, duty_start_date, duty_end_date, base, source)
VALUES 
    ('C001', 'Nguyen Van A', 'FLY', CURRENT_DATE, CURRENT_DATE, 'SGN', 'SAMPLE'),
    ('C002', 'Tran Thi B', 'SBY', CURRENT_DATE, CURRENT_DATE, 'HAN', 'SAMPLE'),
    ('C003', 'Le Van C', 'SL', CURRENT_DATE, CURRENT_DATE + 2, 'DAD', 'SAMPLE'),
    ('C004', 'Pham Thi D', 'OFF', CURRENT_DATE, CURRENT_DATE, 'SGN', 'SAMPLE'),
    ('C005', 'Hoang Van E', 'TRN', CURRENT_DATE, CURRENT_DATE, 'HAN', 'SAMPLE');

-- Done
