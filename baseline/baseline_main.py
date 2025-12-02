"""
Baseline chat application WITHOUT custom Sentry instrumentation.

This demonstrates what you get with ONLY Sentry's out-of-the-box
auto-instrumentation. Compare traces from this app vs the custom
instrumented version to see the difference.
"""
from typing import Dict, Any, List
from core.config import get_settings
from baseline.baseline_sentry_config import setup_baseline_sentry
from baseline.baseline_state_graph import BaselineChatStateGraph


class BaselineChatService:
    """
    Chat service WITHOUT custom Sentry instrumentation.
    
    This is the "before" version - what your monitoring would look like
    if you just enabled Sentry's AI monitoring without any custom work.
    """
    
    def __init__(self):
        """Initialize the chat service."""
        # Setup baseline Sentry (auto-instrumentation only)
        setup_baseline_sentry()
        
        # Get configuration
        self.settings = get_settings()
        
        # Initialize the StateGraph
        self.chat_graph = BaselineChatStateGraph(self.settings.openai_api_key)
        
        print("Baseline chat service initialized (auto-instrumentation only)!")
    
    def process_message(self, user_input: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message - NO custom transaction or spans.
        
        This just runs the workflow and lets Sentry automatically capture
        whatever it can. No manual transaction creation, no custom spans,
        no manual instrumentation.
        """
        try:
            # Just call the graph - no transaction wrapper
            result = self.chat_graph.process_chat(user_input, conversation_history)
            
            return {
                "success": True,
                "response": result.get("processed_response", ""),
                "conversation_history": result.get("conversation_history", []),
                "metadata": {
                    "workflow_completed": True,
                    "response_metadata": result.get("response_metadata", {})
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "conversation_history": conversation_history or []
            }


def main():
    """Main entry point for baseline testing."""
    import sys
    import os
    
    try:
        # Check for required environment variables
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: OPENAI_API_KEY environment variable is required")
            print("Please set your OpenAI API key:")
            print("export OPENAI_API_KEY='your-api-key-here'")
            sys.exit(1)
        
        # Initialize and test
        chat_service = BaselineChatService()
        
        print("\n" + "="*60)
        print("🔬 BASELINE TEST - Auto-Instrumentation Only")
        print("="*60)
        print("\nThis uses ONLY Sentry's out-of-the-box AI monitoring.")
        print("Compare traces in Sentry to see what's missing vs custom instrumentation.\n")
        
        # Test message
        test_message = "Hello! Tell me a fun fact about Python programming."
        print(f"📝 Test message: {test_message}")
        
        result = chat_service.process_message(test_message)
        
        if result["success"]:
            print(f"\n✅ Response: {result['response']}")
            print("\n💡 Check Sentry dashboard for traces in the '-baseline' environment")
            print("   Compare with traces from the custom instrumented version!")
        else:
            print(f"\n❌ Error: {result['error']}")
        
    except Exception as e:
        print(f"❌ Failed to run baseline test: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()





