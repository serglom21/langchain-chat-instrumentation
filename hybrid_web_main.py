"""
Web server with HYBRID OpenTelemetry + Sentry SDK instrumentation.

This demonstrates:
- OTel traces sent to Sentry via OTLP
- Errors captured by Sentry SDK
- Both linked together via trace context

Test endpoints:
- /api/chat - Normal chat (traces + any errors)
- /api/test-error - Intentionally throw error to test capturing
- /health - Health check
"""
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from opentelemetry import trace
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

from config import get_settings
from hybrid_config import init_hybrid_instrumentation, shutdown_instrumentation
from hybrid_instrumentation import (
    create_span,
    capture_exception_with_span_context,
    add_span_attributes,
    add_span_annotation,
    track_timing_metric,
)
from otel_state_graph import OtelChatStateGraph


# Initialize HYBRID instrumentation (both OTel and Sentry SDK)
init_hybrid_instrumentation(
    service_name="chat-web-hybrid",
    service_version="1.0.0",
    environment="development",
)

# Initialize settings and chat graph
settings = get_settings()
chat_graph = OtelChatStateGraph(settings.openai_api_key)

# Store conversation histories (in production, use a database)
conversation_histories = {}


async def test_error_endpoint(request):
    """
    Test endpoint to demonstrate hybrid instrumentation.
    
    This endpoint intentionally throws different types of errors
    to show how they're captured in Sentry and linked to OTel traces.
    """
    try:
        # Parse request to get error type
        data = await request.json()
        error_type = data.get('error_type', 'generic')
        
        # Add span attributes
        add_span_attributes(
            test_endpoint=True,
            error_type_requested=error_type,
        )
        
        # Create a child span for the "operation"
        with create_span("Intentional Error Generation", "test.error") as span:
            span.set_attribute("error_type", error_type)
            
            add_span_annotation(
                "About to throw test error",
                {"error_type": error_type},
                level="warning"
            )
            
            # Throw different types of errors
            if error_type == 'validation':
                raise ValueError("Invalid input: test validation error")
            elif error_type == 'llm_timeout':
                raise TimeoutError("LLM API timeout after 30 seconds")
            elif error_type == 'division':
                result = 10 / 0
            else:
                raise Exception(f"Generic test error: {error_type}")
                
    except Exception as e:
        # THIS IS THE KEY DIFFERENCE:
        # Instead of span.record_exception(e) which gets dropped,
        # we use capture_exception_with_span_context(e) which:
        # 1. Captures to Sentry Issues (full stack trace)
        # 2. Links it to the OTel trace via trace_id and span_id
        
        capture_exception_with_span_context(
            e,
            tags={
                "endpoint": "/api/test-error",
                "error_type": error_type,
                "test_error": True,
            },
            extra={
                "message": "This is a test error to demonstrate hybrid instrumentation",
                "expected": True,
            }
        )
        
        return JSONResponse({
            'success': True,
            'message': 'Error captured successfully!',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'check_sentry': {
                'issues_tab': 'Error should appear here with full stack trace',
                'performance_tab': 'Trace should appear here with span details',
                'linked': 'Click trace_id tag in error to see the full trace'
            }
        })


async def chat_endpoint(request):
    """
    Handle chat requests with HYBRID instrumentation.
    
    Starlette instrumentation automatically creates a span for this endpoint.
    We add custom attributes and use hybrid error capturing.
    
    Test error injection:
    - Send "inject_error": "validation" to trigger error in validation span
    - Send "inject_error": "llm" to trigger error in LLM span
    - Send "inject_error": "formatting" to trigger error in formatting span
    """
    current_span = trace.get_current_span()
    
    try:
        # Parse request
        data = await request.json()
        user_input = data.get('message', '')
        session_id = data.get('session_id', 'default')
        inject_error = data.get('inject_error', None)  # For testing: validation, llm, formatting
        
        if not user_input:
            current_span.set_attribute("error", "empty_input")
            return JSONResponse({'error': 'Message is required'}, status_code=400)
        
        # Add request attributes
        add_span_attributes(
            session_id=session_id,
            input_length=len(user_input),
            input_word_count=len(user_input.split()),
        )
        
        # Get conversation history
        conversation_history = conversation_histories.get(session_id, [])
        current_span.set_attribute("chat.history_length", len(conversation_history))
        
        # Process chat with child span
        with create_span("Process Chat Workflow", "workflow.execution") as workflow_span:
            workflow_span.set_attribute("workflow.type", "chat")
            workflow_span.set_attribute("session_id", session_id)
            
            if inject_error:
                workflow_span.set_attribute("test.inject_error", inject_error)
            
            add_span_annotation(
                "Starting chat workflow",
                {"session_id": session_id, "history_items": len(conversation_history)},
                level="info"
            )
            
            # Validation span with potential error injection
            with create_span("Input Validation", "validation") as validation_span:
                validation_span.set_attribute("input_length", len(user_input))
                validation_span.set_attribute("has_conversation_history", len(conversation_history) > 0)
                
                if inject_error == "validation":
                    # Inject error in validation span
                    try:
                        raise ValueError(f"TEST ERROR: Validation failed for input '{user_input[:50]}'")
                    except ValueError as e:
                        capture_exception_with_span_context(
                            e,
                            tags={
                                "test_error": True,
                                "span": "validation",
                                "session_id": session_id,
                            },
                            extra={
                                "input": user_input,
                                "message": "This is a test error injected in the validation span"
                            }
                        )
                        # Continue anyway for testing
                        add_span_annotation("Recovered from test error", level="warning")
            
            # LLM processing span with potential error injection
            with create_span("LLM Processing", "ai.chat") as llm_span:
                llm_span.set_attribute("model", "gpt-3.5-turbo")
                llm_span.set_attribute("provider", "openai")
                
                if inject_error == "llm":
                    # Inject error in LLM span
                    try:
                        raise TimeoutError("TEST ERROR: OpenAI API timeout after 30 seconds")
                    except TimeoutError as e:
                        capture_exception_with_span_context(
                            e,
                            tags={
                                "test_error": True,
                                "span": "llm",
                                "model": "gpt-3.5-turbo",
                                "session_id": session_id,
                            },
                            extra={
                                "input": user_input,
                                "message": "This is a test error injected in the LLM span"
                            }
                        )
                        # Continue anyway for testing
                        add_span_annotation("Recovered from test error", level="warning")
                
                # Actual LLM call
                result = chat_graph.process_chat(
                    user_input=user_input,
                    conversation_history=conversation_history
                )
            
            # Extract response
            response_text = result.get("processed_response", "")
            updated_history = result.get("conversation_history", conversation_history)
            
            # Response formatting span with potential error injection
            with create_span("Response Formatting", "formatting") as format_span:
                format_span.set_attribute("response_length", len(response_text))
                format_span.set_attribute("format_type", "markdown")
                
                if inject_error == "formatting":
                    # Inject error in formatting span
                    try:
                        raise RuntimeError("TEST ERROR: Failed to format response - markdown parser error")
                    except RuntimeError as e:
                        capture_exception_with_span_context(
                            e,
                            tags={
                                "test_error": True,
                                "span": "formatting",
                                "session_id": session_id,
                            },
                            extra={
                                "response_length": len(response_text),
                                "message": "This is a test error injected in the formatting span"
                            }
                        )
                        # Continue anyway for testing
                        add_span_annotation("Recovered from test error", level="warning")
                
                format_span.set_attribute("word_count", len(response_text.split()))
            
            # Update conversation history
            conversation_histories[session_id] = updated_history
            
            # Track timing metrics
            if "token_timing" in result:
                token_timing = result["token_timing"]
                if "time_to_first_token_ms" in token_timing:
                    track_timing_metric(
                        "time_to_first_token",
                        token_timing["time_to_first_token_ms"],
                        {"session_id": session_id}
                    )
                if "time_to_last_token_ms" in token_timing:
                    track_timing_metric(
                        "time_to_last_token",
                        token_timing["time_to_last_token_ms"],
                        {"session_id": session_id}
                    )
            
            add_span_annotation(
                "Chat workflow completed",
                {"response_length": len(response_text)},
                level="info"
            )
        
        # Add success attributes
        current_span.set_attribute("chat.success", True)
        current_span.set_attribute("chat.response_length", len(response_text))
        
        response_data = {
            'response': response_text,
            'session_id': session_id,
            'conversation_length': len(updated_history)
        }
        
        # Add test info if error was injected
        if inject_error:
            response_data['test_info'] = {
                'error_injected_in_span': inject_error,
                'message': f'Test error captured in {inject_error} span and sent to Sentry',
                'check_sentry': 'Error should appear in Issues tab, linked to this trace'
            }
        
        return JSONResponse(response_data)
    
    except Exception as e:
        # HYBRID ERROR CAPTURING
        # Captured in Sentry Issues + linked to this trace
        capture_exception_with_span_context(
            e,
            tags={
                "endpoint": "/api/chat",
                "session_id": session_id,
            },
            extra={
                "user_input": user_input,
                "conversation_length": len(conversation_history),
            }
        )
        
        # Also set span status (for OTel trace visualization)
        current_span.set_attribute("chat.success", False)
        current_span.set_attribute("error.type", type(e).__name__)
        
        # Print error for debugging
        import traceback
        print(f"\n❌ ERROR in chat endpoint:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"\n   Error captured in Sentry Issues and linked to OTel trace!")
        traceback.print_exc()
        print()
        
        return JSONResponse({
            'error': str(e),
            'type': type(e).__name__
        }, status_code=500)


async def get_history(request):
    """Get conversation history for a session."""
    session_id = request.path_params['session_id']
    
    with create_span("Get History", "db.query") as span:
        span.set_attribute("session_id", session_id)
        
        history = conversation_histories.get(session_id, [])
        span.set_attribute("history_length", len(history))
    
    return JSONResponse({
        'session_id': session_id,
        'history': history,
        'length': len(history)
    })


async def clear_history(request):
    """Clear conversation history for a session."""
    session_id = request.path_params['session_id']
    
    with create_span("Clear History", "db.delete") as span:
        span.set_attribute("session_id", session_id)
        
        if session_id in conversation_histories:
            del conversation_histories[session_id]
            span.set_attribute("cleared", True)
            add_span_annotation(f"Cleared history for session {session_id}")
        else:
            span.set_attribute("cleared", False)
    
    return JSONResponse({
        'session_id': session_id,
        'cleared': True
    })


async def health(request):
    """Health check endpoint."""
    current_span = trace.get_current_span()
    current_span.set_attribute("health.status", "healthy")
    
    return JSONResponse({
        'status': 'healthy',
        'instrumentation': 'hybrid',
        'otel_exporter': 'sentry-otlp',
        'sentry_sdk': 'enabled',
        'environment': settings.sentry_environment,
        'test_endpoints': {
            'test_error': '/api/test-error',
            'usage': 'POST {"error_type": "validation|llm_timeout|division|generic"}'
        }
    })


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route('/api/chat', chat_endpoint, methods=['POST']),
        Route('/api/test-error', test_error_endpoint, methods=['POST']),
        Route('/api/history/{session_id}', get_history, methods=['GET']),
        Route('/api/clear/{session_id}', clear_history, methods=['POST']),
        Route('/health', health, methods=['GET']),
        Mount('/static', StaticFiles(directory='static'), name='static'),
        Mount('/', StaticFiles(directory='static', html=True), name='root'),
    ],
)

# Instrument Starlette with OpenTelemetry
StarletteInstrumentor.instrument_app(app)


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🔗 HYBRID OpenTelemetry + Sentry SDK Chat Application")
    print("="*80)
    print(f"Environment: {settings.sentry_environment}")
    print("Instrumentation: OpenTelemetry (traces) + Sentry SDK (errors)")
    print("Server: http://0.0.0.0:8003")
    print("="*80)
    print("\nTest Endpoints:")
    print("  1. Normal chat:  POST http://localhost:8003/api/chat")
    print("  2. Test error:   POST http://localhost:8003/api/test-error")
    print("  3. Health check: GET  http://localhost:8003/health")
    print("\nTo test error capturing:")
    print("  curl -X POST http://localhost:8003/api/test-error \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"error_type\": \"validation\"}'")
    print("\nCheck Sentry:")
    print("  • Issues tab: Error with full stack trace")
    print("  • Performance tab: Trace with span details")
    print("  • Click trace_id tag in error to see linked trace!")
    print("="*80 + "\n")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8003,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n⚠️  Server stopped by user")
    finally:
        print("\n🔄 Shutting down instrumentation...")
        shutdown_instrumentation()
        print("✅ Shutdown complete")

