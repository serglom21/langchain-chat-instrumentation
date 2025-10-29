# LangChain + StateGraph Sentry Instrumentation Example

This repository demonstrates how to properly instrument a LangChain application using StateGraph with Sentry for comprehensive AI Agent monitoring and custom span tracking.

This example provides a **complete working solution** with proper span hierarchy, AI Agent monitoring, and a beautiful web chat interface.

## 🎨 Web Chat Interface

Try the interactive chat UI to test the instrumentation:

```bash
./start_chat_ui.sh
# Then open http://localhost:8000
```

See [CHAT_UI_README.md](CHAT_UI_README.md) for details.

## 🔬 NEW: Side-by-Side Comparison

**Compare custom instrumentation vs auto-instrumentation in isolation!**

We've created a complete baseline version that uses ONLY Sentry's out-of-the-box auto-instrumentation. Run both versions side-by-side to see exactly what data you gain from custom instrumentation:

```bash
# Start both servers (different ports)
./compare_both.sh

# Or start individually:
python web_main.py          # Custom (port 8000, purple theme)
python baseline_web_main.py  # Baseline (port 8001, orange theme)
```

**Then compare traces in Sentry:**
- Custom version: `production` environment
- Baseline version: `production-baseline` environment

See [COMPARISON_GUIDE.md](COMPARISON_GUIDE.md) for detailed comparison instructions.

## 🏗️ Architecture Overview

```
Chat Workflow (Transaction)
├── LangGraph Workflow Execution (Span)
│   └── invoke_agent LangGraph (gen_ai.invoke_agent)
│       ├── Node: input_validation (Custom Span)
│       ├── Node: llm_generation (Custom Span)
│       ├── Node: response_processing (Custom Span)
│       ├── Node: conversation_update (Custom Span)
│       ├── LLM Generation with OpenAI GPT-3.5-turbo (ai.chat)
│       ├── chat gpt-3.5-turbo (gen_ai.chat)
│       └── http.client (OpenAI API call)
```

## 📁 Key Files

### Core Application Files
- **`main.py`** - Creates the root `chat_workflow` transaction
- **`state_graph.py`** - LangGraph StateGraph implementation with workflow spans
- **`chat_nodes.py`** - Individual node functions with custom spans
- **`sentry_config.py`** - Sentry SDK configuration with LangChain integration

### Configuration Files
- **`config.py`** - Pydantic settings for environment variables
- **`requirements.txt`** - Python dependencies
- **`test_chat.py`** - Test script to verify instrumentation

## 🔧 Implementation Details

### 1. Sentry Configuration (`sentry_config.py`)

**Critical Configuration:**
```python
sentry_sdk.init(
    dsn=settings.sentry_dsn,
    environment=settings.sentry_environment,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    send_default_pii=True,  # Required for AI monitoring
    debug=True,  # Enable for troubleshooting
    integrations=[
        LangchainIntegration(
            include_prompts=True,  # Include LLM inputs/outputs
        ),
    ],
    disabled_integrations=[
        OpenAIIntegration(),  # Critical: Disable for correct token accounting
    ],
)
```

**Key Points:**
- ✅ **LangChain Integration**: Required for AI Agent monitoring
- ✅ **OpenAI Integration Disabled**: Prevents double token counting
- ✅ **PII Enabled**: Allows prompt/output visibility
- ✅ **Flask Blocked**: Prevents auto-detection conflicts

### 2. Transaction Management (`main.py`)

**Root Transaction Creation:**
```python
def process_message(self, user_input: str, conversation_history: List[Dict[str, Any]] = None):
    # Create transaction for the entire chat workflow
    with sentry_sdk.start_transaction(
        op="chat_workflow",
        name="Chat Workflow: chat_workflow"
    ) as transaction:
        # All spans created within this context will be children
        result = self.chat_graph.process_chat(user_input, conversation_history)
        return result
```

**Key Points:**
- ✅ **Single Transaction**: One transaction per request
- ✅ **Context Manager**: Ensures proper transaction lifecycle
- ✅ **Root Span**: All other spans become children

### 3. Workflow Spans (`state_graph.py`)

**Workflow Execution Span:**
```python
def process_chat(self, user_input: str, conversation_history: List[Dict[str, Any]] = None):
    # DON'T create a new transaction - work within existing context
    with sentry_sdk.start_span(
        op="workflow.execution",
        name="LangGraph Workflow Execution"
    ) as workflow_span:
        # Execute the graph - nodes will create spans within this context
        result = self.graph.invoke(initial_state)
        return result
```

**Key Points:**
- ✅ **No Transaction Creation**: Works within existing transaction
- ✅ **Workflow Span**: Represents the entire LangGraph execution
- ✅ **Node Context**: All nodes create spans within this context

### 4. Node Spans (`chat_nodes.py`)

**Individual Node Instrumentation:**
```python
def input_validation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
    # Create span within transaction context
    with sentry_sdk.start_span(
        op="node_operation",
        name="Node: input_validation"
    ) as span:
        span.set_tag("node_name", "input_validation")
        span.set_tag("operation_type", "validation")
        
        # Node logic here
        user_input = state.get("user_input", "")
        # ... validation logic
        
        return {**state, "validated_input": user_input.strip()}
```

**Key Points:**
- ✅ **Custom Spans**: Each node creates its own span
- ✅ **Rich Metadata**: Tags and data for debugging
- ✅ **Transaction Context**: Spans automatically become children

### 5. AI-Specific Spans (`chat_nodes.py`)

**LLM Generation with AI Monitoring:**
```python
def llm_generation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
    with sentry_sdk.start_span(
        op="ai.chat",
        name="LLM Generation with OpenAI GPT-3.5-turbo"
    ) as ai_span:
        # Set AI-specific attributes
        ai_span.set_data("gen_ai.model", "gpt-3.5-turbo")
        ai_span.set_data("gen_ai.operation", "chat")
        ai_span.set_data("gen_ai.system", "You are a helpful AI assistant.")
        
        # LangChain will automatically create gen_ai.chat spans
        response = self.llm.invoke(messages)
        return {**state, "llm_response": response.content}
```

**Key Points:**
- ✅ **AI Operation Spans**: `ai.chat` for custom tracking
- ✅ **LangChain Integration**: Automatically creates `gen_ai.*` spans
- ✅ **Token Tracking**: Automatic via LangChain integration

## 🚨 Common Pitfalls & Solutions

### ❌ Problem: Only 1 Span in Traces
**Cause:** Creating multiple transactions
```python
# WRONG - Creates separate transactions
def process_chat(self, user_input):
    transaction = create_root_span("chat_workflow")  # Transaction 1
    with sentry_sdk.start_transaction(...):          # Transaction 2
        # Spans in Transaction 2 don't appear in Transaction 1
```

**Solution:** Single transaction context
```python
# CORRECT - Single transaction with child spans
def process_message(self, user_input):
    with sentry_sdk.start_transaction(...):  # Single transaction
        result = self.chat_graph.process_chat(user_input)  # Creates child spans
```

### ❌ Problem: No AI Agent Monitoring Data
**Cause:** Missing or incorrect LangChain integration
```python
# WRONG - Missing LangChain integration
sentry_sdk.init(integrations=[])

# WRONG - OpenAI integration conflicts
sentry_sdk.init(integrations=[LangchainIntegration(), OpenAIIntegration()])
```

**Solution:** Correct integration setup
```python
# CORRECT - LangChain enabled, OpenAI disabled
sentry_sdk.init(
    integrations=[LangchainIntegration(include_prompts=True)],
    disabled_integrations=[OpenAIIntegration()],
)
```

### ❌ Problem: Spans Not Appearing
**Cause:** Spans created outside transaction context
```python
# WRONG - No active transaction
def some_function():
    with sentry_sdk.start_span(...):  # No parent transaction
        pass
```

**Solution:** Ensure transaction context
```python
# CORRECT - Within transaction context
def process_message(self, user_input):
    with sentry_sdk.start_transaction(...):
        with sentry_sdk.start_span(...):  # Child of transaction
            pass
```

## 🧪 Testing the Implementation

### Run the Test Script
```bash
python test_chat.py
```

### Verify in Sentry
1. **Check Traces**: Look for multiple spans per trace
2. **Check AI Agent Dashboard**: Should show token usage and costs
3. **Check Span Hierarchy**: Parent-child relationships should be visible

### Expected Trace Structure
```
Chat Workflow: chat_workflow [~800ms]
├── LangGraph Workflow Execution [~800ms]
│   └── invoke_agent LangGraph [~800ms]
│       ├── Node: input_validation [~0ms]
│       ├── Node: llm_generation [~700ms]
│       │   ├── LLM Generation with OpenAI GPT-3.5-turbo [~700ms]
│       │   └── chat gpt-3.5-turbo [~700ms]
│       ├── Node: response_processing [~0ms]
│       ├── Node: conversation_update [~0ms]
│       └── http.client [~300ms]
```

## 📊 What You Get

### Sentry Traces
- ✅ **Complete Workflow Visibility**: Every step tracked
- ✅ **Performance Metrics**: Duration for each component
- ✅ **Error Context**: Full error trace with context
- ✅ **Custom Metadata**: Rich tags and data

### AI Agent Dashboard
- ✅ **Token Usage**: Input/output token counts
- ✅ **Cost Tracking**: Automatic cost calculation
- ✅ **Model Performance**: Time-to-first-token, etc.
- ✅ **Request/Response**: Prompt and response visibility

### Debugging Capabilities
- ✅ **Node-Level Tracking**: See which nodes are slow
- ✅ **LLM Performance**: Track AI generation time
- ✅ **Error Attribution**: Know exactly where failures occur
- ✅ **Custom Metrics**: Add your own tracking

## 🚀 Getting Started

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd ai-chat-instrumentation
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Setup Check
```bash
python setup.py
```
This will check your environment and create a `.env.template` file.

### 4. Configure Environment
Copy the template and fill in your values:
```bash
cp .env.template .env
# Edit .env with your actual API keys
```

Or set environment variables directly:
```bash
export OPENAI_API_KEY="your-openai-key"
export SENTRY_DSN="your-sentry-dsn"
export SENTRY_ENVIRONMENT="development"
```

### 5. Choose Your Mode

#### CLI Mode (Interactive Chat)
```bash
python main.py
```

#### Web API Mode (HTTP Server)
```bash
python web_main.py
```

Then test the API:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

### 6. Test Both Modes
```bash
python test_web_integration.py
```

### 7. Check Sentry
Visit your Sentry project to see the traces and AI Agent dashboard.

## 📁 Repository Structure

```
ai-chat-instrumentation/
├── README.md                    # This comprehensive guide
├── requirements.txt             # Python dependencies (includes Starlette)
├── setup.py                    # Setup verification script
├── example.py                  # Example usage script
├── test_chat.py                # Test script
├── test_web_integration.py     # Web integration test script
├── .env.template               # Environment variables template
├── .gitignore                 # Git ignore rules
├── main.py                    # CLI application (transaction creation)
├── web_main.py                # Web server entry point
├── web_app.py                 # Starlette ASGI application
├── api_routes.py              # HTTP API routes and handlers
├── state_graph.py             # LangGraph StateGraph implementation
├── chat_nodes.py              # Individual node functions with spans
├── sentry_config.py           # Sentry SDK configuration
└── config.py                  # Pydantic settings
```

## 🌐 Web API Features

The project now supports both CLI and Web API modes:

### API Endpoints

- **`POST /chat`** - Send chat messages
  ```json
  {
    "message": "Hello, how are you?",
    "conversation_history": []
  }
  ```

- **`GET /health`** - Health check
- **`GET /info`** - Service information

### Web Mode Benefits

- ✅ **HTTP API Access**: RESTful interface for integration
- ✅ **Concurrent Requests**: Handle multiple users simultaneously  
- ✅ **Enhanced Sentry**: HTTP transactions with web-specific context
- ✅ **CORS Support**: Ready for frontend integration
- ✅ **Production Ready**: ASGI server with proper middleware

### Usage Examples

**Start Web Server:**
```bash
python web_main.py
```

**Test API:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

**Python Client:**
```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "message": "Hello!",
    "conversation_history": []
})
print(response.json())
```

## 🔍 Key Learnings

1. **Single Transaction**: Create one transaction per request, not per component
2. **LangChain Integration**: Essential for AI Agent monitoring
3. **OpenAI Integration**: Must be disabled to prevent double counting
4. **Span Context**: All spans must be created within transaction context
5. **Custom Spans**: Work perfectly alongside LangChain integration
6. **Flask Conflicts**: Block Flask auto-detection to prevent issues
7. **Dual Mode Support**: CLI and Web API can coexist without conflicts

## 📝 License

MIT License - feel free to use this example in your own projects.

## 🤝 Contributing

This is an example repository. If you find issues or have improvements, please open an issue or submit a pull request.

---

**Happy Instrumenting!** 🎉
