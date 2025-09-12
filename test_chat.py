"""Test script for the chat service with Sentry instrumentation."""
import os
import sys
from main import ChatService


def test_chat_service():
    """Test the chat service with sample inputs to verify Sentry instrumentation."""
    print("🧪 Testing Chat Service with Sentry Instrumentation...")
    
    # Set environment variables for testing
    # Note: Replace with your actual keys for testing
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"
    os.environ["SENTRY_DSN"] = "your-sentry-dsn-here"
    
    try:
        # Initialize the chat service
        chat_service = ChatService()
        
        # Test cases
        test_cases = [
            "Hello, how are you?",
            "What is the capital of France?",
            "Can you help me write a Python function?",
            "Tell me a joke"
        ]
        
        conversation_history = []
        
        for i, test_input in enumerate(test_cases, 1):
            print(f"\n📝 Test {i}: {test_input}")
            print("-" * 50)
            
            result = chat_service.process_message(test_input, conversation_history)
            
            if result["success"]:
                print(f"✅ Response: {result['response']}")
                
                # Show timing information
                if result["metadata"].get("token_timing"):
                    timing = result["metadata"]["token_timing"]
                    if timing.get("first_token") and timing.get("last_token"):
                        first_token_ms = int((timing["first_token"] - timing.get("start_time", 0)) * 1000)
                        total_time_ms = int((timing["last_token"] - timing.get("start_time", 0)) * 1000)
                        print(f"⏱️  Timing: {first_token_ms}ms to first token, {total_time_ms}ms total")
                
                conversation_history = result["conversation_history"]
            else:
                print(f"❌ Error: {result['error']}")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_chat_service()
    sys.exit(0 if success else 1)
