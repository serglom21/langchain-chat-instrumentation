"""
Baseline web server entry point - runs on PORT 8001.

This allows you to run both versions side-by-side:
- Port 8000: Custom instrumented version
- Port 8001: Baseline auto-instrumentation only
"""
import uvicorn
from baseline.baseline_web_app import app

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🔬 BASELINE WEB SERVER - Auto-Instrumentation Only")
    print("="*70)
    print("\nThis server uses ONLY Sentry's out-of-the-box AI monitoring.")
    print("Compare traces with the custom instrumented version on port 8000.\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # Different port to run side-by-side
        log_level="info"
    )





