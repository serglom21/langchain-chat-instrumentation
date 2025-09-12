#!/usr/bin/env python3
"""
Web server entry point for the AI chat service.

This starts the Starlette web application with Uvicorn.
Your existing CLI functionality in main.py remains unchanged.
"""
import os
import sys
import uvicorn
from sentry_config import setup_sentry
from config import get_settings


def main():
    """Start the web server."""
    try:
        # Load settings from .env file
        settings = get_settings()
        
        # Check for required environment variables
        if not settings.openai_api_key:
            print("❌ Error: OPENAI_API_KEY environment variable is required")
            print("Please set your OpenAI API key in .env file or environment:")
            print("export OPENAI_API_KEY='your-api-key-here'")
            sys.exit(1)
        
        # Setup Sentry (same as CLI version)
        setup_sentry()
        
        print("🌐 Starting AI Chat Web Service...")
        print("=" * 50)
        print("📡 Sentry instrumentation: ENABLED")
        print("🔗 API Endpoints:")
        print("   POST http://localhost:8000/chat")
        print("   GET  http://localhost:8000/health")
        print("   GET  http://localhost:8000/info")
        print("=" * 50)
        print("💡 To use CLI mode instead, run: python main.py")
        print("=" * 50)
        
        # Start the web server
        uvicorn.run(
            "web_app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,  # Enable auto-reload for development
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n👋 Web server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start web server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
