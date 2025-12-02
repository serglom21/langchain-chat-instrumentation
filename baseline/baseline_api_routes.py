"""Baseline API routes WITHOUT custom Sentry instrumentation."""
import json
from typing import Dict, Any, List
from starlette.responses import JSONResponse
from starlette.requests import Request
from baseline.baseline_main import BaselineChatService


class BaselineChatAPIHandler:
    """Handles HTTP API requests WITHOUT custom Sentry instrumentation."""
    
    def __init__(self):
        """Initialize the chat service."""
        self.chat_service = BaselineChatService()
    
    async def chat_endpoint(self, request: Request) -> JSONResponse:
        """
        Handle chat requests - NO custom Sentry instrumentation.
        
        This relies entirely on Sentry's automatic HTTP transaction tracking.
        No manual tags, no custom spans, no manual instrumentation.
        """
        try:
            body = await request.json()
            user_input = body.get("message", "")
            conversation_history = body.get("conversation_history", [])
            
            if not user_input.strip():
                return JSONResponse(
                    {"error": "Message cannot be empty", "success": False},
                    status_code=400
                )
            
            # Just process the message - no custom Sentry instrumentation
            result = self.chat_service.process_message(user_input, conversation_history)
            
            return JSONResponse(result)
                
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "Invalid JSON in request body", "success": False},
                status_code=400
            )
        except Exception as e:
            return JSONResponse(
                {
                    "error": str(e),
                    "success": False,
                    "response": "I apologize, but I encountered an error processing your request. Please try again."
                },
                status_code=500
            )
    
    async def health_endpoint(self, request: Request) -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse({
            "status": "healthy",
            "service": "ai-chat-baseline",
            "version": "1.0.0-baseline"
        })
    
    async def info_endpoint(self, request: Request) -> JSONResponse:
        """Service information endpoint."""
        return JSONResponse({
            "service": "AI Chat - Baseline (Auto-Instrumentation Only)",
            "description": "LangChain + StateGraph chat service with ONLY Sentry's out-of-the-box monitoring",
            "endpoints": {
                "POST /chat": "Send a chat message",
                "GET /health": "Health check",
                "GET /info": "Service information"
            },
            "instrumentation": "Auto-instrumentation only (no custom spans)",
            "compare_with": "Custom instrumented version on port 8000"
        })


# Create handler instance
baseline_api_handler = BaselineChatAPIHandler()





