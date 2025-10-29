"""
Flask web application with OpenTelemetry instrumentation.

This provides a web interface for the chat application using OpenTelemetry
instead of the Sentry SDK.
"""
from flask import Flask, request, jsonify, send_from_directory
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.trace import Status, StatusCode

from config import get_settings
from otel_config import setup_opentelemetry, get_tracer
from otel_state_graph import OtelChatStateGraph
from otel_instrumentation import add_span_attributes, record_exception


# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Initialize OpenTelemetry
setup_opentelemetry()

# Instrument Flask with OpenTelemetry
FlaskInstrumentor().instrument_app(app)

# Initialize settings and chat graph
settings = get_settings()
chat_graph = OtelChatStateGraph(settings.openai_api_key)

# Store conversation histories (in production, use a database)
conversation_histories = {}


@app.route('/')
def index():
    """Serve the chat UI."""
    return send_from_directory('static', 'chat.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat requests with OpenTelemetry instrumentation.
    
    Flask instrumentation automatically creates a span for this endpoint.
    We add custom attributes and child spans for detailed observability.
    """
    tracer = get_tracer()
    current_span = trace.get_current_span()
    
    try:
        # Parse request
        data = request.get_json()
        user_input = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        if not user_input:
            current_span.set_attribute("error", "empty_input")
            return jsonify({'error': 'Message is required'}), 400
        
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
        
        return jsonify({
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
        
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500


@app.route('/api/history/<session_id>', methods=['GET'])
def get_history(session_id: str):
    """Get conversation history for a session."""
    current_span = trace.get_current_span()
    current_span.set_attribute("chat.session_id", session_id)
    
    history = conversation_histories.get(session_id, [])
    current_span.set_attribute("chat.history_length", len(history))
    
    return jsonify({
        'session_id': session_id,
        'history': history,
        'length': len(history)
    })


@app.route('/api/clear/<session_id>', methods=['POST'])
def clear_history(session_id: str):
    """Clear conversation history for a session."""
    current_span = trace.get_current_span()
    current_span.set_attribute("chat.session_id", session_id)
    
    if session_id in conversation_histories:
        del conversation_histories[session_id]
        current_span.set_attribute("chat.history_cleared", True)
    else:
        current_span.set_attribute("chat.history_cleared", False)
    
    return jsonify({
        'session_id': session_id,
        'cleared': True
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    current_span = trace.get_current_span()
    current_span.set_attribute("health.status", "healthy")
    
    return jsonify({
        'status': 'healthy',
        'instrumentation': 'opentelemetry',
        'exporter': 'sentry-otlp'
    })


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🔭 OpenTelemetry-Instrumented Chat Web Application")
    print("="*80)
    print(f"Environment: {settings.sentry_environment}")
    print("Instrumentation: OpenTelemetry with Sentry OTLP exporter")
    print("Server: http://localhost:5000")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)


