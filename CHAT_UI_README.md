# 🎨 AI Chat Web Interface

A beautiful, modern chat interface for testing the Sentry-instrumented AI chat service.

## ✨ Features

- **Modern UI Design**: Clean, gradient-based design with smooth animations
- **Real-time Chat**: Interactive conversation with AI assistant
- **Typing Indicators**: Visual feedback while AI is generating responses
- **Conversation History**: Maintains context across multiple messages
- **Performance Metrics**: Shows response times and message counts
- **Health Monitoring**: Real-time connection status indicator
- **Responsive Design**: Works on desktop and mobile devices
- **Quick Suggestions**: Pre-built prompts to get started quickly

## 🚀 Quick Start

### 1. Set Environment Variables

```bash
export OPENAI_API_KEY='your-openai-api-key-here'
export SENTRY_DSN='your-sentry-dsn-here'  # Optional but recommended
```

### 2. Start the Web Server

**Option A: Using the start script (recommended)**
```bash
./start_chat_ui.sh
```

**Option B: Using Python directly**
```bash
python web_main.py
```

### 3. Open Your Browser

Navigate to: **http://localhost:8000**

That's it! You should see the chat interface ready to use.

## 🎯 How to Use

1. **Start a Conversation**: Type your message in the input box at the bottom
2. **Send Messages**: Press Enter or click the "Send" button
3. **Try Suggestions**: Click any of the suggestion cards to quickly start
4. **View Metrics**: Response times and message counts appear at the bottom
5. **Monitor Status**: The green indicator shows the connection is healthy

## 📊 What Gets Instrumented

Every chat interaction is fully instrumented with Sentry:

- **HTTP Requests**: Automatic transaction tracking
- **Workflow Execution**: Complete LangGraph state machine visibility
- **Node Operations**: Each processing step (validation, context prep, LLM generation, etc.)
- **Token Timing**: Time-to-first-token and streaming metrics
- **Error Tracking**: Comprehensive error capture with context
- **Performance Metrics**: Response times, cache hits, and optimization data

## 🔍 Testing the Integration

### Test Basic Functionality

1. Send a simple message: "Hello!"
2. Check that you receive a response
3. Send a follow-up message to test conversation history

### Test Sentry Instrumentation

1. Open Sentry dashboard
2. Navigate to Performance → Traces
3. Find your chat transactions
4. Verify you see:
   - Complete span hierarchy
   - Node-level operations
   - Token timing metrics
   - Custom tags and data

### Test Error Handling

1. Stop the server
2. Try sending a message
3. Verify error message appears in the UI
4. Restart server and verify status indicator turns green

## 🎨 UI Components

### Chat Header
- Service name and branding
- Real-time connection status indicator
- Service information

### Message Area
- User messages (purple gradient, right-aligned)
- AI responses (white background, left-aligned)
- Timestamps for each message
- Smooth scroll animations

### Input Area
- Auto-resizing text input
- Send button with hover effects
- Keyboard shortcuts (Enter to send, Shift+Enter for new line)

### Metrics Bar
- Response time tracking
- Message count
- Appears after first message

### Welcome Screen
- Friendly greeting
- Quick suggestion cards
- Helpful prompts to get started

## 🛠️ Customization

### Change API Endpoint

Edit `static/chat.html` and modify:
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

### Modify Styling

All styles are in the `<style>` section of `static/chat.html`. Key variables:
- Primary gradient: `#667eea` to `#764ba2`
- Success color: `#4ade80`
- Error color: `#ef4444`

### Add More Suggestions

Edit the suggestion cards in `static/chat.html`:
```html
<div class="suggestion-card" onclick="sendSuggestion('Your prompt here')">
    <div class="icon">🎯</div>
    <div class="text">Your prompt here</div>
</div>
```

## 🐛 Troubleshooting

### "Unable to connect to the API server"
- Ensure the web server is running: `python web_main.py`
- Check that port 8000 is not in use
- Verify OPENAI_API_KEY is set

### "Failed to get response from the assistant"
- Check server logs for errors
- Verify your OpenAI API key is valid
- Check Sentry dashboard for error details

### Chat UI not loading
- Ensure `static/chat.html` exists
- Check browser console for errors
- Verify the web server started successfully

### Styling issues
- Clear browser cache
- Try hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
- Check browser console for CSS errors

## 📱 Browser Compatibility

Tested and working on:
- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## 🔗 Related Files

- `web_app.py` - Starlette application with routes
- `api_routes.py` - API endpoint handlers
- `main.py` - Core chat service with Sentry instrumentation
- `state_graph.py` - LangGraph workflow definition
- `chat_nodes.py` - Individual node implementations

## 💡 Tips

1. **Use Quick Suggestions**: Great for testing different types of queries
2. **Monitor Sentry**: Keep the Sentry dashboard open to see real-time instrumentation
3. **Test Conversation History**: Send multiple related messages to test context
4. **Check Performance**: Use the metrics bar to track response times
5. **Try Error Cases**: Test edge cases to verify error handling

## 🎉 Next Steps

- Customize the UI to match your brand
- Add more suggestion prompts
- Implement user authentication
- Add conversation export functionality
- Integrate with your production environment

---

**Built with ❤️ using Starlette, OpenAI, and Sentry**

