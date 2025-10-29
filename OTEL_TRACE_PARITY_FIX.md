# 🔧 OpenTelemetry Trace Parity Fix

## 🔍 Problem Analysis

Comparing the Sentry SDK trace with OpenTelemetry traces, we found **disconnected spans** instead of a unified trace hierarchy.

### Sentry SDK Trace Structure (Target)
```
http.server — /chat (958ms)
└── Autogrouped — middleware.starlette (957ms)
    └── workflow.execution — LangGraph Workflow Execution (952ms)
        └── workflow.langgraph_invoke — LangGraph Graph Invoke (952ms)
            └── gen_ai.invoke_agent — invoke_agent LangGraph (952ms)
                ├── node_operation — Node: input_validation (0.03ms)
                ├── node_operation — Node: context_preparation (0.08ms)
                ├── node_operation — Node: llm_generation (900ms)
                │   ├── ai.chat — LLM Generation with OpenAI GPT-3.5-turbo (900ms)
                │   │   ├── ai.chat.invoke — LangChain LLM Invoke (900ms)
                │   │   │   ├── ai.chat.preprocess — LangChain Message Preprocessing (0.01ms)
                │   │   │   ├── ai.chat.generate — Streaming LangChain Generate Call (900ms)
                │   │   │   │   ├── ai.chat.internal_processing — LangChain Internal Processing (900ms)
                │   │   │   │   │   ├── ai.chat.invoke_overhead — LangChain Invoke Overhead (900ms)
                │   │   │   │   │   │   ├── gen_ai.chat — chat gpt-3.5-turbo (899ms)
                │   │   │   │   │   │   │   └── http.client — POST OpenAI API (513ms)
                │   │   │   │   │   │   └── ai.chat.post_http_processing — LangGraph Post-HTTP (0.04ms)
                │   │   │   │   └── ai.chat.langgraph_processing — LangGraph Internal (0.48ms)
                │   │   └── ai.chat.process_response — Process LLM Response (0.17ms)
                ├── node_operation — Node: response_processing (0.05ms)
                └── node_operation — Node: conversation_update (0.03ms)
```

### OpenTelemetry Current State (Problem)
```
❌ Disconnected spans:
- Node: input_validation (isolated)
- Node: context_preparation (isolated)
- parent_span (test trace)
```

## 🎯 Root Causes

### 1. Missing HTTP Server Root Span
**Issue**: Starlette instrumentation is applied but not creating proper root spans.

**Why**: The instrumentation needs to be applied BEFORE the app routes are defined, and we need to ensure the server span is the root.

### 2. Missing LangGraph Auto-Instrumentation
**Issue**: Sentry SDK has `gen_ai.invoke_agent` span from LangGraph integration, but OpenTelemetry doesn't.

**Why**: There's no official OpenTelemetry instrumentation for LangGraph yet. Sentry's integration is proprietary.

### 3. Missing LangChain Auto-Instrumentation
**Issue**: Sentry SDK has automatic `gen_ai.chat` spans, but OpenTelemetry doesn't.

**Why**: We're not using OpenTelemetry's LangChain instrumentation (if it exists), or we need to add it manually.

### 4. Context Not Propagating
**Issue**: Spans are created but not connected to parent context.

**Why**: The workflow execution might not be happening within the HTTP request span context.

## ✅ Solutions

### Solution 1: Fix HTTP Server Instrumentation

**File**: `otel_web_main.py`

**Problem**: Starlette instrumentation is applied after app creation.

**Fix**:
```python
# BEFORE (Wrong order)
app = Starlette(routes=[...])
StarletteInstrumentor.instrument_app(app)

# AFTER (Correct order)
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

# Instrument BEFORE creating app
StarletteInstrumentor().instrument()

# Then create app
app = Starlette(routes=[...])
```

### Solution 2: Add HTTP Client Instrumentation for OpenAI

**Missing**: Automatic `http.client` spans for OpenAI API calls.

**Fix**: Add `requests` or `httpx` instrumentation:

```python
# In otel_config.py
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXInstrumentor

def setup_opentelemetry():
    # ... existing code ...
    
    # Add HTTP client instrumentation
    RequestsInstrumentor().instrument()
    HTTPXInstrumentor().instrument()
```

### Solution 3: Add Manual LangGraph Span

**Missing**: `gen_ai.invoke_agent` span that wraps the entire graph execution.

**Fix**: Update `otel_state_graph.py`:

```python
def process_chat(self, user_input: str, conversation_history: List[Dict[str, Any]] = None):
    """Process a chat message through the StateGraph workflow."""
    try:
        initial_state = {
            "user_input": user_input,
            "conversation_history": conversation_history or [],
            "error": None
        }
        
        # Add LangGraph agent span (matches Sentry SDK)
        with create_span(
            "invoke_agent LangGraph",
            "gen_ai.invoke_agent",
            kind=trace.SpanKind.INTERNAL
        ) as agent_span:
            agent_span.set_attribute("gen_ai.system", "langgraph")
            agent_span.set_attribute("gen_ai.operation.name", "invoke_agent")
            
            # Existing workflow execution span
            with create_span(
                "LangGraph Workflow Execution",
                "workflow.execution",
                kind=trace.SpanKind.INTERNAL
            ) as workflow_span:
                # ... rest of the code
```

### Solution 4: Add LangChain Callback Integration

**Missing**: Automatic `gen_ai.chat` spans from LangChain.

**Current**: We have `OpenTelemetryLangChainCallback` but it creates spans manually.

**Enhancement**: Ensure the callback spans are created with proper operation names:

```python
# In otel_chat_nodes.py - OpenTelemetryLangChainCallback

def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs):
    """Called when LLM starts."""
    run_id = self._get_run_id(**kwargs)
    start_time = time.time()
    
    # Create span with EXACT operation name from Sentry SDK
    span = self.tracer.start_span(
        name=f"chat {serialized.get('name', 'unknown')}",  # "chat gpt-3.5-turbo"
        kind=trace.SpanKind.CLIENT,
    )
    
    # Use gen_ai.chat operation (matches Sentry)
    span.set_attribute("span.op", "gen_ai.chat")
    span.set_attribute("gen_ai.system", "openai")
    span.set_attribute("gen_ai.operation.name", "chat")
    # ... rest of the attributes
```

### Solution 5: Ensure Context Propagation

**Issue**: Spans might not be inheriting the HTTP request context.

**Fix**: Verify the tracer is using the current context:

```python
# In otel_web_main.py - chat_endpoint

async def chat_endpoint(request):
    tracer = get_tracer()
    
    # Get current span (should be the HTTP server span from Starlette)
    current_span = trace.get_current_span()
    
    # Verify we have a valid span context
    if not current_span.is_recording():
        print("WARNING: No active span context!")
    
    # All child spans will now inherit this context
    result = chat_graph.process_chat(user_input, conversation_history)
```

## 📝 Complete Implementation

### Step 1: Update `otel_config.py`

Add HTTP client instrumentation:

```python
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXInstrumentor

def setup_opentelemetry() -> trace.Tracer:
    """Initialize OpenTelemetry with Sentry OTLP exporter."""
    global _tracer
    
    if _tracer is not None:
        return _tracer
    
    # ... existing setup code ...
    
    # Add HTTP client instrumentation for OpenAI API calls
    try:
        RequestsInstrumentor().instrument()
    except Exception as e:
        print(f"Warning: Could not instrument requests: {e}")
    
    try:
        HTTPXInstrumentor().instrument()
    except Exception as e:
        print(f"Warning: Could not instrument httpx: {e}")
    
    _tracer = trace.get_tracer(...)
    return _tracer
```

### Step 2: Update `otel_web_main.py`

Fix Starlette instrumentation order:

```python
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

# Initialize OpenTelemetry FIRST
setup_opentelemetry()

# Instrument Starlette BEFORE creating app
StarletteInstrumentor().instrument()

# Initialize settings and chat graph
settings = get_settings()
chat_graph = OtelChatStateGraph(settings.openai_api_key)

# Create Starlette app (will be automatically instrumented)
app = Starlette(
    debug=True,
    routes=[...],
)

# DON'T call instrument_app() again - it's already instrumented
```

### Step 3: Update `otel_state_graph.py`

Add LangGraph agent span:

```python
def process_chat(self, user_input: str, conversation_history: List[Dict[str, Any]] = None):
    """Process a chat message through the StateGraph workflow."""
    try:
        initial_state = {
            "user_input": user_input,
            "conversation_history": conversation_history or [],
            "error": None
        }
        
        # Add LangGraph invoke_agent span (matches Sentry SDK)
        with create_span(
            "invoke_agent LangGraph",
            "gen_ai.invoke_agent",
            kind=trace.SpanKind.INTERNAL
        ) as agent_span:
            agent_span.set_attribute("gen_ai.system", "langgraph")
            agent_span.set_attribute("gen_ai.operation.name", "invoke_agent")
            agent_span.set_attribute("agent.type", "state_graph")
            
            # Workflow execution span
            with create_span(
                "LangGraph Workflow Execution",
                "workflow.execution",
                kind=trace.SpanKind.INTERNAL
            ) as workflow_span:
                workflow_span.set_attribute("initial_state_keys", str(list(initial_state.keys())))
                workflow_span.set_attribute("user_input_length", len(user_input))
                
                # Graph invoke span
                with create_span(
                    "LangGraph Graph Invoke",
                    "workflow.langgraph_invoke",
                    kind=trace.SpanKind.INTERNAL
                ) as graph_invoke_span:
                    graph_invoke_span.set_attribute("description", 
                        "LangGraph internal processing during graph.invoke()")
                    graph_invoke_span.set_attribute("state_keys", str(list(initial_state.keys())))
                    
                    result = self.graph.invoke(initial_state)
                    
                    # ... rest of the code
```

### Step 4: Update `requirements.txt`

Add HTTP client instrumentation:

```txt
# OpenTelemetry HTTP client instrumentation
opentelemetry-instrumentation-requests>=0.41b0
opentelemetry-instrumentation-httpx>=0.41b0
```

## 🧪 Testing the Fix

### 1. Install New Dependencies

```bash
pip install opentelemetry-instrumentation-requests opentelemetry-instrumentation-httpx
```

### 2. Apply the Code Changes

Update the files as described above.

### 3. Run the Server

```bash
python otel_web_main.py
```

### 4. Send a Test Request

```bash
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?", "session_id": "test123"}'
```

### 5. Check Sentry

Expected trace structure:
```
POST /api/chat
└── Autogrouped — middleware.starlette
    └── invoke_agent LangGraph
        └── LangGraph Workflow Execution
            └── LangGraph Graph Invoke
                ├── Node: input_validation
                ├── Node: context_preparation
                ├── Node: llm_generation
                │   ├── LLM Generation with OpenAI
                │   │   └── chat gpt-3.5-turbo
                │   │       └── http.client — POST OpenAI
                ├── Node: response_processing
                └── Node: conversation_update
```

## 📊 Expected Results

### Before Fix
- ❌ Disconnected spans
- ❌ No HTTP root span
- ❌ No LangGraph agent span
- ❌ No automatic HTTP client spans

### After Fix
- ✅ Complete trace hierarchy
- ✅ HTTP server root span (from Starlette)
- ✅ LangGraph agent span (manual)
- ✅ HTTP client spans (from requests/httpx instrumentation)
- ✅ All spans connected in proper parent-child relationships

## 🎯 Parity Checklist

Compare with Sentry SDK trace `40b5515620eb418c9ce9f216a724e07c`:

- [ ] HTTP server root span (`http.server — /chat`)
- [ ] Starlette middleware span (`middleware.starlette`)
- [ ] LangGraph agent span (`gen_ai.invoke_agent`)
- [ ] Workflow execution span (`workflow.execution`)
- [ ] Graph invoke span (`workflow.langgraph_invoke`)
- [ ] Node operation spans (5 nodes)
- [ ] LLM generation spans (ai.chat hierarchy)
- [ ] HTTP client span (`http.client — POST OpenAI`)
- [ ] Proper timing (total ~950ms)
- [ ] All spans connected in hierarchy

## 🚀 Next Steps

1. Apply all code changes
2. Install new dependencies
3. Test with real requests
4. Verify trace in Sentry dashboard
5. Compare span count and hierarchy with Sentry SDK trace
6. Adjust span names/operations to match exactly

