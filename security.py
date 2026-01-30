"""
Security Middleware Module
Security Hardening

Rate limiting, input validation, and API key authentication.
"""

import os
import re
import logging
from functools import wraps
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import request, g, jsonify
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
API_KEY_HEADER = "X-API-Key"
API_KEYS = os.getenv("API_KEYS", "").split(",")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"


# =====================================================
# Input Sanitization
# =====================================================

def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Sanitize string input.
    
    Args:
        value: Input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    
    # Truncate to max length
    value = value[:max_length]
    
    # Remove HTML tags (basic)
    try:
        import bleach
        value = bleach.clean(value, tags=[], strip=True)
    except ImportError:
        # Fallback: simple regex
        value = re.sub(r'<[^>]+>', '', value)
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    return value.strip()


def sanitize_int(value: Any, default: int = 0, min_val: int = None, max_val: int = None) -> int:
    """
    Sanitize integer input.
    
    Args:
        value: Input value
        default: Default if invalid
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Sanitized integer
    """
    try:
        result = int(value)
        
        if min_val is not None and result < min_val:
            result = min_val
        if max_val is not None and result > max_val:
            result = max_val
            
        return result
    except (ValueError, TypeError):
        return default


def sanitize_date(value: str, format: str = "%Y-%m-%d") -> Optional[str]:
    """
    Validate and sanitize date string.
    
    Args:
        value: Date string
        format: Expected format
        
    Returns:
        Valid date string or None
    """
    if not value:
        return None
    
    try:
        parsed = datetime.strptime(value, format)
        return parsed.strftime(format)
    except ValueError:
        return None


def validate_airport_code(code: str) -> bool:
    """Validate 3-letter airport code."""
    return bool(code) and len(code) == 3 and code.isalpha()


def validate_crew_id(crew_id: str) -> bool:
    """Validate crew ID format."""
    if not crew_id:
        return False
    # Allow alphanumeric up to 20 chars
    return bool(re.match(r'^[A-Za-z0-9]{1,20}$', crew_id))


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return True  # Optional field
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# =====================================================
# Request Validation Schemas
# =====================================================

class ValidationError(Exception):
    """Custom validation error."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(", ".join(errors))


def validate_query_params(rules: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Validate query parameters against rules.
    
    Args:
        rules: Dictionary of parameter rules
            {
                "param_name": {
                    "type": "string|int|date",
                    "required": True/False,
                    "max_length": 100,
                    "min": 0,
                    "max": 1000,
                    "default": value
                }
            }
            
    Returns:
        Dictionary of validated parameters
        
    Raises:
        ValidationError: If validation fails
    """
    errors = []
    result = {}
    
    for param, config in rules.items():
        value = request.args.get(param)
        param_type = config.get("type", "string")
        required = config.get("required", False)
        default = config.get("default")
        
        # Check required
        if required and not value:
            errors.append(f"{param} is required")
            continue
        
        # Apply default
        if value is None:
            result[param] = default
            continue
        
        # Validate by type
        if param_type == "string":
            max_length = config.get("max_length", 500)
            result[param] = sanitize_string(value, max_length)
            
        elif param_type == "int":
            min_val = config.get("min")
            max_val = config.get("max")
            result[param] = sanitize_int(value, default or 0, min_val, max_val)
            
        elif param_type == "date":
            date_val = sanitize_date(value)
            if value and not date_val:
                errors.append(f"{param} must be valid date (YYYY-MM-DD)")
            else:
                result[param] = date_val
                
        elif param_type == "email":
            if not validate_email(value):
                errors.append(f"{param} must be valid email")
            else:
                result[param] = sanitize_string(value)
                
        elif param_type == "airport":
            if not validate_airport_code(value):
                errors.append(f"{param} must be valid 3-letter airport code")
            else:
                result[param] = value.upper()
    
    if errors:
        raise ValidationError(errors)
    
    return result


def validate_json_body(rules: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Validate JSON request body.
    
    Similar to validate_query_params but for POST/PUT body.
    """
    errors = []
    result = {}
    
    body = request.get_json() or {}
    
    for field, config in rules.items():
        value = body.get(field)
        field_type = config.get("type", "string")
        required = config.get("required", False)
        default = config.get("default")
        
        if required and value is None:
            errors.append(f"{field} is required")
            continue
        
        if value is None:
            result[field] = default
            continue
        
        if field_type == "string":
            max_length = config.get("max_length", 500)
            result[field] = sanitize_string(str(value), max_length)
            
        elif field_type == "int":
            min_val = config.get("min")
            max_val = config.get("max")
            result[field] = sanitize_int(value, default or 0, min_val, max_val)
            
        elif field_type == "bool":
            result[field] = bool(value)
            
        elif field_type == "list":
            if isinstance(value, list):
                max_items = config.get("max_items", 100)
                result[field] = value[:max_items]
            else:
                errors.append(f"{field} must be a list")
    
    if errors:
        raise ValidationError(errors)
    
    return result


# =====================================================
# API Key Authentication
# =====================================================

def require_api_key(f):
    """
    Decorator to require API key authentication.
    
    Usage:
        @app.route('/api/secure')
        @require_api_key
        def secure_endpoint():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip in development mode
        if os.getenv("FLASK_DEBUG") == "1":
            return f(*args, **kwargs)
        
        # Check API keys enabled
        if not API_KEYS or API_KEYS == [""]:
            return f(*args, **kwargs)
        
        api_key = request.headers.get(API_KEY_HEADER)
        
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key required",
                "timestamp": datetime.now().isoformat()
            }), 401
        
        if api_key not in API_KEYS:
            logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({
                "success": False,
                "error": "Invalid API key",
                "timestamp": datetime.now().isoformat()
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated


def optional_api_key(f):
    """
    Decorator that checks API key if provided, but doesn't require it.
    Sets g.authenticated = True if valid key provided.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        g.authenticated = False
        
        api_key = request.headers.get(API_KEY_HEADER)
        if api_key and api_key in API_KEYS:
            g.authenticated = True
        
        return f(*args, **kwargs)
    
    return decorated


# =====================================================
# Rate Limiting Helpers
# =====================================================

def get_rate_limit_key():
    """Get rate limit key based on IP or API key."""
    api_key = request.headers.get(API_KEY_HEADER)
    if api_key:
        return f"api_key:{api_key}"
    return f"ip:{request.remote_addr}"


def get_rate_limit_message():
    """Custom rate limit exceeded message."""
    return jsonify({
        "success": False,
        "error": "Rate limit exceeded. Please try again later.",
        "timestamp": datetime.now().isoformat()
    }), 429


# =====================================================
# Security Headers Middleware
# =====================================================

def add_security_headers(response):
    """
    Add security headers to response.
    
    Usage:
        app.after_request(add_security_headers)
    """
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy (basic)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
    )
    
    return response


# =====================================================
# Request Logging
# =====================================================

def log_request():
    """Log incoming request details."""
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")


def log_response(response):
    """Log response status."""
    logger.info(f"Response: {response.status_code} for {request.path}")
    return response


# =====================================================
# Common Validation Rules
# =====================================================

COMMON_RULES = {
    "pagination": {
        "page": {"type": "int", "default": 1, "min": 1, "max": 10000},
        "per_page": {"type": "int", "default": 50, "min": 1, "max": 100}
    },
    "date_filter": {
        "date": {"type": "date", "required": False}
    },
    "crew_filter": {
        "base": {"type": "string", "max_length": 10},
        "status": {"type": "string", "max_length": 10}
    }
}


# =====================================================
# Export
# =====================================================

__all__ = [
    'sanitize_string',
    'sanitize_int',
    'sanitize_date',
    'validate_airport_code',
    'validate_crew_id',
    'validate_email',
    'validate_query_params',
    'validate_json_body',
    'ValidationError',
    'require_api_key',
    'optional_api_key',
    'get_rate_limit_key',
    'get_rate_limit_message',
    'add_security_headers',
    'log_request',
    'log_response',
    'COMMON_RULES'
]


# =====================================================
# Test
# =====================================================

if __name__ == "__main__":
    print("="*60)
    print("Security Middleware Test")
    print("="*60)
    
    # Test sanitization
    print(f"\nSanitize string: '{sanitize_string('  Hello <script>alert(1)</script>  ')}'")
    print(f"Sanitize int: {sanitize_int('42', min_val=0, max_val=100)}")
    print(f"Sanitize date: {sanitize_date('2026-01-30')}")
    
    # Test validation
    print(f"\nValid airport: {validate_airport_code('SGN')}")
    print(f"Valid crew ID: {validate_crew_id('ABC123')}")
    print(f"Valid email: {validate_email('test@example.com')}")
    
    print("\nSecurity middleware initialized successfully!")
