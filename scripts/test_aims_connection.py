"""
Test AIMS Connection Script
Phase 1: Foundation Setup

Quick script to verify AIMS SOAP Web Service connectivity.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aims_soap_client import test_connection

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
