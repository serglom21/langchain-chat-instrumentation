#!/bin/bash

# Start OpenTelemetry-instrumented chat web application
# This runs on port 8002 to avoid conflicts with the Sentry SDK version

echo "🔭 Starting OpenTelemetry-Instrumented Chat Application"
echo "=================================================="
echo ""
echo "This version uses OpenTelemetry with Sentry OTLP exporter"
echo "Port: 8002"
echo "URL: http://localhost:8002"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the OpenTelemetry web server
python otel_web_main.py


