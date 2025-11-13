#!/bin/bash

# Setup script for hybrid OpenTelemetry + Sentry SDK instrumentation

echo "=================================="
echo "Hybrid Instrumentation Setup"
echo "=================================="
echo ""

# Check if .env file exists
if [ -f .env ]; then
    echo "⚠️  Found existing .env file"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping .env update"
        exit 0
    fi
    # Backup existing .env
    cp .env .env.backup.$(date +%s)
    echo "✅ Backed up existing .env"
fi

echo ""
echo "Let's configure your Sentry integration!"
echo ""
echo "You'll need to get these values from:"
echo "  Sentry → Settings → Projects → [Your Project] → Client Keys (DSN)"
echo ""

# Get Sentry DSN
echo -n "Enter your Sentry DSN: "
read SENTRY_DSN

if [ -z "$SENTRY_DSN" ]; then
    echo "❌ Sentry DSN is required"
    exit 1
fi

# Get OTLP endpoint
echo ""
echo -n "Enter your OTLP Traces Endpoint (e.g., https://o123.ingest.sentry.io/api/456/otlp/v1/traces): "
read SENTRY_OTLP_ENDPOINT

if [ -z "$SENTRY_OTLP_ENDPOINT" ]; then
    echo "❌ OTLP endpoint is required"
    exit 1
fi

# Get public key
echo ""
echo -n "Enter your Sentry Public Key: "
read SENTRY_PUBLIC_KEY

if [ -z "$SENTRY_PUBLIC_KEY" ]; then
    echo "❌ Public key is required"
    exit 1
fi

# Get environment (optional)
echo ""
echo -n "Enter environment name (default: development): "
read ENVIRONMENT
ENVIRONMENT=${ENVIRONMENT:-development}

# Get OpenAI key (optional)
echo ""
echo -n "Enter OpenAI API key (optional, press Enter to skip): "
read OPENAI_API_KEY

# Write to .env file
cat > .env << EOF
# Sentry Configuration
SENTRY_DSN=$SENTRY_DSN
SENTRY_OTLP_ENDPOINT=$SENTRY_OTLP_ENDPOINT
SENTRY_PUBLIC_KEY=$SENTRY_PUBLIC_KEY

# Environment
ENVIRONMENT=$ENVIRONMENT

# OpenAI (if using LLM features)
EOF

if [ -n "$OPENAI_API_KEY" ]; then
    echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env
fi

echo ""
echo "✅ Configuration saved to .env"
echo ""

# Test the configuration
echo "Testing configuration..."
python3 - << 'PYTHON_TEST'
import os
from dotenv import load_dotenv

load_dotenv()

required = ["SENTRY_DSN", "SENTRY_OTLP_ENDPOINT", "SENTRY_PUBLIC_KEY"]
missing = [k for k in required if not os.getenv(k)]

if missing:
    print(f"❌ Missing required variables: {', '.join(missing)}")
    exit(1)

print("✅ All required variables are set")
print("")
print(f"   SENTRY_DSN: {os.getenv('SENTRY_DSN')[:40]}...")
print(f"   OTLP_ENDPOINT: {os.getenv('SENTRY_OTLP_ENDPOINT')[:50]}...")
print(f"   PUBLIC_KEY: {'*' * len(os.getenv('SENTRY_PUBLIC_KEY'))}")
print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
PYTHON_TEST

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "Setup Complete! 🎉"
    echo "=================================="
    echo ""
    echo "Next steps:"
    echo "  1. Install dependencies: pip install -r requirements.txt"
    echo "  2. Run the example: python hybrid_example.py"
    echo "  3. Check your Sentry dashboard for traces and errors"
    echo ""
    echo "Documentation:"
    echo "  - Read HYBRID_INSTRUMENTATION.md for detailed guide"
    echo "  - See hybrid_example.py for usage examples"
    echo ""
else
    echo ""
    echo "❌ Configuration test failed"
    echo "Please check your .env file and try again"
    exit 1
fi

