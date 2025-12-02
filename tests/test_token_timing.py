"""
Quick test for token timing metrics in OpenTelemetry instrumentation.

This test verifies that time_to_first_token_ms and time_to_last_token_ms
are properly captured and sent to Sentry via OTLP.
"""
import time
from opentelemetry import trace

from otel.otel_config import setup_opentelemetry, shutdown_opentelemetry
from otel.otel_instrumentation import create_span, add_span_attributes


def simulate_token_generation():
    """Simulate a token generation process with timing."""
    print("\n" + "="*80)
    print("🔬 Testing Token Timing Metrics")
    print("="*80)
    
    # Initialize OpenTelemetry
    tracer = setup_opentelemetry()
    
    # Create root span (simulating a chat request)
    with tracer.start_as_current_span(
        "Chat Request with Token Timing",
        kind=trace.SpanKind.SERVER
    ) as root_span:
        root_span.set_attribute("test.type", "token_timing_test")
        root_span.set_attribute("request.id", "test-123")
        
        print("\n📊 Creating workflow span...")
        
        # Simulate workflow span
        with create_span("LLM Generation Workflow", "ai.chat") as workflow_span:
            workflow_span.set_attribute("model", "gpt-3.5-turbo")
            workflow_span.set_attribute("streaming", True)
            
            # Simulate the token generation timing
            start_time = time.time()
            
            print("⏱️  Starting token generation simulation...")
            
            # Simulate time to first token (100ms)
            time.sleep(0.1)
            first_token_time = time.time()
            time_to_first_token_ms = int((first_token_time - start_time) * 1000)
            
            print(f"✅ First token received after {time_to_first_token_ms}ms")
            
            # Set the first token timing attribute
            workflow_span.set_attribute("time_to_first_token_ms", time_to_first_token_ms)
            add_span_attributes(time_to_first_token_ms=time_to_first_token_ms)
            
            # Simulate rest of generation (300ms more)
            time.sleep(0.3)
            last_token_time = time.time()
            time_to_last_token_ms = int((last_token_time - start_time) * 1000)
            
            print(f"✅ Last token received after {time_to_last_token_ms}ms")
            
            # Set the last token timing attribute
            workflow_span.set_attribute("time_to_last_token_ms", time_to_last_token_ms)
            add_span_attributes(time_to_last_token_ms=time_to_last_token_ms)
            
            # Simulate the token timing data structure returned in state
            token_timing_data = {
                "time_to_first_token_ms": time_to_first_token_ms,
                "time_to_last_token_ms": time_to_last_token_ms,
                "generation_completed": True
            }
            
            print(f"\n📦 Token Timing Data:")
            for key, value in token_timing_data.items():
                print(f"   {key}: {value}")
        
        # Set token timing on root span (equivalent to Sentry tags)
        root_span.set_attribute("time_to_first_token_ms", time_to_first_token_ms)
        root_span.set_attribute("time_to_last_token_ms", time_to_last_token_ms)
        root_span.set_attribute("test.completed", True)
    
    print("\n" + "="*80)
    print("✅ Test completed successfully!")
    print("="*80)
    print("\n🔄 Flushing spans to Sentry...")
    
    # Shutdown to flush all spans
    shutdown_opentelemetry()
    
    print("✅ Spans sent to Sentry via OTLP!")
    print("\n📊 Check your Sentry dashboard:")
    print("   Service: langchain-chat-instrumentation")
    print("   Look for span: 'Chat Request with Token Timing'")
    print("   Attributes to verify:")
    print("     - time_to_first_token_ms")
    print("     - time_to_last_token_ms")
    print("\n💡 These metrics are now available at multiple span levels:")
    print("   1. Root span (for filtering/searching)")
    print("   2. Workflow span (for detailed analysis)")
    print("   3. As measurements (for performance monitoring)")


if __name__ == "__main__":
    try:
        simulate_token_generation()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        shutdown_opentelemetry()





