"""
Web server entry point with OpenTelemetry instrumentation using Starlette.

This provides the same web interface as web_main.py but using OpenTelemetry
instead of the Sentry SDK, with data sent to Sentry via OTLP protocol.
"""
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from opentelemetry import trace
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from opentelemetry.trace import Status, StatusCode

from core.config import get_settings
from otel.otel_config import setup_opentelemetry, get_tracer, shutdown_opentelemetry
from otel.otel_state_graph import OtelChatStateGraph
from otel.otel_instrumentation import add_span_attributes, record_exception


# Initialize OpenTelemetry with Sentry OTLP exporter
setup_opentelemetry()

# Initialize settings and chat graph
settings = get_settings()
chat_graph = OtelChatStateGraph(settings.openai_api_key)

# Store conversation histories (in production, use a database)
conversation_histories = {}


async def chat_endpoint(request):
    """
    Handle chat requests with OpenTelemetry instrumentation.
    
    Starlette instrumentation automatically creates a span for this endpoint.
    We add custom attributes and child spans for detailed observability.
    """
    tracer = get_tracer()
    current_span = trace.get_current_span()
    
    try:
        # Parse request
        data = await request.json()
        user_input = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        if not user_input:
            current_span.set_attribute("error", "empty_input")
            return JSONResponse({'error': 'Message is required'}, status_code=400)
        
        # Add request attributes to current span
        current_span.set_attribute("chat.session_id", session_id)
        current_span.set_attribute("chat.user_input", user_input)
        current_span.set_attribute("chat.input_length", len(user_input))
        
        # Get conversation history
        conversation_history = conversation_histories.get(session_id, [])
        current_span.set_attribute("chat.history_length", len(conversation_history))
        
        # Process chat with workflow span
        with tracer.start_as_current_span(
            "Process Chat Workflow",
            kind=trace.SpanKind.INTERNAL
        ) as workflow_span:
            workflow_span.set_attribute("workflow.type", "chat")
            workflow_span.set_attribute("workflow.session_id", session_id)
            
            result = chat_graph.process_chat(
                user_input=user_input,
                conversation_history=conversation_history
            )
            
            # Extract response
            response_text = result.get("processed_response", "")
            updated_history = result.get("conversation_history", conversation_history)
            
            # Update conversation history
            conversation_histories[session_id] = updated_history
            
            # Add response attributes
            workflow_span.set_attribute("response.length", len(response_text))
            workflow_span.set_attribute("response.word_count", len(response_text.split()))
            
            # Add token timing if available
            if "token_timing" in result:
                token_timing = result["token_timing"]
                if "time_to_first_token_ms" in token_timing:
                    workflow_span.set_attribute("time_to_first_token_ms", 
                        token_timing["time_to_first_token_ms"])
                if "time_to_last_token_ms" in token_timing:
                    workflow_span.set_attribute("time_to_last_token_ms", 
                        token_timing["time_to_last_token_ms"])
        
        # Add success attributes to endpoint span
        current_span.set_attribute("chat.success", True)
        current_span.set_attribute("chat.response_length", len(response_text))
        current_span.set_status(Status(StatusCode.OK))
        
        return JSONResponse({
            'response': response_text,
            'session_id': session_id,
            'conversation_length': len(updated_history)
        })
    
    except Exception as e:
        # Record exception in span
        current_span.record_exception(e)
        current_span.set_attribute("chat.success", False)
        current_span.set_attribute("error.type", type(e).__name__)
        current_span.set_status(Status(StatusCode.ERROR, str(e)))
        
        record_exception(e)
        
        return JSONResponse({
            'error': str(e),
            'type': type(e).__name__
        }, status_code=500)


async def get_history(request):
    """Get conversation history for a session."""
    session_id = request.path_params['session_id']
    current_span = trace.get_current_span()
    current_span.set_attribute("chat.session_id", session_id)
    
    history = conversation_histories.get(session_id, [])
    current_span.set_attribute("chat.history_length", len(history))
    
    return JSONResponse({
        'session_id': session_id,
        'history': history,
        'length': len(history)
    })


async def clear_history(request):
    """Clear conversation history for a session."""
    session_id = request.path_params['session_id']
    current_span = trace.get_current_span()
    current_span.set_attribute("chat.session_id", session_id)
    
    if session_id in conversation_histories:
        del conversation_histories[session_id]
        current_span.set_attribute("chat.history_cleared", True)
    else:
        current_span.set_attribute("chat.history_cleared", False)
    
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
        'instrumentation': 'opentelemetry',
        'exporter': 'sentry-otlp',
        'environment': settings.sentry_environment
    })


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route('/api/chat', chat_endpoint, methods=['POST']),
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
    print("🔭 OpenTelemetry-Instrumented Chat Web Application (Starlette)")
    print("="*80)
    print(f"Environment: {settings.sentry_environment}")
    print("Instrumentation: OpenTelemetry with Sentry OTLP exporter")
    print("Server: http://0.0.0.0:8002")
    print("Static files: ./static/")
    print("="*80 + "\n")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8002,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n⚠️  Server stopped by user")
    finally:
        print("🔄 Shutting down OpenTelemetry...")
        shutdown_opentelemetry()
        print("✅ Shutdown complete")


