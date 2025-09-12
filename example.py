#!/usr/bin/env python3
"""
Example usage of the LangChain + StateGraph Sentry instrumentation.

This script demonstrates how to use the instrumented chat service
and what to expect in your Sentry traces.
"""

import os
from main import ChatService


def main():
    """Run example chat interactions with Sentry instrumentation."""
    
    # Set up environment variables
    # Replace with your actual values
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"
    os.environ["SENTRY_DSN"] = "your-sentry-dsn-here"
    os.environ["SENTRY_ENVIRONMENT"] = "development"
    
    print("🚀 Starting LangChain + StateGraph Sentry Instrumentation Example")
    print("=" * 70)
    
    try:
        # Initialize the chat service
        print("📡 Initializing Chat Service with Sentry...")
        chat_service = ChatService()
        
        # Example conversation
        conversation_history = []
        
        # Test different types of interactions
        test_messages = [
            "Hello! Can you help me understand how this works?",
            "What is the capital of France?",
            "Can you write a simple Python function to calculate fibonacci?",
            "Tell me a programming joke"
        ]
        
        print(f"\n💬 Running {len(test_messages)} test interactions...")
        print("=" * 70)
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📝 Test {i}: {message}")
            print("-" * 50)
            
            # Process the message (this creates Sentry traces)
            result = chat_service.process_message(message, conversation_history)
            
            if result["success"]:
                print(f"✅ Response: {result['response']}")
                conversation_history = result["conversation_history"]
            else:
                print(f"❌ Error: {result['error']}")
        
        print("\n" + "=" * 70)
        print("🎉 Example completed!")
        print("\n📊 Check your Sentry dashboard to see:")
        print("   • Complete trace hierarchy")
        print("   • AI Agent monitoring data")
        print("   • Token usage and costs")
        print("   • Performance metrics")
        print("   • Custom node spans")
        
    except Exception as e:
        print(f"❌ Error running example: {e}")
        print("\n💡 Make sure to set your OPENAI_API_KEY and SENTRY_DSN environment variables")


if __name__ == "__main__":
    main()
