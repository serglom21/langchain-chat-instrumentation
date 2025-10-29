# ⚡ Quick Start: Side-by-Side Comparison

## 🚀 30-Second Setup

```bash
# 1. Set environment variables
export OPENAI_API_KEY='your-key-here'
export SENTRY_DSN='your-dsn-here'

# 2. Start both servers
./compare_both.sh

# 3. Open both UIs in separate tabs
# - http://localhost:8000 (Purple - Custom)
# - http://localhost:8001 (Orange - Baseline)
```

## 📝 Quick Test

1. **Send the same message to both**: "What is Python?"
2. **Go to Sentry → Performance → Traces**
3. **Filter by environment**:
   - `production` = Custom
   - `production-baseline` = Baseline
4. **Compare the traces**

## 👀 What You'll See

### Custom (Purple, Port 8000)
- ✅ 15+ spans showing complete workflow
- ✅ Node-level timing
- ✅ Token timing metrics
- ✅ Business context tags
- ✅ Framework overhead visible

### Baseline (Orange, Port 8001)
- ❌ Only 2 spans (HTTP + API call)
- ❌ No workflow visibility
- ❌ No token timing
- ❌ No business context
- ❌ Framework overhead hidden

## 🎯 Key Differences

| What | Custom | Baseline |
|------|--------|----------|
| Spans | 15+ | 2 |
| Can find bottlenecks? | ✅ Yes | ❌ No |
| Token timing? | ✅ Yes | ❌ No |
| Business metrics? | ✅ Yes | ❌ No |
| Debug errors easily? | ✅ Yes | ❌ No |

## 💡 The Point

**Auto-instrumentation alone is NOT enough for AI/LLM applications.**

You need custom instrumentation to see:
- Workflow execution
- Token-level performance
- Business context
- Framework overhead
- Granular errors

## 📚 Learn More

- [COMPARISON_GUIDE.md](COMPARISON_GUIDE.md) - Detailed comparison instructions
- [COMPARISON_SUMMARY.md](COMPARISON_SUMMARY.md) - Visual comparison
- [README.md](README.md) - Full documentation


