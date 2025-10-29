#!/bin/bash

# Side-by-Side Comparison Script
# Starts both custom and baseline versions simultaneously

echo "🔬 Starting Side-by-Side Comparison"
echo "=" * 70
echo ""

# Check environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY environment variable is not set"
    echo "Please set it with: export OPENAI_API_KEY='your-api-key-here'"
    exit 1
fi

if [ -z "$SENTRY_DSN" ]; then
    echo "⚠️  Warning: SENTRY_DSN not set. Sentry instrumentation will be disabled."
    echo "To enable Sentry, set: export SENTRY_DSN='your-sentry-dsn-here'"
    echo ""
fi

echo "✅ Environment variables configured"
echo ""
echo "🚀 Starting both servers..."
echo ""
echo "📱 Custom Instrumented Version:"
echo "   URL: http://localhost:8000"
echo "   Theme: Purple"
echo "   Features: Full custom instrumentation"
echo ""
echo "🔬 Baseline Auto-Instrumentation:"
echo "   URL: http://localhost:8001"
echo "   Theme: Orange/Red"
echo "   Features: Out-of-the-box only"
echo ""
echo "💡 Open both URLs in separate browser tabs and send the SAME message to compare!"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start both servers in background
python web_main.py &
PID1=$!

python baseline_web_main.py &
PID2=$!

# Wait for both processes
wait $PID1 $PID2



