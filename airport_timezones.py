"""
Airport Timezone Mapping

Maps IATA airport codes to their UTC offset in hours.
Used for converting flight times to local departure time.
"""

# UTC offsets for airports (in hours)
# Positive values = ahead of UTC (Asia, Europe)
# Negative values = behind UTC (Americas)

AIRPORT_TIMEZONES = {
    # =====================================================
    # VIETNAM (UTC+7)
    # =====================================================
    "SGN": 7,   # Ho Chi Minh City (Tan Son Nhat)
    "HAN": 7,   # Hanoi (Noi Bai)
    "DAD": 7,   # Da Nang
    "CXR": 7,   # Cam Ranh (Nha Trang)
    "PQC": 7,   # Phu Quoc
    "VII": 7,   # Vinh
    "HPH": 7,   # Hai Phong (Cat Bi)
    "VDO": 7,   # Van Don
    "THD": 7,   # Thanh Hoa
    "DLI": 7,   # Da Lat
    "HUI": 7,   # Hue
    "VCA": 7,   # Can Tho
    "PXU": 7,   # Pleiku
    "BMV": 7,   # Ban Me Thuot (Buon Ma Thuot)
    "UIH": 7,   # Quy Nhon (Phu Cat)
    "VCS": 7,   # Con Son (Con Dao)
    "TBB": 7,   # Tuy Hoa
    "VKG": 7,   # Rach Gia
    "CAH": 7,   # Ca Mau
    "DIN": 7,   # Dien Bien Phu
    "VCL": 7,   # Chu Lai
    
    # =====================================================
    # KOREA (UTC+9)
    # =====================================================
    "ICN": 9,   # Seoul (Incheon)
    "GMP": 9,   # Seoul (Gimpo)
    "PUS": 9,   # Busan
    "TAE": 9,   # Daegu
    "CJU": 9,   # Jeju
    "CJJ": 9,   # Cheongju
    "MWX": 9,   # Muan
    
    # =====================================================
    # JAPAN (UTC+9)
    # =====================================================
    "NRT": 9,   # Tokyo (Narita)
    "HND": 9,   # Tokyo (Haneda)
    "KIX": 9,   # Osaka (Kansai)
    "NGO": 9,   # Nagoya (Chubu)
    "FUK": 9,   # Fukuoka
    "CTS": 9,   # Sapporo (New Chitose)
    "OKA": 9,   # Okinawa (Naha)
    
    # =====================================================
    # CHINA (UTC+8)
    # =====================================================
    "PEK": 8,   # Beijing (Capital)
    "PKX": 8,   # Beijing (Daxing)
    "PVG": 8,   # Shanghai (Pudong)
    "SHA": 8,   # Shanghai (Hongqiao)
    "CAN": 8,   # Guangzhou (Baiyun)
    "SZX": 8,   # Shenzhen
    "CTU": 8,   # Chengdu
    "KWL": 8,   # Guilin
    "HAK": 8,   # Haikou
    "SYX": 8,   # Sanya
    "NNG": 8,   # Nanning
    "KMG": 8,   # Kunming
    "XIY": 8,   # Xi'an
    "WUH": 8,   # Wuhan
    "CSX": 8,   # Changsha
    "HGH": 8,   # Hangzhou
    "NKG": 8,   # Nanjing
    "TAO": 8,   # Qingdao
    "DLC": 8,   # Dalian
    "CGO": 8,   # Zhengzhou
    "TNA": 8,   # Jinan
    "XMN": 8,   # Xiamen
    "FOC": 8,   # Fuzhou
    "LHW": 8,   # Lanzhou
    "WNZ": 8,   # Wenzhou
    
    # =====================================================
    # HONG KONG, MACAU, TAIWAN (UTC+8)
    # =====================================================
    "HKG": 8,   # Hong Kong
    "MFM": 8,   # Macau
    "TPE": 8,   # Taipei (Taoyuan)
    "TSA": 8,   # Taipei (Songshan)
    "RMQ": 8,   # Taichung
    "KHH": 8,   # Kaohsiung
    
    # =====================================================
    # INDIA (UTC+5.5)
    # =====================================================
    "DEL": 5.5,  # Delhi
    "BOM": 5.5,  # Mumbai
    "MAA": 5.5,  # Chennai
    "CCU": 5.5,  # Kolkata
    "BLR": 5.5,  # Bangalore
    "HYD": 5.5,  # Hyderabad
    "AMD": 5.5,  # Ahmedabad
    "COK": 5.5,  # Kochi
    "GOI": 5.5,  # Goa
    "TRV": 5.5,  # Trivandrum
    
    # =====================================================
    # SOUTHEAST ASIA
    # =====================================================
    # Thailand (UTC+7)
    "BKK": 7,   # Bangkok (Suvarnabhumi)
    "DMK": 7,   # Bangkok (Don Mueang)
    "CNX": 7,   # Chiang Mai
    "HKT": 7,   # Phuket
    "USM": 7,   # Koh Samui
    
    # Cambodia (UTC+7)
    "PNH": 7,   # Phnom Penh
    "REP": 7,   # Siem Reap
    
    # Laos (UTC+7)
    "VTE": 7,   # Vientiane
    "LPQ": 7,   # Luang Prabang
    
    # Myanmar (UTC+6.5)
    "RGN": 6.5,  # Yangon
    "MDL": 6.5,  # Mandalay
    
    # Malaysia (UTC+8)
    "KUL": 8,   # Kuala Lumpur
    "PEN": 8,   # Penang
    "LGK": 8,   # Langkawi
    
    # Singapore (UTC+8)
    "SIN": 8,   # Singapore (Changi)
    
    # Indonesia
    "CGK": 7,   # Jakarta (Soekarno-Hatta) - WIB (UTC+7)
    "DPS": 8,   # Bali (Ngurah Rai) - WITA (UTC+8)
    "SUB": 7,   # Surabaya - WIB (UTC+7)
    
    # Philippines (UTC+8)
    "MNL": 8,   # Manila
    "CEB": 8,   # Cebu
    
    # =====================================================
    # AUSTRALIA
    # =====================================================
    # Eastern (AEST UTC+10, AEDT UTC+11 in summer)
    # Using UTC+11 for DST period (Nov-Mar)
    "SYD": 11,  # Sydney
    "MEL": 11,  # Melbourne
    "BNE": 10,  # Brisbane (no DST)
    "ADL": 10.5, # Adelaide
    "PER": 8,   # Perth
    
    # =====================================================
    # EUROPE
    # =====================================================
    # Western Europe (UTC+0/+1)
    "LHR": 0,   # London Heathrow
    "LGW": 0,   # London Gatwick
    "CDG": 1,   # Paris Charles de Gaulle
    "ORY": 1,   # Paris Orly
    "FRA": 1,   # Frankfurt
    "MUC": 1,   # Munich
    "AMS": 1,   # Amsterdam
    "ZRH": 1,   # Zurich
    
    # Eastern Europe (UTC+2/+3)
    "SVO": 3,   # Moscow (Sheremetyevo)
    "DME": 3,   # Moscow (Domodedovo)
    
    # =====================================================
    # RUSSIA (Far East)
    # =====================================================
    "VVO": 10,  # Vladivostok
    "KHV": 10,  # Khabarovsk
    
    # =====================================================
    # MIDDLE EAST
    # =====================================================
    "DXB": 4,   # Dubai
    "DOH": 3,   # Doha
    "AUH": 4,   # Abu Dhabi
    "IST": 3,   # Istanbul
    
    # =====================================================
    # NORTH AMERICA
    # =====================================================
    "LAX": -8,  # Los Angeles
    "SFO": -8,  # San Francisco
    "JFK": -5,  # New York JFK
    "EWR": -5,  # Newark
    "ORD": -6,  # Chicago O'Hare
    "YVR": -8,  # Vancouver
    
    # =====================================================
    # DEFAULT (Vietnam time for unknown airports)
    # =====================================================
    "DEFAULT": 7
}


def get_airport_timezone(airport_code: str) -> float:
    """
    Get UTC offset for an airport.
    
    Args:
        airport_code: IATA 3-letter airport code
        
    Returns:
        UTC offset in hours (e.g., 7 for Vietnam, 9 for Korea)
    """
    if not airport_code:
        return AIRPORT_TIMEZONES["DEFAULT"]
    
    return AIRPORT_TIMEZONES.get(airport_code.upper().strip(), AIRPORT_TIMEZONES["DEFAULT"])


def convert_utc_to_local(utc_hour: int, utc_min: int, airport_code: str) -> tuple:
    """
    Convert UTC time to local time for a given airport.
    
    Args:
        utc_hour: Hour in UTC (0-23)
        utc_min: Minute (0-59)
        airport_code: Departure airport IATA code
        
    Returns:
        Tuple of (local_hour, date_offset) where date_offset is:
        - 0: same day
        - 1: next day (rollover past midnight)
        - -1: previous day (rollback before midnight)
    """
    tz_offset = get_airport_timezone(airport_code)
    
    # Handle fractional timezone (like India +5.5)
    offset_hours = int(tz_offset)
    offset_mins = int((tz_offset - offset_hours) * 60)
    
    local_min = utc_min + offset_mins
    local_hour = utc_hour + offset_hours
    
    # Handle minute overflow
    if local_min >= 60:
        local_min -= 60
        local_hour += 1
    elif local_min < 0:
        local_min += 60
        local_hour -= 1
    
    # Handle day rollover
    date_offset = 0
    if local_hour >= 24:
        local_hour -= 24
        date_offset = 1
    elif local_hour < 0:
        local_hour += 24
        date_offset = -1
    
    return (local_hour, local_min, date_offset)
