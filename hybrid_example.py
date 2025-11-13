"""
Example demonstrating hybrid OpenTelemetry + Sentry SDK instrumentation.

This shows how to:
1. Use OTel for distributed tracing
2. Use Sentry SDK for error reporting
3. Link errors to traces automatically
"""

import os
import time
from typing import Dict, Any

# Ensure environment variables are set
os.environ.setdefault("SENTRY_DSN", "YOUR_SENTRY_DSN_HERE")
os.environ.setdefault("SENTRY_OTLP_ENDPOINT", "YOUR_OTLP_ENDPOINT_HERE")
os.environ.setdefault("SENTRY_PUBLIC_KEY", "YOUR_PUBLIC_KEY_HERE")

from hybrid_config import init_hybrid_instrumentation, shutdown_instrumentation
from hybrid_instrumentation import (
    instrument_node,
    create_span,
    capture_exception_with_span_context,
    capture_message_with_span_context,
    add_span_attributes,
    add_span_annotation,
    set_ai_attributes,
    track_timing_metric,
)


class ChatWorkflow:
    """Example chat workflow using hybrid instrumentation."""
    
    @instrument_node("input_validation", "validation")
    def validate_input(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user input."""
        user_input = state.get("user_input", "")
        
        # Add custom attributes
        add_span_attributes(
            input_length=len(user_input),
            word_count=len(user_input.split()),
        )
        
        if not user_input:
            # This error will be captured by Sentry and linked to the OTel span
            raise ValueError("Empty input provided")
        
        if len(user_input) > 1000:
            # This error will also be captured with full context
            raise ValueError("Input too long (max 1000 characters)")
        
        # Add an annotation (will be stored as attributes in OTel, breadcrumb in Sentry)
        add_span_annotation(
            "Input validation passed",
            {"validation_time_ms": 5},
            level="info"
        )
        
        state["validated"] = True
        return state
    
    @instrument_node("llm_generation", "ai_processing")
    def generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LLM response."""
        user_input = state.get("user_input", "")
        
        # Create a child span for the actual LLM call
        with create_span("OpenAI API Call", "ai.chat") as span:
            # Track time to first token
            start_time = time.time()
            
            # Simulate LLM call
            try:
                # This would be your actual LLM call
                response = self._call_llm(user_input)
                
                ttft = (time.time() - start_time) * 1000
                
                # Track the metric in both systems
                track_timing_metric("time_to_first_token", ttft, {
                    "model": "gpt-3.5-turbo",
                })
                
                # Set AI-specific attributes
                set_ai_attributes(
                    span,
                    model="gpt-3.5-turbo",
                    operation="chat",
                    provider="openai",
                    prompts=[user_input],
                    response=response,
                    token_usage={
                        "prompt_tokens": 50,
                        "completion_tokens": 100,
                        "total_tokens": 150,
                    }
                )
                
                state["response"] = response
                
            except Exception as e:
                # Error is automatically captured by create_span context manager
                # It will appear in Sentry linked to this OTel span
                raise
        
        return state
    
    def _call_llm(self, prompt: str) -> str:
        """Simulate LLM call."""
        # Simulate some processing
        time.sleep(0.1)
        
        # Simulate an error 20% of the time
        import random
        if random.random() < 0.2:
            raise Exception("LLM API timeout")
        
        return f"Response to: {prompt}"
    
    @instrument_node("response_formatting", "formatting")
    def format_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format the response."""
        response = state.get("response", "")
        
        # Create a span for formatting work
        with create_span("Format Markdown", "formatting") as span:
            formatted = f"**AI Response:**\n\n{response}"
            
            add_span_attributes(
                original_length=len(response),
                formatted_length=len(formatted),
            )
            
            state["formatted_response"] = formatted
        
        return state


def example_successful_workflow():
    """Example of a successful workflow execution."""
    print("\n" + "="*60)
    print("Example 1: Successful Workflow")
    print("="*60)
    
    workflow = ChatWorkflow()
    
    # Create a root span for the entire workflow
    with create_span("Chat Workflow", "workflow.execution") as span:
        state = {"user_input": "Hello, how are you?"}
        
        # Execute workflow steps
        state = workflow.validate_input(state)
        state = workflow.generate_response(state)
        state = workflow.format_response(state)
        
        print(f"✅ Workflow completed successfully")
        print(f"   Final response: {state['formatted_response'][:50]}...")


def example_validation_error():
    """Example of a validation error being captured."""
    print("\n" + "="*60)
    print("Example 2: Validation Error")
    print("="*60)
    
    workflow = ChatWorkflow()
    
    try:
        with create_span("Chat Workflow", "workflow.execution") as span:
            state = {"user_input": ""}  # Empty input will cause error
            state = workflow.validate_input(state)
    except ValueError as e:
        print(f"❌ Validation error caught: {e}")
        print(f"   This error was sent to Sentry linked to the OTel span")


def example_llm_error():
    """Example of an LLM error being captured."""
    print("\n" + "="*60)
    print("Example 3: LLM Error (with retry logic)")
    print("="*60)
    
    workflow = ChatWorkflow()
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with create_span(
                f"Chat Workflow (attempt {attempt + 1})",
                "workflow.execution"
            ) as span:
                add_span_attributes(
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                
                state = {"user_input": "Hello!"}
                state = workflow.validate_input(state)
                state = workflow.generate_response(state)
                state = workflow.format_response(state)
                
                print(f"✅ Workflow succeeded on attempt {attempt + 1}")
                break
                
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                # Capture as warning (will retry)
                capture_message_with_span_context(
                    f"Retry {attempt + 1} of {max_retries} after error",
                    level="warning",
                    tags={"attempt": attempt + 1},
                )
                time.sleep(1)  # Wait before retry
            else:
                # Final failure - capture as error
                capture_exception_with_span_context(
                    e,
                    tags={"final_failure": True, "attempts": max_retries},
                )
                print(f"❌ All {max_retries} attempts failed")


def example_custom_error_capture():
    """Example of manually capturing errors with context."""
    print("\n" + "="*60)
    print("Example 4: Custom Error Capture with Context")
    print("="*60)
    
    with create_span("Custom Operation", "custom", capture_errors_to_sentry=False) as span:
        try:
            # Some risky operation
            result = 10 / 0
        except ZeroDivisionError as e:
            # Manually capture with rich context
            event_id = capture_exception_with_span_context(
                e,
                level="error",
                tags={
                    "operation": "division",
                    "component": "math_operations",
                },
                extra={
                    "numerator": 10,
                    "denominator": 0,
                    "expected_behavior": "Should validate denominator first",
                }
            )
            print(f"❌ Error captured with event ID: {event_id}")
            print(f"   Error is linked to OTel trace and will appear in Sentry")


def main():
    """Run all examples."""
    print("\n" + "🚀" * 30)
    print("Hybrid OpenTelemetry + Sentry SDK Example")
    print("🚀" * 30)
    
    # Initialize instrumentation
    try:
        init_hybrid_instrumentation(
            service_name="hybrid-example",
            service_version="1.0.0",
            environment="development",
        )
    except ValueError as e:
        print(f"\n⚠️  Configuration error: {e}")
        print("\nPlease set these environment variables:")
        print("  - SENTRY_DSN: Your Sentry project DSN")
        print("  - SENTRY_OTLP_ENDPOINT: Your Sentry OTLP endpoint")
        print("  - SENTRY_PUBLIC_KEY: Your Sentry public key")
        print("\nYou can find these in your Sentry project settings:")
        print("  Settings > Projects > [Your Project] > Client Keys (DSN)")
        return
    
    # Run examples
    try:
        example_successful_workflow()
        time.sleep(1)
        
        example_validation_error()
        time.sleep(1)
        
        example_llm_error()
        time.sleep(1)
        
        example_custom_error_capture()
        time.sleep(1)
        
    finally:
        # Shutdown and flush all telemetry
        print("\n" + "="*60)
        print("Flushing telemetry data...")
        print("="*60)
        shutdown_instrumentation()
    
    print("\n✅ All examples completed!")
    print("\nCheck your Sentry dashboard to see:")
    print("  1. OpenTelemetry traces with distributed tracing")
    print("  2. Errors linked to specific spans")
    print("  3. AI/LLM metrics and attributes")
    print("  4. Custom breadcrumbs and context")


if __name__ == "__main__":
    main()

