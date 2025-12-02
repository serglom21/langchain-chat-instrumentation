"""Simple test to check if OTel web server can handle requests."""
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse

from otel.otel_config import setup_opentelemetry

# Initialize OpenTelemetry
setup_opentelemetry()

async def test_endpoint(request):
    """Simple test endpoint."""
    try:
        data = await request.json()
        message = data.get('message', '')
        
        # Just return a simple response without calling LangChain
        return JSONResponse({
            'response': f'Echo: {message}',
            'status': 'success'
        })
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()
        return JSONResponse({
            'error': str(e),
            'type': type(e).__name__
        }, status_code=500)

# Create app
app = Starlette(
    debug=True,
    routes=[
        Route('/api/test', test_endpoint, methods=['POST']),
    ],
)

if __name__ == '__main__':
    print("Starting simple test server on port 8003...")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")





