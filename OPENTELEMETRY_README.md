# 🔭 OpenTelemetry Implementation with Sentry OTLP

This document explains the OpenTelemetry implementation that sends telemetry data to Sentry via the OTLP (OpenTelemetry Protocol) endpoint.

## 📋 Overview

This project now includes **two instrumentation approaches**:

1. **Sentry SDK** (original) - Direct Sentry instrumentation
2. **OpenTelemetry + OTLP** (new) - Vendor-neutral instrumentation sending to Sentry

Both approaches provide the same level of detailed instrumentation for LangChain + LangGraph workflows.

## 🏗️ Architecture

### OpenTelemetry Files

```
otel_config.py              # OpenTelemetry setup with Sentry OTLP exporter
otel_instrumentation.py     # Custom instrumentation helpers (decorators, spans, attributes)
otel_chat_nodes.py          # Chat nodes with OpenTelemetry instrumentation
otel_state_graph.py         # StateGraph with OpenTelemetry instrumentation
otel_main.py                # CLI application with OpenTelemetry
otel_web_main.py            # Web server (Starlette) with OpenTelemetry
otel_web_app.py             # Web server (Flask) with OpenTelemetry
```

### Sentry OTLP Configuration

The OpenTelemetry data is sent to Sentry using:

- **Endpoint**: `https://o88872.ingest.us.sentry.io/api/4509997697073152/integration/otlp/v1/traces`
- **Authentication**: `x-sentry-auth: sentry sentry_key=691b07f94dbbca9171ae9995b25dc778`
- **Protocol**: OTLP over HTTP (JSON)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- OpenTelemetry API and SDK
- OTLP HTTP exporter
- Flask and Starlette instrumentation
- Semantic conventions

### 2. Set Environment Variables

```bash
cp .env.template .env
# Edit .env with your keys
```

Required:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SENTRY_DSN` - Your Sentry DSN (optional, used for environment tagging)
- `SENTRY_ENVIRONMENT` - Environment name (e.g., "development", "production")

### 3. Run the Application

**CLI Mode:**
```bash
python otel_main.py
```

**Web Server (Starlette - Port 8002):**
```bash
python otel_web_main.py
```

**Web Server (Flask - Port 5000):**
```bash
python otel_web_app.py
```

## 📊 What Gets Instrumented

### Automatic Instrumentation

OpenTelemetry automatically instruments:
- ✅ HTTP requests (Flask/Starlette endpoints)
- ✅ HTTP client calls (to OpenAI API)
- ✅ Framework middleware

### Custom Instrumentation

We add custom spans for:
- ✅ **Workflow execution** - Overall LangGraph workflow
- ✅ **Node operations** - Each StateGraph node (validation, context prep, LLM, etc.)
- ✅ **LLM calls** - Detailed AI/LLM spans with semantic conventions
- ✅ **Token timing** - Time to first token, time to last token
- ✅ **Framework overhead** - LangChain/LangGraph internal processing
- ✅ **Cache operations** - Cache hits/misses

### Span Hierarchy Example

```
POST /api/chat (Starlette auto-instrumentation)
├── Process Chat Workflow
│   ├── LangGraph Workflow Execution
│   │   ├── LangGraph Graph Invoke
│   │   │   ├── Node: input_validation
│   │   │   │   └── Attributes: input_length, word_count
│   │   │   ├── Node: context_preparation
│   │   │   │   └── Attributes: context_messages_count, history_length
│   │   │   ├── Node: llm_generation
│   │   │   │   ├── LLM Generation with OpenAI GPT-3.5-turbo
│   │   │   │   │   ├── LangChain LLM Invoke
│   │   │   │   │   │   ├── LangChain Message Preprocessing
│   │   │   │   │   │   ├── Streaming LangChain Generate Call
│   │   │   │   │   │   │   ├── LangChain Internal Processing
│   │   │   │   │   │   │   │   └── LangChain Invoke Overhead
│   │   │   │   │   │   │   │       └── HTTP POST (OpenAI API)
│   │   │   │   │   │   │   │       └── LangGraph Post-HTTP Processing
│   │   │   │   │   │   │   └── Process LLM Response
│   │   │   │   │   └── LangGraph Internal Processing
│   │   │   ├── Node: response_processing
│   │   │   └── Node: conversation_update
```

## 🔍 OpenTelemetry Semantic Conventions

We follow OpenTelemetry semantic conventions for AI/LLM operations:

### AI Attributes

```python
gen_ai.system = "openai"
gen_ai.operation.name = "chat"
gen_ai.request.model = "gpt-3.5-turbo"
gen_ai.usage.prompt_tokens = 150
gen_ai.usage.completion_tokens = 75
gen_ai.usage.total_tokens = 225
gen_ai.response.time_to_first_token_ms = 100
```

### Custom Attributes

```python
# Node-level
node.name = "input_validation"
node.operation_type = "validation"
workflow.step = "input_validation"

# Workflow-level
workflow.type = "chat"
workflow.session_id = "abc123"
workflow.duration_ms = 1247

# Chat-specific
chat.session_id = "abc123"
chat.input_length = 42
chat.history_length = 5
chat.response_length = 150
```

## 🆚 Comparison: Sentry SDK vs OpenTelemetry

| Aspect | Sentry SDK | OpenTelemetry + OTLP |
|--------|------------|----------------------|
| **Vendor Lock-in** | Sentry-specific | Vendor-neutral |
| **Instrumentation** | Direct SDK calls | Standard OTel API |
| **Portability** | Sentry only | Any OTel backend |
| **Auto-instrumentation** | Sentry integrations | OTel instrumentations |
| **Semantic Conventions** | Sentry-specific | OpenTelemetry standard |
| **Migration Path** | Locked to Sentry | Easy to switch backends |
| **Feature Parity** | ✅ Full Sentry features | ✅ Same visibility |

### When to Use Each

**Use Sentry SDK when:**
- You're committed to Sentry long-term
- You want Sentry-specific features (Releases, User Feedback, etc.)
- You prefer simpler setup

**Use OpenTelemetry when:**
- You want vendor flexibility
- You follow cloud-native standards
- You might switch observability backends
- You want to send to multiple backends simultaneously

## 🔧 Key Implementation Details

### 1. Tracer Setup (`otel_config.py`)

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Create OTLP exporter for Sentry
otlp_exporter = OTLPSpanExporter(
    endpoint="https://o88872.ingest.us.sentry.io/api/.../integration/otlp/v1/traces",
    headers={
        "x-sentry-auth": "sentry sentry_key=...",
        "Content-Type": "application/json",
    },
)

# Set up tracer provider
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)
```

### 2. Custom Span Decorator (`otel_instrumentation.py`)

```python
def instrument_node(node_name: str, operation_type: str = "processing"):
    """Decorator to instrument node methods with OpenTelemetry spans."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, state: Dict[str, Any]) -> Dict[str, Any]:
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

### 3. LangChain Callback (`otel_chat_nodes.py`)

```python
class OpenTelemetryLangChainCallback(BaseCallbackHandler):
    """OpenTelemetry callback for LangChain instrumentation."""
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Create span when LLM starts."""
        span = self.tracer.start_span(
            name=f"LLM: {serialized.get('name', 'unknown')}",
            kind=trace.SpanKind.CLIENT,
        )
        set_ai_attributes(span, model=model_name, prompts=prompts)
        self.spans[run_id] = span
    
    def on_llm_end(self, response, **kwargs):
        """Finalize span when LLM completes."""
        span = self.spans[run_id]
        span.set_attribute("gen_ai.usage.total_tokens", total_tokens)
        span.set_status(Status(StatusCode.OK))
        span.end()
```

## 📈 Viewing Data in Sentry

After running the application, view traces in Sentry:

1. Go to **Performance** → **Traces**
2. Filter by:
   - Service: `langchain-chat-instrumentation`
   - Environment: Your configured environment
3. Click on a trace to see the full span hierarchy
4. View custom attributes in span details

### Key Metrics to Monitor

- **Time to First Token** - User experience metric
- **Node Duration** - Identify bottlenecks
- **Cache Hit Rate** - Optimization opportunities
- **Framework Overhead** - LangChain/LangGraph processing time
- **Total Request Duration** - End-to-end performance

## 🧪 Testing

### Test CLI Application

```bash
python otel_main.py "What is the capital of France?"
```

### Test Web Application

```bash
# Start server
python otel_web_main.py

# In another terminal, test the API
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "session_id": "test123"}'
```

### Verify in Sentry

1. Check Sentry dashboard within 30 seconds
2. Look for traces with service name `langchain-chat-instrumentation`
3. Verify span hierarchy matches expected structure
4. Check that custom attributes are present

## 🔄 Migration from Sentry SDK

To migrate existing code from Sentry SDK to OpenTelemetry:

| Sentry SDK | OpenTelemetry |
|------------|---------------|
| `sentry_sdk.init()` | `setup_opentelemetry()` |
| `sentry_sdk.start_transaction()` | `tracer.start_as_current_span()` |
| `sentry_sdk.start_span()` | `tracer.start_as_current_span()` |
| `span.set_tag()` | `span.set_attribute()` |
| `span.set_data()` | `span.set_attribute()` |
| `sentry_sdk.capture_exception()` | `span.record_exception()` |
| `sentry_sdk.set_measurement()` | `span.set_attribute()` |

## 📚 Additional Resources

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Sentry OTLP Integration](https://docs.sentry.io/concepts/otlp/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [OpenTelemetry API Reference](https://opentelemetry-python.readthedocs.io/)

## 🐛 Troubleshooting

### Spans Not Appearing in Sentry

1. Check that the OTLP endpoint is correct
2. Verify authentication header is set
3. Ensure `shutdown_opentelemetry()` is called to flush spans
4. Check for network connectivity issues

### Missing Custom Attributes

1. Verify span is recording: `span.is_recording()`
2. Check attribute value types (must be str, bool, int, float, or sequences)
3. Ensure attributes are set before span ends

### Performance Issues

1. Reduce sampling rate if needed
2. Use `BatchSpanProcessor` for better performance
3. Limit attribute value sizes (especially for prompts/responses)

## 🎯 Best Practices

1. **Always call `shutdown_opentelemetry()`** at application exit to flush spans
2. **Use semantic conventions** for AI/LLM attributes
3. **Set span status** explicitly (OK or ERROR)
4. **Record exceptions** in spans for better error tracking
5. **Limit attribute sizes** to avoid payload issues
6. **Use span events** for large data (prompts, responses)
7. **Add context** with meaningful span names and attributes

## 🚀 Next Steps

- [ ] Add metrics collection (OpenTelemetry Metrics)
- [ ] Add logging integration (OpenTelemetry Logs)
- [ ] Implement distributed tracing across services
- [ ] Add custom metrics for business KPIs
- [ ] Set up alerting based on trace data
- [ ] Implement sampling strategies for production


