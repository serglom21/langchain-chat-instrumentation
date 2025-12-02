"""API routes for the Starlette web application."""
import json
import sentry_sdk
from typing import Dict, Any, List
from starlette.responses import JSONResponse
from starlette.requests import Request
from main import ChatService


class ChatAPIHandler:
    """Handles HTTP API requests for chat functionality."""
    
    def __init__(self):
        """Initialize the chat service."""
        self.chat_service = ChatService()
    
    async def chat_endpoint(self, request: Request) -> JSONResponse:
        """
        Handle chat requests via HTTP API.
        
        Sentry's Starlette integration automatically creates HTTP transactions.
        We work within that transaction context to create workflow spans.
        """
        try:
            # Parse request body
            body = await request.json()
            user_input = body.get("message", "")
            conversation_history = body.get("conversation_history", [])
            
            # Validate input
            if not user_input.strip():
                return JSONResponse(
                    {"error": "Message cannot be empty", "success": False},
                    status_code=400
                )
            
            # Add request metadata to Sentry (within the automatic HTTP transaction)
            sentry_sdk.set_tag("user_input_length", len(user_input))
            sentry_sdk.set_tag("conversation_history_length", len(conversation_history))
            sentry_sdk.set_tag("http.route", "/chat")
            
            # Use ChatService WITHOUT creating a separate transaction
            # The ChatService will create spans within the automatic HTTP transaction
            result = self.chat_service.process_message_without_transaction(user_input, conversation_history)
            
            # Add response metadata to Sentry
            sentry_sdk.set_tag("response_success", result.get("success", False))
            if result.get("success"):
                sentry_sdk.set_tag("response_length", len(result.get("response", "")))
            
            return JSONResponse(result)
                
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "Invalid JSON in request body", "success": False},
                status_code=400
            )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            sentry_sdk.set_tag("error", True)
            sentry_sdk.set_tag("error_type", type(e).__name__)
            
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
        sentry_sdk.set_tag("http.route", "/health")
        
        return JSONResponse({
            "status": "healthy",
            "service": "ai-chat-instrumentation",
            "version": "1.0.0"
        })
    
    async def info_endpoint(self, request: Request) -> JSONResponse:
        """Service information endpoint."""
        sentry_sdk.set_tag("http.route", "/info")
        
        return JSONResponse({
            "service": "AI Chat with Sentry Instrumentation",
            "description": "LangChain + StateGraph chat service with comprehensive Sentry monitoring",
            "endpoints": {
                "POST /chat": "Send a chat message",
                "GET /health": "Health check",
                "GET /info": "Service information"
            },
            "features": [
                "LangGraph workflow execution",
                "OpenAI GPT-3.5-turbo integration",
                "Comprehensive Sentry instrumentation",
                "AI/LLM monitoring",
                "Token usage tracking",
                "Performance metrics"
            ]
        })


# Create handler instance
api_handler = ChatAPIHandler()
