# 📁 Baseline Files Overview

These files implement the **baseline version** with ONLY Sentry's out-of-the-box auto-instrumentation.

## Core Baseline Files

### Configuration
- **`baseline_sentry_config.py`**
  - Minimal Sentry setup
  - Only LangChain integration enabled
  - No custom spans or callbacks
  - Uses `-baseline` environment suffix

### Application Logic
- **`baseline_chat_nodes.py`**
  - Chat nodes WITHOUT custom instrumentation
  - No `@instrument_node` decorators
  - No `ComprehensiveSentryCallback`
  - No manual span creation
  - Pure business logic only

- **`baseline_state_graph.py`**
  - StateGraph WITHOUT custom spans
  - No workflow instrumentation
  - No transaction management
  - Just plain graph execution

- **`baseline_main.py`**
  - Chat service WITHOUT custom transactions
  - No manual span creation
  - No custom tags or measurements
  - CLI test interface included

### Web API
- **`baseline_api_routes.py`**
  - API routes WITHOUT custom Sentry tags
  - No manual instrumentation
  - Relies on auto HTTP tracking

- **`baseline_web_app.py`**
  - Starlette app WITHOUT custom middleware
  - No custom Sentry context
  - Runs on port 8001

- **`baseline_web_main.py`**
  - Web server entry point
  - Runs on port 8001 (vs 8000 for custom)

### UI
- **`static/baseline_chat.html`**
  - Chat UI with orange/red theme
  - Points to port 8001
  - Labeled as "BASELINE"

## Helper Files

### Scripts
- **`compare_both.sh`**
  - Starts both servers simultaneously
  - Custom on port 8000
  - Baseline on port 8001

### Documentation
- **`COMPARISON_GUIDE.md`**
  - Detailed comparison instructions
  - What to look for in Sentry
  - Test cases and worksheets

- **`COMPARISON_SUMMARY.md`**
  - Visual comparison of trace structures
  - Key differences highlighted
  - Real-world impact examples

- **`QUICK_START_COMPARISON.md`**
  - 30-second quick start
  - Fast comparison test
  - Key takeaways

- **`BASELINE_FILES.md`** (this file)
  - Overview of all baseline files

## File Comparison

| Aspect | Custom Files | Baseline Files |
|--------|-------------|----------------|
| Sentry Config | `sentry_config.py` | `baseline_sentry_config.py` |
| Chat Nodes | `chat_nodes.py` | `baseline_chat_nodes.py` |
| State Graph | `state_graph.py` | `baseline_state_graph.py` |
| Main Service | `main.py` | `baseline_main.py` |
| API Routes | `api_routes.py` | `baseline_api_routes.py` |
| Web App | `web_app.py` | `baseline_web_app.py` |
| Web Main | `web_main.py` | `baseline_web_main.py` |
| Chat UI | `static/chat.html` | `static/baseline_chat.html` |
| Port | 8000 | 8001 |
| Theme | Purple | Orange/Red |
| Environment | `production` | `production-baseline` |

## Key Differences

### What's REMOVED in Baseline Files

1. **No Custom Spans**
   - No `sentry_sdk.start_span()` calls
   - No `@instrument_node` decorators
   - No workflow instrumentation

2. **No Custom Callbacks**
   - No `ComprehensiveSentryCallback`
   - No token timing tracking
   - No LLM lifecycle hooks

3. **No Custom Tags/Data**
   - No `set_tag()` calls
   - No `set_data()` calls
   - No `set_measurement()` calls

4. **No Custom Transactions**
   - No `start_transaction()` calls
   - Relies on auto HTTP transactions only

5. **No Custom Middleware**
   - No `SentryMiddleware`
   - No custom context setting

### What's KEPT in Baseline Files

1. **Same Business Logic**
   - Identical chat functionality
   - Same LangGraph workflow
   - Same node operations

2. **Same LLM Setup**
   - Same OpenAI configuration
   - Same model and parameters

3. **Same API Structure**
   - Same endpoints
   - Same request/response format

4. **Basic Sentry Integration**
   - LangChain integration enabled
   - Auto HTTP tracking
   - Auto error capture

## Usage

### Run Baseline Only
```bash
export OPENAI_API_KEY='your-key'
export SENTRY_DSN='your-dsn'
python baseline_web_main.py
# Open http://localhost:8001
```

### Run Both for Comparison
```bash
export OPENAI_API_KEY='your-key'
export SENTRY_DSN='your-dsn'
./compare_both.sh
# Open http://localhost:8000 (custom)
# Open http://localhost:8001 (baseline)
```

### CLI Test
```bash
python baseline_main.py
```

## Sentry Environment Separation

The baseline version uses a different Sentry environment to keep traces separate:

- **Custom**: `production` (or your configured environment)
- **Baseline**: `production-baseline` (adds `-baseline` suffix)

This allows you to:
- Filter traces by environment in Sentry
- Compare side-by-side without mixing data
- Keep both versions running simultaneously

## Maintenance

When updating the custom instrumentation:

1. **Don't modify baseline files** - they should stay minimal
2. **Keep business logic in sync** - both should have same functionality
3. **Update comparison docs** - if you add new custom instrumentation

The baseline files serve as a **reference point** to show what auto-instrumentation alone provides.



