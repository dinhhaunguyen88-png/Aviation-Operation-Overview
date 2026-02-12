-- ============================================================
-- Aircraft Swap Analysis Tables
-- Run this script in Supabase SQL Editor
-- ============================================================

-- Table: aircraft_swaps
-- Stores detected aircraft swap events
CREATE TABLE IF NOT EXISTS aircraft_swaps (
    id SERIAL PRIMARY KEY,
    swap_event_id VARCHAR(20) UNIQUE NOT NULL,
    flight_date DATE NOT NULL,
    flight_number VARCHAR(20) NOT NULL,
    departure VARCHAR(10),
    arrival VARCHAR(10),
    original_reg VARCHAR(20) NOT NULL,
    swapped_reg VARCHAR(20) NOT NULL,
    original_ac_type VARCHAR(20),
    swapped_ac_type VARCHAR(20),
    swap_reason VARCHAR(255),
    swap_category VARCHAR(50) DEFAULT 'UNKNOWN',
    delay_minutes INT DEFAULT 0,
    recovery_status VARCHAR(50) DEFAULT 'PENDING',
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    mod_log_ref TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_swaps_date ON aircraft_swaps(flight_date);
CREATE INDEX IF NOT EXISTS idx_swaps_flight ON aircraft_swaps(flight_number);
CREATE INDEX IF NOT EXISTS idx_swaps_orig_reg ON aircraft_swaps(original_reg);
CREATE INDEX IF NOT EXISTS idx_swaps_swap_reg ON aircraft_swaps(swapped_reg);
CREATE INDEX IF NOT EXISTS idx_swaps_category ON aircraft_swaps(swap_category);
CREATE INDEX IF NOT EXISTS idx_swaps_event_id ON aircraft_swaps(swap_event_id);

-- Table: aircraft_swap_snapshots
-- Stores the first-seen aircraft registration for each flight
-- Used as baseline for swap comparison
CREATE TABLE IF NOT EXISTS aircraft_swap_snapshots (
    id SERIAL PRIMARY KEY,
    flight_date DATE NOT NULL,
    flight_number VARCHAR(20) NOT NULL,
    departure VARCHAR(10) NOT NULL,
    first_seen_reg VARCHAR(20) NOT NULL,
    first_seen_ac_type VARCHAR(20),
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(flight_date, flight_number, departure)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_date ON aircraft_swap_snapshots(flight_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_flight ON aircraft_swap_snapshots(flight_number);

-- ============================================================
-- SUMMARY
-- ============================================================
-- aircraft_swaps: Stores detected swap events with original/swapped reg
-- aircraft_swap_snapshots: Baseline registration per flight for comparison
-- ============================================================
