-- =====================================================
-- AIMS Additional Tables Schema
-- Created: 2026-01-31
-- Purpose: Add tables for complete AIMS data integration
-- =====================================================

-- 1. Aircraft Registry Table
-- Source: FetchAircrafts (#27)
-- =====================================================
CREATE TABLE IF NOT EXISTS aircraft (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ac_type VARCHAR(20),              -- Aircraft type code (A321, A350, B787)
    ac_reg VARCHAR(20) UNIQUE,        -- Registration number (VN-A888)
    ac_country VARCHAR(10),           -- Country registered
    use_pound SMALLINT DEFAULT 1,     -- 1=Kgs, 2=Pounds
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, MAINTENANCE, AOG
    location VARCHAR(10),             -- Current airport code
    weekly_flight_hours DECIMAL(10,2) DEFAULT 0,
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aircraft_ac_reg ON aircraft(ac_reg);
CREATE INDEX IF NOT EXISTS idx_aircraft_status ON aircraft(status);

-- 2. Aircraft Types Reference Table
-- Source: FetchACTypes (#28)
-- =====================================================
CREATE TABLE IF NOT EXISTS aircraft_types (
    ac_type_code VARCHAR(20) PRIMARY KEY,   -- A321, A350, B787
    description VARCHAR(200),               -- Full description
    manufacturer VARCHAR(100),              -- Boeing, Airbus
    category VARCHAR(50),                   -- Narrow-body, Wide-body
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Airports Reference Table
-- Source: FetchAirports (#30)
-- =====================================================
CREATE TABLE IF NOT EXISTS airports (
    airport_code VARCHAR(10) PRIMARY KEY,   -- IATA code (SGN, HAN)
    airport_name VARCHAR(200),              -- Full name
    city VARCHAR(100),                      -- City name
    country_code VARCHAR(10),               -- Country code
    latitude DOUBLE PRECISION,              -- GPS latitude
    longitude DOUBLE PRECISION,             -- GPS longitude
    altitude INTEGER,                       -- Altitude in feet
    runway_length INTEGER,                  -- Main runway length
    timezone VARCHAR(50),                   -- Timezone ID
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Crew Qualifications Table
-- Source: FetchCrewQuals (#14), GetCrewList (#12)
-- =====================================================
CREATE TABLE IF NOT EXISTS crew_qualifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crew_id VARCHAR(20) NOT NULL,
    qual_base VARCHAR(10),                  -- Base airport (SGN, HAN)
    qual_ac_type VARCHAR(20),               -- Aircraft type qualified for
    qual_position VARCHAR(20),              -- Position: PIC, FO, CCM, FA, etc.
    roster_group SMALLINT,                  -- Roster group number
    begin_date DATE,                        -- Qualification start date
    end_date DATE,                          -- Qualification expiry date
    is_primary BOOLEAN DEFAULT FALSE,       -- Primary qualification flag
    not_to_roster BOOLEAN DEFAULT FALSE,    -- Not to be rostered flag
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(crew_id, qual_ac_type, qual_position, begin_date)
);

CREATE INDEX IF NOT EXISTS idx_crew_quals_crew_id ON crew_qualifications(crew_id);
CREATE INDEX IF NOT EXISTS idx_crew_quals_position ON crew_qualifications(qual_position);
CREATE INDEX IF NOT EXISTS idx_crew_quals_base ON crew_qualifications(qual_base);

-- 5. Daily Crew Status Table (for SBY/SL/CSL tracking)
-- Source: FetchDayMembers (#2)
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_crew_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crew_id VARCHAR(20) NOT NULL,
    crew_name VARCHAR(200),
    status_date DATE NOT NULL,
    duty_code VARCHAR(20),                  -- SBY, SL, CSL, OFF, FLT, TRN, LVE, etc.
    duty_description VARCHAR(200),          -- Full description
    duty_start_time TIME,                   -- Start time
    duty_end_time TIME,                     -- End time
    base VARCHAR(10),                       -- Assigned base
    flight_number VARCHAR(20),              -- If FLT, the flight number
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(crew_id, status_date, duty_code)
);

CREATE INDEX IF NOT EXISTS idx_daily_status_date ON daily_crew_status(status_date);
CREATE INDEX IF NOT EXISTS idx_daily_status_duty_code ON daily_crew_status(duty_code);
CREATE INDEX IF NOT EXISTS idx_daily_status_crew_id ON daily_crew_status(crew_id);

-- 6. Update flights table with additional columns
-- Source: FetchDayFlights (#19), FetchFlightsFrTo (#20)
-- =====================================================
ALTER TABLE flights 
    ADD COLUMN IF NOT EXISTS departure_airport VARCHAR(10),
    ADD COLUMN IF NOT EXISTS arrival_airport VARCHAR(10),
    ADD COLUMN IF NOT EXISTS std_time TIME,           -- Scheduled Time of Departure
    ADD COLUMN IF NOT EXISTS sta_time TIME,           -- Scheduled Time of Arrival
    ADD COLUMN IF NOT EXISTS etd_time TIME,           -- Estimated Time of Departure
    ADD COLUMN IF NOT EXISTS eta_time TIME,           -- Estimated Time of Arrival
    ADD COLUMN IF NOT EXISTS atd_time TIME,           -- Actual Time of Departure
    ADD COLUMN IF NOT EXISTS ata_time TIME,           -- Actual Time of Arrival
    ADD COLUMN IF NOT EXISTS off_block_time TIME,     -- Actual off block time
    ADD COLUMN IF NOT EXISTS on_block_time TIME,      -- Actual on block time
    ADD COLUMN IF NOT EXISTS block_hours DECIMAL(10,2),  -- Calculated block hours
    ADD COLUMN IF NOT EXISTS delay_code_2 VARCHAR(10),
    ADD COLUMN IF NOT EXISTS delay_time_2 INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS leg_code VARCHAR(10),    -- Flight leg suffix
    ADD COLUMN IF NOT EXISTS charterer VARCHAR(100);  -- Charter company if any

-- Create indexes for flights table if not exist
CREATE INDEX IF NOT EXISTS idx_flights_departure ON flights(departure_airport);
CREATE INDEX IF NOT EXISTS idx_flights_arrival ON flights(arrival_airport);

-- 7. Flight Crew (Crew assigned to specific flights)
-- Source: FetchLegMembers (#1)
-- =====================================================
CREATE TABLE IF NOT EXISTS flight_crew (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_date DATE NOT NULL,
    flight_number VARCHAR(20) NOT NULL,
    departure VARCHAR(10),
    crew_id VARCHAR(20) NOT NULL,
    crew_name VARCHAR(200),
    position VARCHAR(20),                   -- PIC, FO, CCM, etc.
    check_in_time TIMESTAMPTZ,
    check_out_time TIMESTAMPTZ,
    source VARCHAR(20) DEFAULT 'AIMS',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(flight_date, flight_number, departure, crew_id)
);

CREATE INDEX IF NOT EXISTS idx_flight_crew_date ON flight_crew(flight_date);
CREATE INDEX IF NOT EXISTS idx_flight_crew_crew_id ON flight_crew(crew_id);

-- 8. Create view for dashboard summary with crew status
-- =====================================================
CREATE OR REPLACE VIEW v_daily_crew_summary AS
SELECT 
    status_date,
    COUNT(*) FILTER (WHERE duty_code = 'SBY') AS standby_count,
    COUNT(*) FILTER (WHERE duty_code = 'SL') AS sick_leave_count,
    COUNT(*) FILTER (WHERE duty_code = 'CSL') AS call_sick_count,
    COUNT(*) FILTER (WHERE duty_code = 'OFF') AS day_off_count,
    COUNT(*) FILTER (WHERE duty_code = 'FLT') AS flying_count,
    COUNT(*) FILTER (WHERE duty_code = 'TRN') AS training_count,
    COUNT(*) FILTER (WHERE duty_code = 'LVE') AS leave_count,
    COUNT(*) AS total_entries
FROM daily_crew_status
GROUP BY status_date;

-- 9. Create view for flight block hours summary
-- =====================================================
CREATE OR REPLACE VIEW v_daily_flight_summary AS
SELECT 
    flight_date,
    COUNT(*) AS total_flights,
    COUNT(DISTINCT aircraft_reg) AS total_aircraft,
    SUM(block_hours) AS total_block_hours,
    AVG(block_hours) AS avg_block_hours
FROM flights
WHERE flight_date IS NOT NULL
GROUP BY flight_date;

-- =====================================================
-- Insert sample reference data
-- =====================================================

-- Sample aircraft types
INSERT INTO aircraft_types (ac_type_code, description, manufacturer, category)
VALUES 
    ('A321', 'Airbus A321-200', 'Airbus', 'Narrow-body'),
    ('A321N', 'Airbus A321neo', 'Airbus', 'Narrow-body'),
    ('A350', 'Airbus A350-900', 'Airbus', 'Wide-body'),
    ('B787', 'Boeing 787-10 Dreamliner', 'Boeing', 'Wide-body'),
    ('B789', 'Boeing 787-9 Dreamliner', 'Boeing', 'Wide-body'),
    ('A320', 'Airbus A320-200', 'Airbus', 'Narrow-body')
ON CONFLICT (ac_type_code) DO NOTHING;

-- Sample airports (Vietnam)
INSERT INTO airports (airport_code, airport_name, city, country_code, timezone)
VALUES 
    ('SGN', 'Tan Son Nhat International Airport', 'Ho Chi Minh City', 'VN', 'Asia/Ho_Chi_Minh'),
    ('HAN', 'Noi Bai International Airport', 'Hanoi', 'VN', 'Asia/Ho_Chi_Minh'),
    ('DAD', 'Da Nang International Airport', 'Da Nang', 'VN', 'Asia/Ho_Chi_Minh'),
    ('CXR', 'Cam Ranh International Airport', 'Nha Trang', 'VN', 'Asia/Ho_Chi_Minh'),
    ('PQC', 'Phu Quoc International Airport', 'Phu Quoc', 'VN', 'Asia/Ho_Chi_Minh'),
    ('VDO', 'Van Don International Airport', 'Quang Ninh', 'VN', 'Asia/Ho_Chi_Minh'),
    ('HPH', 'Cat Bi International Airport', 'Hai Phong', 'VN', 'Asia/Ho_Chi_Minh'),
    ('VII', 'Vinh International Airport', 'Vinh', 'VN', 'Asia/Ho_Chi_Minh'),
    ('HUI', 'Phu Bai International Airport', 'Hue', 'VN', 'Asia/Ho_Chi_Minh'),
    ('UIH', 'Phu Cat Airport', 'Quy Nhon', 'VN', 'Asia/Ho_Chi_Minh'),
    ('DLI', 'Lien Khuong Airport', 'Da Lat', 'VN', 'Asia/Ho_Chi_Minh'),
    ('BMV', 'Buon Ma Thuot Airport', 'Buon Ma Thuot', 'VN', 'Asia/Ho_Chi_Minh'),
    ('VCS', 'Con Dao Airport', 'Con Dao', 'VN', 'Asia/Ho_Chi_Minh'),
    ('PXU', 'Pleiku Airport', 'Pleiku', 'VN', 'Asia/Ho_Chi_Minh'),
    ('VCL', 'Chu Lai Airport', 'Chu Lai', 'VN', 'Asia/Ho_Chi_Minh'),
    ('TBB', 'Dong Tac Airport', 'Tuy Hoa', 'VN', 'Asia/Ho_Chi_Minh'),
    ('VCA', 'Can Tho International Airport', 'Can Tho', 'VN', 'Asia/Ho_Chi_Minh'),
    ('VKG', 'Rach Gia Airport', 'Rach Gia', 'VN', 'Asia/Ho_Chi_Minh'),
    ('CAH', 'Ca Mau Airport', 'Ca Mau', 'VN', 'Asia/Ho_Chi_Minh'),
    ('THD', 'Tho Xuan Airport', 'Thanh Hoa', 'VN', 'Asia/Ho_Chi_Minh'),
    ('VDH', 'Dong Hoi Airport', 'Dong Hoi', 'VN', 'Asia/Ho_Chi_Minh'),
    ('DIN', 'Dien Bien Phu Airport', 'Dien Bien', 'VN', 'Asia/Ho_Chi_Minh')
ON CONFLICT (airport_code) DO NOTHING;

-- =====================================================
-- Done! Tables created successfully.
-- =====================================================
