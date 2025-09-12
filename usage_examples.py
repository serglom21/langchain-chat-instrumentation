#!/usr/bin/env python3
"""
Usage examples for both CLI and Web API modes.

This file demonstrates how to use the AI chat service in different ways.
"""
import os
import requests
import json
from main import ChatService


def cli_example():
    """Example of using CLI mode."""
    print("🖥️  CLI Mode Example")
    print("=" * 40)
    
    # Set environment variables (replace with your actual keys)
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"
    os.environ["SENTRY_DSN"] = "your-sentry-dsn-here"
    os.environ["SENTRY_ENVIRONMENT"] = "development"
    
    try:
        # Initialize chat service
        chat_service = ChatService()
        
        # Process a message
        result = chat_service.process_message("Hello! Can you tell me a joke?")
        
        if result["success"]:
            print(f"✅ Response: {result['response']}")
        else:
            print(f"❌ Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure to set your OPENAI_API_KEY environment variable")


def web_api_example():
    """Example of using Web API mode."""
    print("\n🌐 Web API Mode Example")
    print("=" * 40)
    
    # Example API calls (server must be running)
    base_url = "http://localhost:8000"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
        
        # Test info endpoint
        response = requests.get(f"{base_url}/info", timeout=5)
        if response.status_code == 200:
            info = response.json()
            print("✅ Service info retrieved")
            print(f"   Service: {info['service']}")
        else:
            print(f"❌ Info endpoint failed: {response.status_code}")
            return
        
        # Test chat endpoint
        chat_data = {
            "message": "What is the capital of France?",
            "conversation_history": []
        }
        
        response = requests.post(
            f"{base_url}/chat",
            json=chat_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ Chat request successful")
                print(f"   Response: {result['response']}")
            else:
                print(f"❌ Chat request failed: {result.get('error')}")
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Web server not running")
        print("💡 Start the server with: python web_main.py")
    except Exception as e:
        print(f"❌ Error: {e}")


def python_client_example():
    """Example of using the service as a Python client."""
    print("\n🐍 Python Client Example")
    print("=" * 40)
    
    class ChatClient:
        """Simple client for the chat service."""
        
        def __init__(self, base_url="http://localhost:8000"):
            self.base_url = base_url
            self.conversation_history = []
        
        def send_message(self, message: str):
            """Send a message and get response."""
            try:
                response = requests.post(
                    f"{self.base_url}/chat",
                    json={
                        "message": message,
                        "conversation_history": self.conversation_history
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        # Update conversation history
                        self.conversation_history = result.get("conversation_history", [])
                        return result["response"]
                    else:
                        return f"Error: {result.get('error')}"
                else:
                    return f"HTTP Error: {response.status_code}"
                    
            except requests.exceptions.ConnectionError:
                return "Error: Server not running. Start with: python web_main.py"
            except Exception as e:
                return f"Error: {e}"
    
    # Example usage
    try:
        client = ChatClient()
        
        # Send a few messages
        messages = [
            "Hello! How are you?",
            "What's the weather like?",
            "Can you tell me a programming joke?"
        ]
        
        for message in messages:
            print(f"👤 You: {message}")
            response = client.send_message(message)
            print(f"🤖 Assistant: {response}")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all examples."""
    print("🚀 AI Chat Service Usage Examples")
    print("=" * 50)
    
    # CLI Example
    cli_example()
    
    # Web API Example
    web_api_example()
    
    # Python Client Example
    python_client_example()
    
    print("\n" + "=" * 50)
    print("📚 How to Use:")
    print("1. CLI Mode: python main.py")
    print("2. Web Mode: python web_main.py")
    print("3. Test Integration: python test_web_integration.py")
    print("4. View Examples: python usage_examples.py")


if __name__ == "__main__":
    main()
