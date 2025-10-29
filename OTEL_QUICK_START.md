# 🚀 OpenTelemetry Quick Start Guide

Get up and running with OpenTelemetry instrumentation in 5 minutes!

## ⚡ Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs OpenTelemetry packages:
- `opentelemetry-api` - Core API
- `opentelemetry-sdk` - SDK implementation
- `opentelemetry-exporter-otlp-proto-http` - Sentry OTLP exporter
- `opentelemetry-instrumentation-flask` - Flask auto-instrumentation
- `opentelemetry-instrumentation-starlette` - Starlette auto-instrumentation

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key"
export SENTRY_DSN="your-sentry-dsn"
export SENTRY_ENVIRONMENT="development"
```

Or create a `.env` file:
```bash
cp .env.template .env
# Edit .env with your keys
```

### 3. Run the Application

**CLI Mode:**
```bash
python otel_main.py
```

**Web Server Mode:**
```bash
python otel_web_main.py
# Server runs on http://localhost:8002
```

**Or use the startup script:**
```bash
./start_otel_chat.sh
```

### 4. Test the API

```bash
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "session_id": "test123"}'
```

### 5. View Traces in Sentry

1. Go to your Sentry dashboard
2. Navigate to **Performance** → **Traces**
3. Filter by service: `langchain-chat-instrumentation`
4. Click on a trace to see the full span hierarchy

## 🎯 What You'll See

### Span Hierarchy

```
POST /api/chat
├── Process Chat Workflow
│   ├── LangGraph Workflow Execution
│   │   ├── LangGraph Graph Invoke
│   │   │   ├── Node: input_validation (1ms)
│   │   │   ├── Node: context_preparation (2ms)
│   │   │   ├── Node: llm_generation (800ms)
│   │   │   │   ├── LLM Generation with OpenAI
│   │   │   │   │   ├── LangChain LLM Invoke
│   │   │   │   │   │   ├── LangChain Internal Processing
│   │   │   │   │   │   │   └── LangChain Invoke Overhead
│   │   │   │   │   │   │       └── HTTP POST (OpenAI API)
│   │   │   │   │   │   └── Process LLM Response
│   │   │   ├── Node: response_processing (1ms)
│   │   │   └── Node: conversation_update (1ms)
```

### Custom Attributes

- `gen_ai.system` = "openai"
- `gen_ai.request.model` = "gpt-3.5-turbo"
- `gen_ai.usage.total_tokens` = 225
- `time_to_first_token_ms` = 100
- `node.name` = "input_validation"
- `workflow.type` = "chat"

## 🧪 Run Tests

```bash
python test_otel.py
```

This will:
- ✅ Test basic span creation
- ✅ Test nested spans
- ✅ Test custom instrumentation helpers
- ✅ Test error handling
- ✅ Test full chat workflow
- ✅ Send all traces to Sentry

## 🔍 Compare with Sentry SDK

Run both implementations side-by-side:

```bash
# Terminal 1: Sentry SDK
python web_main.py  # Port 8000

# Terminal 2: OpenTelemetry
python otel_web_main.py  # Port 8002

# Terminal 3: Baseline
python baseline_web_main.py  # Port 8001
```

Then compare traces in Sentry dashboard!

## 📊 Key Differences from Sentry SDK

### Code Changes

**Sentry SDK:**
```python
import sentry_sdk

sentry_sdk.init(dsn=..., integrations=[...])

with sentry_sdk.start_transaction(...) as transaction:
    with sentry_sdk.start_span(...) as span:
        span.set_tag("key", "value")
```

**OpenTelemetry:**
```python
from opentelemetry import trace
from otel_config import setup_opentelemetry, get_tracer

setup_opentelemetry()
tracer = get_tracer()

with tracer.start_as_current_span(...) as span:
    span.set_attribute("key", "value")
```

### Benefits

✅ **Vendor Flexibility** - Not locked into Sentry
✅ **Industry Standard** - CNCF project
✅ **Portable Traces** - Works with any OTLP backend
✅ **Multi-Backend** - Send to multiple destinations

## 🎓 Next Steps

1. **Read the full guide**: [OPENTELEMETRY_README.md](OPENTELEMETRY_README.md)
2. **Compare approaches**: [OTEL_VS_SENTRY_COMPARISON.md](OTEL_VS_SENTRY_COMPARISON.md)
3. **Customize instrumentation**: Add your own spans and attributes
4. **Explore Sentry**: Check out the AI Agent dashboard

## 💡 Common Tasks

### Add a Custom Span

```python
from otel_instrumentation import create_span

with create_span("My Custom Operation", "custom.operation") as span:
    span.set_attribute("custom.key", "custom_value")
    # Your code here
```

### Add Custom Attributes

```python
from otel_instrumentation import add_span_attributes

add_span_attributes(
    user_id=user_id,
    request_type="chat",
    input_length=len(user_input)
)
```

### Record an Exception

```python
from otel_instrumentation import record_exception

try:
    risky_operation()
except Exception as e:
    record_exception(e, {"operation": "risky_operation"})
    raise
```

### Track Timing Metrics

```python
from otel_instrumentation import track_timing_metric

track_timing_metric("custom_operation_time", 123.45)
```

## 🐛 Troubleshooting

### Spans Not Showing Up

**Problem:** No traces in Sentry
**Solution:** 
1. Check OTLP endpoint is correct in `otel_config.py`
2. Verify authentication header
3. Ensure `shutdown_opentelemetry()` is called
4. Check console for errors

### Missing Attributes

**Problem:** Custom attributes not appearing
**Solution:**
1. Verify span is recording: `span.is_recording()`
2. Check attribute types (must be str, bool, int, float)
3. Set attributes before span ends

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'opentelemetry'`
**Solution:**
```bash
pip install -r requirements.txt
```

## 📚 Documentation

- **[OPENTELEMETRY_README.md](OPENTELEMETRY_README.md)** - Complete guide
- **[OTEL_VS_SENTRY_COMPARISON.md](OTEL_VS_SENTRY_COMPARISON.md)** - Detailed comparison
- **[OPENTELEMETRY_MIGRATION_SUMMARY.md](OPENTELEMETRY_MIGRATION_SUMMARY.md)** - Migration summary
- **[README.md](README.md)** - Main project documentation

## 🎉 You're Ready!

You now have OpenTelemetry instrumentation running and sending data to Sentry via OTLP!

**What's Next?**
- Explore the traces in Sentry
- Compare with Sentry SDK implementation
- Add your own custom instrumentation
- Deploy to production with confidence

---

**Need Help?** Check the [OPENTELEMETRY_README.md](OPENTELEMETRY_README.md) for detailed documentation.


