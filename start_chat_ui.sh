#!/bin/bash

# Start Chat UI Script
# This script starts the web server with the chat interface

echo "🚀 Starting AI Chat Web Interface..."
echo ""

# Check if required environment variables are set
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
echo "🌐 Starting web server..."
echo "📱 Chat UI will be available at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the web server
python web_main.py

