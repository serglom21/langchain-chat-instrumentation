# Chat UI Assets

This directory contains the static assets for the AI Chat web interface.

## Files

- `chat.html` - Complete single-page chat application with embedded CSS and JavaScript

## Features

### Visual Design
- **Gradient Theme**: Purple gradient (#667eea to #764ba2) for headers and user messages
- **Clean Layout**: Modern card-based design with smooth shadows
- **Responsive**: Mobile-friendly with adaptive layouts
- **Animations**: Smooth slide-in effects for messages and typing indicators

### User Experience
- **Real-time Status**: Connection indicator in header
- **Typing Feedback**: Animated dots while AI is responding
- **Auto-scroll**: Messages automatically scroll into view
- **Auto-resize**: Input field grows with content
- **Keyboard Shortcuts**: Enter to send, Shift+Enter for new line

### Functionality
- **Conversation History**: Maintains context across messages
- **Quick Suggestions**: Pre-built prompts to get started
- **Performance Metrics**: Response time and message count tracking
- **Error Handling**: User-friendly error messages
- **Health Checks**: Automatic API connection verification

## Technical Details

- **Pure HTML/CSS/JS**: No build process required
- **Single File**: Everything in one HTML file for easy deployment
- **Modern CSS**: Flexbox, Grid, CSS animations
- **Fetch API**: Modern async HTTP requests
- **ES6+**: Modern JavaScript features

## Customization

All styling is contained in the `<style>` section of `chat.html`. Key areas:

1. **Colors**: Search for gradient definitions and color codes
2. **Spacing**: Modify padding/margin values
3. **Animations**: Adjust keyframe definitions
4. **Layout**: Change flexbox/grid properties

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Mobile 90+)

## API Integration

The chat UI expects these endpoints:

- `GET /health` - Health check
- `POST /chat` - Send message and get response
  - Request: `{ "message": string, "conversation_history": array }`
  - Response: `{ "success": boolean, "response": string, "conversation_history": array }`

## Development

To modify the UI:

1. Edit `chat.html`
2. Refresh browser (no build step needed)
3. Test on different screen sizes
4. Check browser console for errors

## Production Notes

Before deploying to production:

1. Update CORS settings in `web_app.py`
2. Change `API_BASE_URL` in chat.html if needed
3. Consider adding authentication
4. Enable HTTPS
5. Optimize assets (minify CSS/JS)
6. Add proper error logging

