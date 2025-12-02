"""
Mock web server for testing OpenTelemetry instrumentation without OpenAI.
This allows you to test the token timing metrics and span creation.
"""
import time
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from opentelemetry import trace
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from opentelemetry.trace import Status, StatusCode

from core.config import get_settings
from otel.otel_config import setup_opentelemetry, get_tracer
from otel.otel_instrumentation import create_span, add_span_attributes

# Initialize OpenTelemetry with Sentry OTLP exporter
setup_opentelemetry()

# Initialize settings
settings = get_settings()

# Store conversation histories (in production, use a database)
conversation_histories = {}


async def chat_endpoint(request):
    """
    Mock chat endpoint that simulates LLM response with token timing.
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
            "Process Chat Workflow (Mock)",
            kind=trace.SpanKind.INTERNAL
        ) as workflow_span:
            workflow_span.set_attribute("workflow.type", "chat")
            workflow_span.set_attribute("workflow.session_id", session_id)
            workflow_span.set_attribute("mock_mode", True)
            
            # Simulate LangGraph workflow
            with create_span("invoke_agent LangGraph (Mock)", "gen_ai.invoke_agent") as agent_span:
                agent_span.set_attribute("gen_ai.system", "langgraph")
                agent_span.set_attribute("gen_ai.operation.name", "invoke_agent")
                agent_span.set_attribute("agent.type", "state_graph")
                
                # Simulate validation
                with create_span("Node: input_validation", "validation"):
                    add_span_attributes(
                        node_name="input_validation",
                        input_length=len(user_input)
                    )
                    time.sleep(0.05)  # Simulate processing
                
                # Simulate context preparation
                with create_span("Node: context_preparation", "preprocessing"):
                    add_span_attributes(
                        node_name="context_preparation",
                        context_prepared=True
                    )
                    time.sleep(0.05)
                
                # Simulate LLM generation WITH TOKEN TIMING
                with create_span("Node: llm_generation", "generation") as gen_span:
                    gen_span.set_attribute("node_name", "llm_generation")
                    
                    # Simulate LLM call with token timing
                    with create_span("LLM Generation with Token Timing", "ai.chat") as llm_span:
                        llm_span.set_attribute("model", "gpt-3.5-turbo")
                        llm_span.set_attribute("streaming", True)
                        llm_span.set_attribute("mock_mode", True)
                        
                        start_time = time.time()
                        
                        # Simulate time to first token (100ms)
                        time.sleep(0.1)
                        first_token_time = time.time()
                        time_to_first_token_ms = int((first_token_time - start_time) * 1000)
                        
                        # Simulate rest of generation (300ms)
                        time.sleep(0.3)
                        last_token_time = time.time()
                        time_to_last_token_ms = int((last_token_time - start_time) * 1000)
                        
                        # Set token timing on LLM span
                        llm_span.set_attribute("time_to_first_token_ms", time_to_first_token_ms)
                        llm_span.set_attribute("time_to_last_token_ms", time_to_last_token_ms)
                        llm_span.set_attribute("gen_ai.usage.total_tokens", 150)
                        llm_span.set_attribute("gen_ai.usage.prompt_tokens", 50)
                        llm_span.set_attribute("gen_ai.usage.completion_tokens", 100)
                        
                        # Generate mock response
                        response_text = f"This is a mock response to: '{user_input}'. The OpenTelemetry instrumentation is working! Check your Sentry dashboard for spans with token timing metrics."
                        
                        # Add response attributes
                        llm_span.set_attribute("response.length", len(response_text))
                
                # Set token timing on agent span (for easy querying)
                agent_span.set_attribute("time_to_first_token_ms", time_to_first_token_ms)
                agent_span.set_attribute("time_to_last_token_ms", time_to_last_token_ms)
                
                # Simulate response processing
                with create_span("Node: response_processing", "postprocessing"):
                    add_span_attributes(
                        node_name="response_processing",
                        response_length=len(response_text)
                    )
                    time.sleep(0.05)
                
                # Simulate conversation update
                with create_span("Node: conversation_update", "state_update"):
                    add_span_attributes(
                        node_name="conversation_update",
                        updated=True
                    )
                    time.sleep(0.05)
            
            # Add token timing to workflow span
            workflow_span.set_attribute("time_to_first_token_ms", time_to_first_token_ms)
            workflow_span.set_attribute("time_to_last_token_ms", time_to_last_token_ms)
            workflow_span.set_attribute("response.length", len(response_text))
            workflow_span.set_attribute("response.word_count", len(response_text.split()))
        
        # Update conversation history
        conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": time.time()
        })
        conversation_history.append({
            "role": "assistant",
            "content": response_text,
            "timestamp": time.time()
        })
        conversation_histories[session_id] = conversation_history
        
        # Add success attributes to endpoint span
        current_span.set_attribute("chat.success", True)
        current_span.set_attribute("chat.response_length", len(response_text))
        current_span.set_attribute("time_to_first_token_ms", time_to_first_token_ms)
        current_span.set_attribute("time_to_last_token_ms", time_to_last_token_ms)
        current_span.set_status(Status(StatusCode.OK))
        
        return JSONResponse({
            'response': response_text,
            'session_id': session_id,
            'conversation_length': len(conversation_history),
            'mock_mode': True,
            'token_timing': {
                'time_to_first_token_ms': time_to_first_token_ms,
                'time_to_last_token_ms': time_to_last_token_ms
            }
        })
    
    except Exception as e:
        # Record exception in span
        current_span.record_exception(e)
        current_span.set_attribute("chat.success", False)
        current_span.set_attribute("error.type", type(e).__name__)
        current_span.set_status(Status(StatusCode.ERROR, str(e)))
        
        import traceback
        print(f"\n❌ ERROR in mock chat endpoint:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        traceback.print_exc()
        
        return JSONResponse({
            'error': str(e),
            'type': type(e).__name__
        }, status_code=500)


async def health(request):
    """Health check endpoint."""
    current_span = trace.get_current_span()
    current_span.set_attribute("health.status", "healthy")
    
    return JSONResponse({
        'status': 'healthy',
        'instrumentation': 'opentelemetry',
        'exporter': 'sentry-otlp',
        'environment': settings.sentry_environment,
        'mode': 'MOCK (No OpenAI API calls)'
    })


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route('/api/chat', chat_endpoint, methods=['POST']),
        Route('/health', health, methods=['GET']),
        Mount('/static', StaticFiles(directory='static'), name='static'),
        Mount('/', StaticFiles(directory='static', html=True), name='root'),
    ],
)

# Instrument Starlette with OpenTelemetry
StarletteInstrumentor.instrument_app(app)


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🔭 MOCK OpenTelemetry-Instrumented Chat (No OpenAI API Required)")
    print("="*80)
    print(f"Environment: {settings.sentry_environment}")
    print("Instrumentation: OpenTelemetry with Sentry OTLP exporter")
    print("Mode: MOCK - Simulates LLM responses with realistic timing")
    print("Server: http://0.0.0.0:8002")
    print("\nThis version simulates:")
    print("  ✓ Complete workflow execution")
    print("  ✓ Token timing metrics (time_to_first_token_ms, time_to_last_token_ms)")
    print("  ✓ All OpenTelemetry spans and attributes")
    print("  ✓ Traces sent to Sentry via OTLP")
    print("\n💡 Use this to test the instrumentation while you fix your OpenAI API key!")
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
        from otel_config import shutdown_opentelemetry
        print("🔄 Shutting down OpenTelemetry...")
        shutdown_opentelemetry()
        print("✅ Shutdown complete")





