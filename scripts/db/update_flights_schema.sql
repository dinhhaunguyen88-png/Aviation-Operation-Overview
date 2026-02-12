-- Update flights table with detailed metrics columns

-- Timestamps for Scheduled/Estimated Times (using Time or Text depending on format, Text is safer for raw HH:MM import initially, but Timestamp is better for query)
-- Given the source data is HH:MM strings, let's stick to TEXT for now or convert. 
-- However, strict schema suggests separate DATE and TIME columns or a Timestamp.
-- For simplicity compatible with current `flight_date` + HH:MM, adding them as TEXT is safest to avoid parsing errors during upsert if AIMS sends "24:00" or similar.
-- Or better: TEXT for HH:MM.

ALTER TABLE flights ADD COLUMN IF NOT EXISTS std text;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS sta text;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS etd text;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS eta text;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS off_block text;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS on_block text;

-- Delay Info
ALTER TABLE flights ADD COLUMN IF NOT EXISTS delay_code_1 text;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS delay_time_1 integer DEFAULT 0;

-- Pax
ALTER TABLE flights ADD COLUMN IF NOT EXISTS pax_total integer DEFAULT 0;

-- Comment
COMMENT ON COLUMN flights.off_block IS 'Actual Off Block Time (HH:MM)';
COMMENT ON COLUMN flights.on_block IS 'Actual On Block Time (HH:MM)';
