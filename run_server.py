from waitress import serve
from api_server import app
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("waitress")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print("="*60)
    print(f"  Aviation Dashboard - Production Server")
    print("="*60)
    print(f"  [*] Serving on http://{host}:{port}")
    print(f"  [*] Mode: Production (Waitress)")
    print("="*60)
    
    serve(app, host=host, port=port)
