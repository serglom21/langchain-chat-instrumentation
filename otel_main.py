"""
Main entry point for the OpenTelemetry-instrumented chat application.

This demonstrates the same chat workflow as main.py but using OpenTelemetry
instead of the Sentry SDK, with data sent to Sentry via OTLP protocol.
"""
import sys
import time
from opentelemetry import trace

from config import get_settings
from otel_config import setup_opentelemetry, shutdown_opentelemetry
from otel_state_graph import OtelChatStateGraph
from otel_instrumentation import create_span, add_span_attributes


def run_chat_example():
    """Run an example chat interaction with OpenTelemetry instrumentation."""
    settings = get_settings()
    
    # Initialize OpenTelemetry with Sentry OTLP exporter
    tracer = setup_opentelemetry()
    
    print("\n" + "="*80)
    print("🔭 OpenTelemetry-Instrumented Chat Application")
    print("="*80)
    print(f"Environment: {settings.sentry_environment}")
    print(f"Sending traces to Sentry via OTLP protocol")
    print("="*80 + "\n")
    
    # Create the chat state graph
    chat_graph = OtelChatStateGraph(settings.openai_api_key)
    
    # Example conversation
    test_messages = [
        "What is the capital of France?",
        "Tell me an interesting fact about it.",
        "What's the weather like there in summer?"
    ]
    
    conversation_history = []
    
    for i, user_message in enumerate(test_messages, 1):
        print(f"\n{'─'*80}")
        print(f"💬 Message {i}/{len(test_messages)}")
        print(f"{'─'*80}")
        print(f"User: {user_message}")
        
        # Create a root span for this chat interaction (equivalent to Sentry transaction)
        with tracer.start_as_current_span(
            name=f"Chat Workflow: process_chat",
            kind=trace.SpanKind.SERVER,
        ) as transaction_span:
            # Set transaction-level attributes
            transaction_span.set_attribute("workflow.type", "chat")
            transaction_span.set_attribute("workflow.message_number", i)
            transaction_span.set_attribute("user.input", user_message)
            transaction_span.set_attribute("conversation.history_length", len(conversation_history))
            
            start_time = time.time()
            
            # Process the chat message through the workflow
            result = chat_graph.process_chat(
                user_input=user_message,
                conversation_history=conversation_history
            )
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Extract response
            response = result.get("processed_response", "No response generated")
            conversation_history = result.get("conversation_history", conversation_history)
            
            # Add response attributes to transaction
            transaction_span.set_attribute("response.length", len(response))
            transaction_span.set_attribute("response.word_count", len(response.split()))
            transaction_span.set_attribute("workflow.duration_ms", duration_ms)
            
            # Add token timing if available
            if "token_timing" in result:
                token_timing = result["token_timing"]
                if "time_to_first_token_ms" in token_timing:
                    transaction_span.set_attribute("time_to_first_token_ms", 
                        token_timing["time_to_first_token_ms"])
                if "time_to_last_token_ms" in token_timing:
                    transaction_span.set_attribute("time_to_last_token_ms", 
                        token_timing["time_to_last_token_ms"])
            
            print(f"\n🤖 Assistant: {response}")
            print(f"\n⏱️  Total Duration: {duration_ms:.2f}ms")
            
            if "token_timing" in result:
                token_timing = result["token_timing"]
                if token_timing.get("time_to_first_token_ms"):
                    print(f"⚡ Time to First Token: {token_timing['time_to_first_token_ms']}ms")
                if token_timing.get("time_to_last_token_ms"):
                    print(f"🏁 Time to Last Token: {token_timing['time_to_last_token_ms']}ms")
        
        # Small delay between messages
        if i < len(test_messages):
            time.sleep(1)
    
    print(f"\n{'='*80}")
    print("✅ Chat session completed!")
    print(f"Total messages: {len(test_messages)}")
    print(f"Conversation history: {len(conversation_history)} entries")
    print("="*80 + "\n")
    
    # Shutdown OpenTelemetry to flush all spans
    print("🔄 Flushing all traces to Sentry...")
    shutdown_opentelemetry()
    print("✅ All traces sent to Sentry via OTLP!")
    print("\n📊 Check your Sentry dashboard to see the traces:")
    print("   https://sentry.io/organizations/your-org/performance/")


def run_single_chat(user_input: str):
    """Run a single chat interaction (useful for testing)."""
    settings = get_settings()
    
    # Initialize OpenTelemetry
    tracer = setup_opentelemetry()
    
    # Create the chat state graph
    chat_graph = OtelChatStateGraph(settings.openai_api_key)
    
    # Create a root span for this chat interaction
    with tracer.start_as_current_span(
        name="Chat Workflow: process_chat",
        kind=trace.SpanKind.SERVER,
    ) as transaction_span:
        transaction_span.set_attribute("workflow.type", "chat")
        transaction_span.set_attribute("user.input", user_input)
        
        # Process the chat message
        result = chat_graph.process_chat(user_input=user_input)
        
        # Extract response
        response = result.get("processed_response", "No response generated")
        
        transaction_span.set_attribute("response.length", len(response))
        
        print(f"User: {user_input}")
        print(f"Assistant: {response}")
    
    # Shutdown to flush spans
    shutdown_opentelemetry()
    
    return response


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            # Single message mode
            user_message = " ".join(sys.argv[1:])
            run_single_chat(user_message)
        else:
            # Example conversation mode
            run_chat_example()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        shutdown_opentelemetry()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        shutdown_opentelemetry()
        sys.exit(1)


