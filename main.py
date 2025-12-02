"""
Main chat application with StateGraph workflow and Sentry instrumentation.

This file demonstrates the key pattern for Sentry instrumentation:
1. Create a single transaction per request
2. All spans created within this transaction become children
3. LangGraph workflow creates spans within the transaction context
"""
import os
import sys
from typing import Dict, Any, List
from core.config import get_settings
from core.sentry_config import setup_sentry
from core.state_graph import ChatStateGraph
import sentry_sdk


class ChatService:
    """Main chat service application."""
    
    def __init__(self):
        """Initialize the chat service."""
        # Setup Sentry first
        setup_sentry()
        
        # Get configuration
        self.settings = get_settings()
        
        # Initialize the StateGraph
        self.chat_graph = ChatStateGraph(self.settings.openai_api_key)
        
        print("Chat service initialized successfully!")
        print(f"Sentry environment: {self.settings.sentry_environment}")
    
    def process_message(self, user_input: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message through the chat workflow.
        
        KEY PATTERN: This method creates the root transaction for the entire workflow.
        All spans created within this transaction (including LangGraph spans) will
        automatically become children of this transaction.
        """
        # Create transaction for the entire chat workflow
        with sentry_sdk.start_transaction(
            op="chat_workflow",
            name="Chat Workflow: chat_workflow"
        ) as transaction:
            transaction.set_tag("user_input_length", len(user_input))
            transaction.set_tag("conversation_history_length", len(conversation_history) if conversation_history else 0)
            
            try:
                result = self.chat_graph.process_chat(user_input, conversation_history)
                
                return {
                    "success": True,
                    "response": result.get("processed_response", ""),
                    "conversation_history": result.get("conversation_history", []),
                    "metadata": {
                        "workflow_completed": True,
                        "token_timing": result.get("token_timing"),
                        "response_metadata": result.get("response_metadata", {})
                    }
                }
                
            except Exception as e:
                sentry_sdk.capture_exception(e)
                return {
                    "success": False,
                    "error": str(e),
                    "response": "I apologize, but I encountered an error processing your request. Please try again.",
                    "conversation_history": conversation_history or []
                }
    
    def process_message_without_transaction(self, user_input: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message through the chat workflow WITHOUT creating a new transaction.
        
        This method is used by the web API to work within the existing HTTP transaction context.
        All spans created within this method will become children of the current transaction.
        """
        try:
            result = self.chat_graph.process_chat(user_input, conversation_history)
            
            return {
                "success": True,
                "response": result.get("processed_response", ""),
                "conversation_history": result.get("conversation_history", []),
                "metadata": {
                    "workflow_completed": True,
                    "token_timing": result.get("token_timing"),
                    "response_metadata": result.get("response_metadata", {})
                }
            }
            
        except Exception as e:
            sentry_sdk.capture_exception(e)
            
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "conversation_history": conversation_history or [],
                "metadata": {
                    "workflow_completed": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            }
    
    def run_interactive_chat(self):
        """Run an interactive chat session."""
        print("\n🤖 Chat Service Started!")
        print("Type 'quit', 'exit', or 'bye' to end the conversation.")
        print("=" * 50)
        
        conversation_history = []
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    print("Please enter a message.")
                    continue
                
                print("\n🤖 Assistant: ", end="", flush=True)
                
                # Process the message
                result = self.process_message(user_input, conversation_history)
                
                if result["success"]:
                    print(result["response"])
                    conversation_history = result["conversation_history"]
                    
                    # Display timing information if available
                    if result["metadata"].get("token_timing"):
                        timing = result["metadata"]["token_timing"]
                        if timing.get("first_token") and timing.get("last_token"):
                            first_token_ms = int((timing["first_token"] - timing.get("start_time", 0)) * 1000)
                            total_time_ms = int((timing["last_token"] - timing.get("start_time", 0)) * 1000)
                            print(f"\n⏱️  Timing: {first_token_ms}ms to first token, {total_time_ms}ms total")
                else:
                    print(result["response"])
                    print(f"Error: {result['error']}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                sentry_sdk.capture_exception(e)


def main():
    """Main entry point."""
    try:
        # Check for required environment variables
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: OPENAI_API_KEY environment variable is required")
            print("Please set your OpenAI API key:")
            print("export OPENAI_API_KEY='your-api-key-here'")
            sys.exit(1)
        
        # Initialize and run the chat service
        chat_service = ChatService()
        chat_service.run_interactive_chat()
        
    except Exception as e:
        print(f"❌ Failed to start chat service: {e}")
        sentry_sdk.capture_exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

