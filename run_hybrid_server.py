#!/usr/bin/env python3
"""
Wrapper script to run hybrid web server with environment variables loaded from .env
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify required variables are set
required_vars = ["SENTRY_DSN", "SENTRY_OTLP_ENDPOINT", "SENTRY_PUBLIC_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print("\n❌ Error: Missing required environment variables:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\nPlease ensure your .env file contains all required variables.")
    print("Run: ./setup_hybrid.sh to configure them.")
    sys.exit(1)

print("✅ Environment variables loaded successfully")
print(f"   SENTRY_DSN: {os.getenv('SENTRY_DSN')[:40]}...")
print(f"   SENTRY_OTLP_ENDPOINT: {os.getenv('SENTRY_OTLP_ENDPOINT')[:50]}...")
print(f"   SENTRY_PUBLIC_KEY: {'*' * len(os.getenv('SENTRY_PUBLIC_KEY'))}")
print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT', 'development')}")
print()

# Now run the hybrid web server
exec(open('hybrid/hybrid_web_main.py').read())

