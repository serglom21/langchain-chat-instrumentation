#!/usr/bin/env python3
"""
Test script to verify both CLI and web modes work correctly.
"""
import os
import sys
import json
import requests
import time
from main import ChatService


def test_cli_mode():
    """Test that CLI mode still works."""
    print("🧪 Testing CLI Mode...")
    print("-" * 30)
    
    try:
        # Initialize chat service (same as before)
        chat_service = ChatService()
        
        # Test a simple message
        result = chat_service.process_message("Hello, this is a test!", [])
        
        if result["success"]:
            print("✅ CLI mode works correctly")
            print(f"   Response: {result['response'][:50]}...")
            return True
        else:
            print(f"❌ CLI mode failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ CLI mode error: {e}")
        return False


def test_web_mode():
    """Test that web mode works."""
    print("\n🌐 Testing Web Mode...")
    print("-" * 30)
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint works")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
        
        # Test info endpoint
        response = requests.get("http://localhost:8000/info", timeout=5)
        if response.status_code == 200:
            print("✅ Info endpoint works")
        else:
            print(f"❌ Info endpoint failed: {response.status_code}")
            return False
        
        # Test chat endpoint
        chat_data = {
            "message": "Hello, this is a web test!",
            "conversation_history": []
        }
        
        response = requests.post(
            "http://localhost:8000/chat",
            json=chat_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ Chat endpoint works")
                print(f"   Response: {result['response'][:50]}...")
                return True
            else:
                print(f"❌ Chat endpoint failed: {result.get('error')}")
                return False
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Web server not running. Start it with: python web_main.py")
        return False
    except Exception as e:
        print(f"❌ Web mode error: {e}")
        return False


def main():
    """Run integration tests."""
    print("🚀 AI Chat Integration Test")
    print("=" * 50)
    
    # Test CLI mode
    cli_success = test_cli_mode()
    
    # Test web mode (only if server is running)
    web_success = test_web_mode()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   CLI Mode: {'✅ PASS' if cli_success else '❌ FAIL'}")
    print(f"   Web Mode: {'✅ PASS' if web_success else '❌ FAIL'}")
    
    if cli_success and web_success:
        print("\n🎉 All tests passed! Both modes work correctly.")
        print("\n💡 Usage:")
        print("   CLI Mode: python main.py")
        print("   Web Mode: python web_main.py")
        print("   API Test: curl -X POST http://localhost:8000/chat \\")
        print("             -H 'Content-Type: application/json' \\")
        print("             -d '{\"message\": \"Hello!\"}'")
    elif cli_success:
        print("\n✅ CLI mode works. Web server needs to be started.")
        print("   Run: python web_main.py")
    else:
        print("\n❌ Some tests failed. Check your configuration.")
    
    return cli_success and web_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
