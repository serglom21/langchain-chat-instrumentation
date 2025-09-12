#!/usr/bin/env python3
"""
Setup script for the LangChain + StateGraph Sentry instrumentation example.

This script helps users set up the environment and verify their configuration.
"""

import os
import sys
from pathlib import Path


def check_environment():
    """Check if required environment variables are set."""
    print("🔍 Checking environment configuration...")
    
    required_vars = {
        "OPENAI_API_KEY": "Your OpenAI API key for LLM calls",
        "SENTRY_DSN": "Your Sentry DSN for error tracking and monitoring"
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  • {var}: {description}")
        else:
            print(f"  ✅ {var}: Set")
    
    if missing_vars:
        print("\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(var)
        print("\n💡 Set them using:")
        print("  export OPENAI_API_KEY='your-key-here'")
        print("  export SENTRY_DSN='your-dsn-here'")
        return False
    
    print("  ✅ All required environment variables are set!")
    return True


def check_dependencies():
    """Check if required Python packages are installed."""
    print("\n📦 Checking Python dependencies...")
    
    required_packages = [
        "sentry_sdk",
        "langchain",
        "langchain_openai",
        "langgraph",
        "pydantic"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}: Installed")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}: Missing")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Install them using:")
        print("  pip install -r requirements.txt")
        return False
    
    print("  ✅ All required packages are installed!")
    return True


def create_env_template():
    """Create a .env.template file for users."""
    template_content = """# Environment variables for LangChain + StateGraph Sentry instrumentation
# Copy this file to .env and fill in your actual values

# OpenAI API Key (required for LLM calls)
OPENAI_API_KEY=your-openai-api-key-here

# Sentry DSN (required for monitoring and error tracking)
SENTRY_DSN=your-sentry-dsn-here

# Sentry Environment (optional, defaults to 'development')
SENTRY_ENVIRONMENT=development
"""
    
    template_path = Path(".env.template")
    if not template_path.exists():
        with open(template_path, "w") as f:
            f.write(template_content)
        print(f"\n📄 Created {template_path} - copy to .env and fill in your values")
    else:
        print(f"\n📄 {template_path} already exists")


def main():
    """Run the setup checks."""
    print("🚀 LangChain + StateGraph Sentry Instrumentation Setup")
    print("=" * 60)
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check environment
    env_ok = check_environment()
    
    # Create template
    create_env_template()
    
    print("\n" + "=" * 60)
    
    if deps_ok and env_ok:
        print("🎉 Setup complete! You're ready to run the example.")
        print("\nNext steps:")
        print("  1. Run: python example.py")
        print("  2. Check your Sentry dashboard for traces")
        print("  3. Explore the AI Agent monitoring data")
    else:
        print("❌ Setup incomplete. Please fix the issues above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
