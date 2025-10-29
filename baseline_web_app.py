"""Baseline Starlette web application WITHOUT custom Sentry middleware."""
import sentry_sdk
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from baseline_api_routes import baseline_api_handler
import os


async def serve_baseline_chat_ui(request: Request):
    """Serve the baseline chat UI."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    chat_file = os.path.join(static_dir, "baseline_chat.html")
    return FileResponse(chat_file)


# Create Starlette application - NO custom Sentry middleware
app = Starlette(
    debug=True,
    routes=[
        Route("/", serve_baseline_chat_ui, methods=["GET"]),
        Route("/chat", baseline_api_handler.chat_endpoint, methods=["POST"]),
        Route("/health", baseline_api_handler.health_endpoint, methods=["GET"]),
        Route("/info", baseline_api_handler.info_endpoint, methods=["GET"]),
        Mount("/static", StaticFiles(directory="static"), name="static"),
    ],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        # NO custom Sentry middleware - just auto-instrumentation
    ]
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("🔬 Baseline AI Chat Web Service Starting...")
    print("📡 Sentry auto-instrumentation enabled (NO custom spans)")
    print("🌐 Baseline API available at:")
    print("   GET  / - Baseline Chat UI")
    print("   POST /chat - Send chat messages")
    print("   GET  /health - Health check")
    print("   GET  /info - Service information")
    print("\n💡 Open your browser to: http://localhost:8001")
    print("   Compare with custom instrumented version on port 8000")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("👋 Baseline AI Chat Web Service shutting down...")


