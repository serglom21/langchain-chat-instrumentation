# 🔬 Side-by-Side Comparison Guide

This guide helps you compare Sentry's **out-of-the-box auto-instrumentation** vs **custom instrumentation** to see exactly what data you gain from manual instrumentation.

## 🎯 Quick Start

### 1. Start Both Servers

**Terminal 1 - Custom Instrumented Version (Port 8000):**
```bash
export OPENAI_API_KEY='your-key-here'
export SENTRY_DSN='your-dsn-here'
python web_main.py
```

**Terminal 2 - Baseline Auto-Instrumentation (Port 8001):**
```bash
export OPENAI_API_KEY='your-key-here'
export SENTRY_DSN='your-dsn-here'
python baseline_web_main.py
```

### 2. Open Both UIs

- **Custom Version**: http://localhost:8000 (Purple theme)
- **Baseline Version**: http://localhost:8001 (Orange/Red theme)

### 3. Send the SAME Message to Both

Send identical messages to both versions, then compare the traces in Sentry.

## 📊 What to Compare in Sentry

### Sentry Dashboard Navigation

1. Go to **Performance → Traces**
2. Filter by environment:
   - `production` = Custom instrumented version
   - `production-baseline` = Auto-instrumentation only

### Key Differences to Look For

## 🔍 Comparison Checklist

### ✅ Custom Instrumentation Shows (Port 8000)

| Feature | Description | Where to Find |
|---------|-------------|---------------|
| **Workflow Spans** | `LangGraph Workflow Execution` span | Top-level span hierarchy |
| **Node-Level Tracking** | Individual spans for each node | Child spans under workflow |
| **Token Timing** | `time_to_first_token_ms`, `time_to_last_token_ms` | Span data & measurements |
| **LangChain Overhead** | Internal processing spans | Nested under LLM generation |
| **Custom Tags** | `node_name`, `operation_type`, etc. | Span tags section |
| **Business Metrics** | Input length, word count, cache hits | Span data section |
| **Error Context** | Detailed error data per node | Error span data |
| **Performance Breakdown** | Granular timing for each step | Span waterfall |

### ❌ Baseline Auto-Instrumentation Shows (Port 8001)

| Feature | Description | What's Missing |
|---------|-------------|----------------|
| **HTTP Transaction** | Basic HTTP request tracking | ✅ Present |
| **LLM Call** | OpenAI API call | ✅ Present |
| **Basic Timing** | Total request duration | ✅ Present |
| **Workflow Visibility** | Individual node execution | ❌ **Missing** |
| **Token Timing** | Streaming metrics | ❌ **Missing** |
| **Framework Overhead** | LangChain/LangGraph processing | ❌ **Missing** |
| **Business Context** | Application-specific metrics | ❌ **Missing** |
| **Error Granularity** | Which node failed | ❌ **Missing** |

## 📈 Specific Traces to Compare

### Test Case 1: Simple Question

**Message**: "What is the capital of France?"

**Custom Version Shows**:
- Transaction: `Chat Workflow: chat_workflow`
  - Span: `LangGraph Workflow Execution`
    - Span: `Node: input_validation` (~1ms)
    - Span: `Node: context_preparation` (~2ms)
    - Span: `Node: llm_generation` (~800ms)
      - Span: `LLM Generation with OpenAI GPT-3.5-turbo`
        - Span: `LangChain LLM Invoke`
          - Span: `LangChain Internal Processing`
          - Span: `http.client` (OpenAI API)
    - Span: `Node: response_processing` (~1ms)
    - Span: `Node: conversation_update` (~1ms)

**Baseline Version Shows**:
- Transaction: `POST /chat`
  - Span: `http.client` (OpenAI API)
  - (That's it!)

### Test Case 2: Multi-turn Conversation

Send 3 messages in sequence to both versions.

**Custom Version Shows**:
- Conversation history length in tags
- Context preparation timing
- Cache hits (if repeated query)
- Complete workflow for each message

**Baseline Version Shows**:
- Just the HTTP transaction
- Basic LLM call
- No conversation context visibility

### Test Case 3: Error Scenario

Send an empty message or cause an error.

**Custom Version Shows**:
- Which node failed
- Error type and message
- Execution state at failure
- Partial workflow completion

**Baseline Version Shows**:
- HTTP error
- Generic error message
- No workflow context

## 🎯 Key Insights to Discover

### 1. Span Hierarchy Depth

**Question**: How many spans do you see?

- **Custom**: 10-15+ spans per request
- **Baseline**: 1-3 spans per request

### 2. Performance Breakdown

**Question**: Can you identify bottlenecks?

- **Custom**: Yes - see exactly which node is slow
- **Baseline**: No - just total time

### 3. Token Timing

**Question**: Can you see streaming performance?

- **Custom**: Yes - `time_to_first_token_ms` measurement
- **Baseline**: No - not captured

### 4. Business Context

**Question**: Can you see application-specific data?

- **Custom**: Yes - input length, word count, cache hits, etc.
- **Baseline**: No - just technical data

### 5. Error Debugging

**Question**: Can you identify where errors occur?

- **Custom**: Yes - exact node and operation
- **Baseline**: No - just that it failed

## 📝 Comparison Worksheet

Use this to document your findings:

```
Test Message: _________________________________

CUSTOM VERSION (Port 8000)
- Total Spans: _______
- Span Depth: _______
- Time to First Token: _______ ms
- Slowest Node: _______
- Custom Tags Found: _______
- Business Metrics: _______

BASELINE VERSION (Port 8001)
- Total Spans: _______
- Span Depth: _______
- Time to First Token: _______ (available?)
- Slowest Component: _______
- Custom Tags Found: _______
- Business Metrics: _______

KEY DIFFERENCES:
1. _________________________________
2. _________________________________
3. _________________________________
```

## 🔬 Advanced Comparisons

### Performance Analysis

1. **Send 10 identical messages to each version**
2. **Compare average response times**
3. **Look for caching effects in custom version**

### Error Handling

1. **Trigger errors in both versions**
2. **Compare error context and debugging info**
3. **Note which version provides better troubleshooting data**

### Scalability Insights

1. **Send complex multi-turn conversations**
2. **Compare visibility into conversation state**
3. **Identify which version helps optimize performance**

## 📊 Expected Results Summary

| Metric | Custom | Baseline | Improvement |
|--------|--------|----------|-------------|
| Spans per Request | 10-15+ | 1-3 | **5-10x more visibility** |
| Token Timing | ✅ Yes | ❌ No | **Critical for UX** |
| Node-Level Metrics | ✅ Yes | ❌ No | **Bottleneck identification** |
| Business Context | ✅ Rich | ❌ None | **Application insights** |
| Error Granularity | ✅ Detailed | ❌ Basic | **Faster debugging** |
| Framework Overhead | ✅ Visible | ❌ Hidden | **Performance tuning** |

## 💡 Key Takeaways

After comparing both versions, you should see that **custom instrumentation provides**:

1. **10x More Visibility**: See every step of your AI workflow
2. **Performance Insights**: Identify exact bottlenecks
3. **Business Context**: Track application-specific metrics
4. **Better Debugging**: Know exactly where errors occur
5. **User Experience Metrics**: Token timing for perceived performance
6. **Optimization Opportunities**: See framework overhead and caching effects

## 🎓 Learning Points

### What Auto-Instrumentation Captures Well
- ✅ HTTP requests and responses
- ✅ Database queries (if applicable)
- ✅ External API calls (OpenAI)
- ✅ Basic timing information

### What Auto-Instrumentation Misses
- ❌ Application workflow structure
- ❌ Business logic execution
- ❌ Framework internal processing
- ❌ Streaming/token-level metrics
- ❌ Custom business metrics
- ❌ Granular error context

## 🚀 Next Steps

1. **Document Your Findings**: Note the specific gaps you discover
2. **Identify Critical Metrics**: Which custom metrics are most valuable?
3. **Prioritize Instrumentation**: What's worth the effort?
4. **Share with Team**: Show the comparison to stakeholders

---

**Remember**: Both versions are running the SAME application logic. The only difference is the Sentry instrumentation level. This isolated comparison shows exactly what value custom instrumentation adds!


