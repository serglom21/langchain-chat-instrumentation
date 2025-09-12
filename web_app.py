"""Starlette web application for the AI chat service."""
import sentry_sdk
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from api_routes import api_handler


class SentryMiddleware(BaseHTTPMiddleware):
    """Custom middleware to enhance Sentry HTTP instrumentation."""
    
    async def dispatch(self, request: Request, call_next):
        """Add additional Sentry context for HTTP requests."""
        # Set user context if available (you can extend this)
        sentry_sdk.set_context("http", {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None
        })
        
        # Set tags
        sentry_sdk.set_tag("service", "ai-chat-instrumentation")
        sentry_sdk.set_tag("component", "web-api")
        
        response = await call_next(request)
        
        # Add response context
        sentry_sdk.set_context("response", {
            "status_code": response.status_code,
            "headers": dict(response.headers)
        })
        
        return response


# Create Starlette application
app = Starlette(
    debug=True,
    routes=[
        Route("/chat", api_handler.chat_endpoint, methods=["POST"]),
        Route("/health", api_handler.health_endpoint, methods=["GET"]),
        Route("/info", api_handler.info_endpoint, methods=["GET"]),
    ],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(SentryMiddleware),
    ]
)


# Optional: Add startup event to initialize services
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("🚀 AI Chat Web Service Starting...")
    print("📡 Sentry instrumentation enabled")
    print("🌐 Web API available at:")
    print("   POST /chat - Send chat messages")
    print("   GET /health - Health check")
    print("   GET /info - Service information")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("👋 AI Chat Web Service shutting down...")
