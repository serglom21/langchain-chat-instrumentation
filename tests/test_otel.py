"""
Test script for OpenTelemetry instrumentation.

This script tests the OpenTelemetry implementation and verifies that
traces are being sent to Sentry via OTLP.
"""
import time
import sys
from opentelemetry import trace

from otel.otel_config import setup_opentelemetry, shutdown_opentelemetry, get_tracer
from otel.otel_state_graph import OtelChatStateGraph
from otel.otel_instrumentation import create_span, add_span_attributes
from core.config import get_settings


def test_basic_span():
    """Test basic span creation and attributes."""
    print("\n" + "="*80)
    print("Test 1: Basic Span Creation")
    print("="*80)
    
    tracer = get_tracer()
    
    with tracer.start_as_current_span("test_span") as span:
        span.set_attribute("test.name", "basic_span_test")
        span.set_attribute("test.value", 42)
        print("✅ Created span with attributes")
        time.sleep(0.1)
    
    print("✅ Span completed")


def test_nested_spans():
    """Test nested span creation."""
    print("\n" + "="*80)
    print("Test 2: Nested Spans")
    print("="*80)
    
    tracer = get_tracer()
    
    with tracer.start_as_current_span("parent_span") as parent:
        parent.set_attribute("level", "parent")
        print("✅ Created parent span")
        
        with tracer.start_as_current_span("child_span_1") as child1:
            child1.set_attribute("level", "child")
            child1.set_attribute("child_id", 1)
            print("  ✅ Created child span 1")
            time.sleep(0.05)
        
        with tracer.start_as_current_span("child_span_2") as child2:
            child2.set_attribute("level", "child")
            child2.set_attribute("child_id", 2)
            print("  ✅ Created child span 2")
            time.sleep(0.05)
    
    print("✅ All spans completed")


def test_chat_workflow():
    """Test the full chat workflow with OpenTelemetry."""
    print("\n" + "="*80)
    print("Test 3: Chat Workflow")
    print("="*80)
    
    settings = get_settings()
    tracer = get_tracer()
    
    # Create chat graph
    chat_graph = OtelChatStateGraph(settings.openai_api_key)
    
    # Test message
    test_message = "What is 2+2?"
    print(f"User: {test_message}")
    
    # Create root span for the workflow
    with tracer.start_as_current_span(
        "Test Chat Workflow",
        kind=trace.SpanKind.SERVER
    ) as transaction:
        transaction.set_attribute("test.type", "chat_workflow")
        transaction.set_attribute("test.message", test_message)
        
        start_time = time.time()
        
        # Process chat
        result = chat_graph.process_chat(user_input=test_message)
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Extract response
        response = result.get("processed_response", "No response")
        
        transaction.set_attribute("response.length", len(response))
        transaction.set_attribute("workflow.duration_ms", duration_ms)
        
        print(f"Assistant: {response}")
        print(f"Duration: {duration_ms:.2f}ms")
        
        # Check token timing
        if "token_timing" in result:
            token_timing = result["token_timing"]
            if "time_to_first_token_ms" in token_timing:
                print(f"Time to First Token: {token_timing['time_to_first_token_ms']}ms")
                transaction.set_attribute("time_to_first_token_ms", 
                    token_timing["time_to_first_token_ms"])
    
    print("✅ Chat workflow completed")


def test_error_handling():
    """Test error handling and exception recording."""
    print("\n" + "="*80)
    print("Test 4: Error Handling")
    print("="*80)
    
    tracer = get_tracer()
    
    try:
        with tracer.start_as_current_span("error_test_span") as span:
            span.set_attribute("test.type", "error_handling")
            print("✅ Created span")
            
            # Simulate an error
            raise ValueError("This is a test error")
    except ValueError as e:
        print(f"✅ Caught exception: {e}")
        print("✅ Exception recorded in span")


def test_custom_instrumentation():
    """Test custom instrumentation helpers."""
    print("\n" + "="*80)
    print("Test 5: Custom Instrumentation Helpers")
    print("="*80)
    
    with create_span("custom_operation", "test.operation") as span:
        print("✅ Created span with helper")
        
        # Add attributes
        add_span_attributes(
            test_key="test_value",
            test_number=123,
            test_bool=True
        )
        print("✅ Added custom attributes")
        
        # Add nested span
        with create_span("nested_operation", "test.nested"):
            print("  ✅ Created nested span")
            time.sleep(0.05)
    
    print("✅ Custom instrumentation completed")


def run_all_tests():
    """Run all tests."""
    print("\n" + "🔭"*40)
    print("OpenTelemetry Instrumentation Test Suite")
    print("🔭"*40)
    print("\nThis will create test traces and send them to Sentry via OTLP")
    print("Check your Sentry dashboard after running this script.\n")
    
    # Initialize OpenTelemetry
    setup_opentelemetry()
    
    try:
        # Run tests
        test_basic_span()
        test_nested_spans()
        test_custom_instrumentation()
        test_error_handling()
        test_chat_workflow()
        
        print("\n" + "="*80)
        print("✅ All Tests Completed Successfully!")
        print("="*80)
        print("\n🔄 Flushing traces to Sentry...")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Shutdown to flush all spans
        shutdown_opentelemetry()
        print("✅ Traces flushed to Sentry via OTLP")
        print("\n📊 Check your Sentry dashboard:")
        print("   https://sentry.io/organizations/your-org/performance/")
        print("\n   Look for service: langchain-chat-instrumentation")
        print("   Filter by: Test spans and Chat Workflow spans")


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        shutdown_opentelemetry()
        sys.exit(0)


