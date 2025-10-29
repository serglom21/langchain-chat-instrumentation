"""
Baseline Sentry configuration using ONLY out-of-the-box auto-instrumentation.

This file demonstrates what you get with Sentry's default AI monitoring
WITHOUT any custom instrumentation. Compare this with sentry_config.py
to see the difference.
"""
import sentry_sdk
from sentry_sdk.integrations.langchain import LangchainIntegration
from config import get_settings


def setup_baseline_sentry() -> None:
    """
    Initialize Sentry with ONLY out-of-the-box auto-instrumentation.
    
    This is the minimal setup - just enabling the LangChain integration
    without any custom spans, callbacks, or manual instrumentation.
    """
    settings = get_settings()
    
    if not settings.sentry_dsn:
        print("Warning: SENTRY_DSN not provided. Sentry instrumentation will be disabled.")
        return
    
    # Minimal Sentry setup - just the basics
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=f"{settings.sentry_environment}-baseline",  # Different environment to separate traces
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        send_default_pii=True,
        debug=True,
        integrations=[
            # ONLY the LangChain integration - no custom code
            LangchainIntegration(
                include_prompts=True,
            ),
        ],
    )
    
    print("✅ Baseline Sentry initialized (auto-instrumentation only)")
    print(f"   Environment: {settings.sentry_environment}-baseline")
    print("   This will show what Sentry captures OUT OF THE BOX")

