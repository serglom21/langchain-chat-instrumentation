# OpenTelemetry Instrumentation with Sentry OTLP

This project demonstrates how to instrument a LangChain + LangGraph application using OpenTelemetry, sending all telemetry data to Sentry via the OTLP (OpenTelemetry Protocol) endpoint.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key"
export SENTRY_DSN="your-sentry-dsn"
export SENTRY_ENVIRONMENT="development"
```

### 3. Run the Application

**Web Server (Port 8002):**
```bash
python otel_web_main.py
```

**CLI Mode:**
```bash
python otel_main.py
```

### 4. Test the API

```bash
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "session_id": "test123"}'
```

## 📊 Architecture

### Sentry OTLP Configuration

**Endpoint**: `https://o88872.ingest.us.sentry.io/api/4509997697073152/integration/otlp/v1/traces`  
**Authentication**: `x-sentry-auth: sentry sentry_key=691b07f94dbbca9171ae9995b25dc778`  
**Protocol**: OTLP over HTTP (JSON)

### Trace Hierarchy

```
POST /api/chat (HTTP server span - Starlette auto-instrumentation)
└── Process Chat Workflow
    └── invoke_agent LangGraph (gen_ai.invoke_agent)
        └── LangGraph Workflow Execution (workflow.execution)
            └── LangGraph Graph Invoke (workflow.langgraph_invoke)
                ├── Node: input_validation (node_operation)
                ├── Node: context_preparation (node_operation)
                ├── Node: llm_generation (node_operation)
                │   ├── LLM Generation with OpenAI GPT-3.5-turbo (ai.chat)
                │   │   ├── LangChain LLM Invoke (ai.chat.invoke)
                │   │   │   ├── LangChain Internal Processing
                │   │   │   │   └── LangChain Invoke Overhead
                │   │   │   │       ├── LLM: gpt-3.5-turbo (callback)
                │   │   │   │       └── http.client — POST OpenAI API
                │   │   │   └── LangGraph Post-HTTP Processing
                │   │   └── Process LLM Response
                ├── Node: response_processing (node_operation)
                └── Node: conversation_update (node_operation)
```

## 🔧 Implementation Details

### 1. OpenTelemetry Setup (`otel_config.py`)

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

def setup_opentelemetry():
    # Create OTLP exporter for Sentry
    otlp_exporter = OTLPSpanExporter(
        endpoint="https://o88872.ingest.us.sentry.io/api/.../otlp/v1/traces",
        headers={
            "x-sentry-auth": "sentry sentry_key=...",
            "Content-Type": "application/json",
        },
    )
    
    # Set up tracer provider
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)
    
    # Instrument HTTP clients for OpenAI API calls
    RequestsInstrumentor().instrument()
    HTTPXInstrumentor().instrument()
    
    return trace.get_tracer("langchain_chat_instrumentation", "1.0.0")
```

### 2. Custom Instrumentation Helpers (`otel_instrumentation.py`)

**Decorator for Node Instrumentation:**
```python
def instrument_node(node_name: str, operation_type: str = "processing"):
    def decorator(func):
        @wraps(func)
        def wrapper(self, state):
            tracer = get_tracer()
            with tracer.start_as_current_span(
                name=f"Node: {node_name}",
                kind=trace.SpanKind.INTERNAL,
            ) as span:
                span.set_attribute("node.name", node_name)
                span.set_attribute("node.operation_type", operation_type)
                
                try:
                    result = func(self, state)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator
```

**Context Manager for Custom Spans:**
```python
@contextmanager
def create_span(name: str, operation: str, kind=trace.SpanKind.INTERNAL):
    tracer = get_tracer()
    with tracer.start_as_current_span(name=name, kind=kind) as span:
        span.set_attribute("operation", operation)
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

**Helper Functions:**
```python
def add_span_attributes(**kwargs):
    """Add attributes to the current active span."""
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in kwargs.items():
            span.set_attribute(key, value)

def record_exception(exception: Exception):
    """Record an exception in the current span."""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))
```

### 3. LangChain Callback (`otel_chat_nodes.py`)

```python
class OpenTelemetryLangChainCallback(BaseCallbackHandler):
    """OpenTelemetry callback for LangChain instrumentation."""
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        run_id = self._get_run_id(**kwargs)
        span = self.tracer.start_span(
            name=f"LLM: {serialized.get('name', 'unknown')}",
            kind=trace.SpanKind.CLIENT,
        )
        
        # Set AI semantic conventions
        span.set_attribute("gen_ai.system", "openai")
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.request.model", model_name)
        span.set_attribute("gen_ai.prompt.count", len(prompts))
        
        self.spans[run_id] = span
    
    def on_llm_end(self, response, **kwargs):
        run_id = self._get_run_id(**kwargs)
        if run_id in self.spans:
            span = self.spans[run_id]
            
            # Add token usage
            span.set_attribute("gen_ai.usage.total_tokens", total_tokens)
            span.set_attribute("gen_ai.response.time_to_first_token_ms", time_ms)
            
            span.set_status(Status(StatusCode.OK))
            span.end()
```

### 4. Node Implementation (`otel_chat_nodes.py`)

```python
class OtelChatNodes:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(openai_api_key=openai_api_key, model="gpt-3.5-turbo")
        self.otel_callback = OpenTelemetryLangChainCallback()
    
    @instrument_node("input_validation", "validation")
    def input_validation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_input = state.get("user_input", "")
        
        if not user_input.strip():
            raise ValueError("User input cannot be empty")
        
        add_span_attributes(
            input_length=len(user_input),
            word_count=len(user_input.split())
        )
        
        return {**state, "validated_input": user_input.strip()}
    
    @instrument_node("llm_generation", "generation")
    def llm_generation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages", [])
        
        with create_span("LLM Generation with OpenAI", "ai.chat") as ai_span:
            ai_span.set_attribute("gen_ai.system", "openai")
            ai_span.set_attribute("gen_ai.request.model", "gpt-3.5-turbo")
            
            response = self.llm.invoke(
                messages,
                config={"callbacks": [self.otel_callback]}
            )
        
        return {**state, "generated_response": response.content}
```

### 5. State Graph (`otel_state_graph.py`)

```python
class OtelChatStateGraph:
    def process_chat(self, user_input: str, conversation_history=None):
        initial_state = {
            "user_input": user_input,
            "conversation_history": conversation_history or [],
        }
        
        # LangGraph agent span (matches Sentry SDK)
        with create_span("invoke_agent LangGraph", "gen_ai.invoke_agent") as agent_span:
            agent_span.set_attribute("gen_ai.system", "langgraph")
            agent_span.set_attribute("gen_ai.operation.name", "invoke_agent")
            
            # Workflow execution
            with create_span("LangGraph Workflow Execution", "workflow.execution") as workflow_span:
                workflow_span.set_attribute("user_input_length", len(user_input))
                
                # Graph invoke
                with create_span("LangGraph Graph Invoke", "workflow.langgraph_invoke") as graph_span:
                    result = self.graph.invoke(initial_state)
        
        return result
```

### 6. Web Server (`otel_web_main.py`)

```python
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

# Initialize OpenTelemetry
setup_opentelemetry()

# Instrument Starlette (creates HTTP server spans automatically)
StarletteInstrumentor().instrument()

# Create app
app = Starlette(routes=[...])

async def chat_endpoint(request):
    tracer = get_tracer()
    current_span = trace.get_current_span()  # HTTP server span from Starlette
    
    data = await request.json()
    user_input = data.get('message', '')
    
    # Add attributes to HTTP span
    current_span.set_attribute("chat.input_length", len(user_input))
    
    # Process chat (creates child spans)
    result = chat_graph.process_chat(user_input)
    
    return JSONResponse({'response': result['processed_response']})
```

## 📋 Key Features

### Automatic Instrumentation
- ✅ **HTTP Server** - Starlette auto-instrumentation creates root spans
- ✅ **HTTP Client** - Requests/HTTPX instrumentation captures OpenAI API calls
- ✅ **Context Propagation** - Spans automatically inherit parent context

### Custom Instrumentation
- ✅ **Node Operations** - Each StateGraph node creates a span
- ✅ **Workflow Execution** - LangGraph workflow wrapped in spans
- ✅ **LLM Calls** - Detailed AI/LLM spans with token timing
- ✅ **Error Tracking** - Exceptions recorded in spans

### OpenTelemetry Semantic Conventions
```python
# AI/LLM attributes
gen_ai.system = "openai"
gen_ai.operation.name = "chat"
gen_ai.request.model = "gpt-3.5-turbo"
gen_ai.usage.prompt_tokens = 150
gen_ai.usage.completion_tokens = 75
gen_ai.usage.total_tokens = 225

# Custom attributes
node.name = "input_validation"
node.operation_type = "validation"
workflow.type = "chat"
chat.input_length = 42
```

## 🧪 Testing

### Run Test Suite

```bash
python test_otel.py
```

**Tests Include:**
- Basic span creation
- Nested span hierarchy
- Custom instrumentation helpers
- Error handling
- Full chat workflow

### Expected Output

```
✅ OpenTelemetry initialized with Sentry OTLP exporter
✅ Instrumented requests library for HTTP client spans
✅ Instrumented httpx library for HTTP client spans

Test 1: Basic Span Creation
✅ Created span with attributes
✅ Span completed

Test 2: Nested Spans
✅ Created parent span
  ✅ Created child span 1
  ✅ Created child span 2
✅ All spans completed

✅ All Tests Completed Successfully!
✅ Traces flushed to Sentry via OTLP!
```

## 📊 Viewing Traces in Sentry

1. Go to your Sentry dashboard
2. Navigate to **Performance** → **Traces**
3. Filter by: `resource.service.name:"langchain-chat-instrumentation"`
4. Click on a trace to see the full span hierarchy

**Expected Trace Structure:**
- Total Spans: 18+
- Root Span: `POST /api/chat` (HTTP server)
- Duration: ~400-1000ms (depending on LLM response time)
- All spans connected in proper parent-child relationships

## 🔍 Troubleshooting

### Spans Not Appearing in Sentry

**Problem**: No traces in Sentry dashboard

**Solutions**:
1. Check OTLP endpoint is correct in `otel_config.py`
2. Verify authentication header is set
3. Ensure `shutdown_opentelemetry()` is called to flush spans
4. Check console for errors during initialization

### Disconnected Spans

**Problem**: Spans appear but not connected in hierarchy

**Solutions**:
1. Ensure HTTP server instrumentation is applied before app creation
2. Verify spans are created within active span context
3. Check that `trace.get_current_span()` returns a recording span

### Missing HTTP Client Spans

**Problem**: No `http.client` spans for OpenAI API calls

**Solutions**:
1. Install instrumentation packages:
   ```bash
   pip install opentelemetry-instrumentation-requests opentelemetry-instrumentation-httpx
   ```
2. Verify instrumentation is called in `setup_opentelemetry()`
3. Check that OpenAI library uses `requests` or `httpx`

## 🎯 Best Practices

### 1. Span Hierarchy
Create logical layers:
- HTTP request (root)
- Workflow/Agent (business logic)
- Nodes (operations)
- LLM calls (external services)

### 2. Semantic Conventions
Follow OpenTelemetry standards:
- Use `gen_ai.*` for AI/LLM operations
- Use `http.*` for HTTP operations
- Use descriptive span names

### 3. Attributes
Add meaningful context:
- Input/output lengths
- Model names
- Token counts
- Business identifiers (session_id, user_id)

### 4. Error Handling
Always record exceptions:
```python
try:
    risky_operation()
except Exception as e:
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, str(e)))
    raise
```

### 5. Cleanup
Flush spans on shutdown:
```python
from otel_config import shutdown_opentelemetry

try:
    app.run()
finally:
    shutdown_opentelemetry()
```

## 📦 Dependencies

```txt
# OpenTelemetry Core
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp-proto-http>=1.20.0

# OpenTelemetry Instrumentation
opentelemetry-instrumentation>=0.41b0
opentelemetry-instrumentation-flask>=0.41b0
opentelemetry-instrumentation-starlette>=0.41b0
opentelemetry-instrumentation-requests>=0.41b0
opentelemetry-instrumentation-httpx>=0.41b0

# Semantic Conventions
opentelemetry-semantic-conventions>=0.41b0
```

## 🚀 Production Deployment

### Environment Variables

```bash
export OPENAI_API_KEY="your-production-key"
export SENTRY_DSN="your-production-dsn"
export SENTRY_ENVIRONMENT="production"
```

### Sampling

For high-traffic applications, configure sampling:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
provider = TracerProvider(resource=resource, sampler=sampler)
```

### Performance

- **Overhead**: ~5-10ms per request
- **Memory**: ~10MB base + ~1KB per span
- **Network**: Batched exports every few seconds

## 📚 Resources

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Sentry OTLP Integration](https://docs.sentry.io/concepts/otlp/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)

## 🎉 Summary

This implementation provides:
- ✅ **Vendor-neutral** observability with OpenTelemetry
- ✅ **Complete trace hierarchy** with 18+ connected spans
- ✅ **AI/LLM monitoring** with semantic conventions
- ✅ **Sentry integration** via OTLP protocol
- ✅ **Production-ready** with proper error handling and cleanup

The OpenTelemetry implementation achieves **feature parity** with Sentry SDK while maintaining vendor flexibility and following industry standards.

