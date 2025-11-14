"""
Configuration for hybrid OpenTelemetry + Sentry SDK instrumentation.

This module initializes both systems to work together:
- OpenTelemetry sends traces to Sentry via OTLP
- Sentry SDK captures errors and events with full context
- Trace context is propagated between both systems
"""

import os
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION


def init_hybrid_instrumentation(
    service_name: str = "ai-chat-service",
    service_version: str = "1.0.0",
    environment: Optional[str] = None,
    enable_logging: bool = True,
) -> None:
    """
    Initialize both OpenTelemetry and Sentry SDK for hybrid instrumentation.
    
    This setup allows you to:
    1. Use OpenTelemetry for distributed tracing
    2. Use Sentry SDK for error reporting
    3. Link errors to traces using shared context
    
    Environment Variables Required:
    - SENTRY_DSN: Sentry project DSN
    - SENTRY_OTLP_ENDPOINT: Sentry OTLP traces endpoint (from project settings)
    - SENTRY_PUBLIC_KEY: Sentry public key (from project settings)
    
    Args:
        service_name: Name of your service
        service_version: Version of your service
        environment: Environment name (production, staging, development)
        enable_logging: Whether to enable Sentry logging integration
    """
    # Get configuration from environment
    sentry_dsn = os.getenv("SENTRY_DSN")
    otlp_endpoint = os.getenv("SENTRY_OTLP_ENDPOINT")
    sentry_public_key = os.getenv("SENTRY_PUBLIC_KEY")
    
    if not sentry_dsn:
        raise ValueError("SENTRY_DSN environment variable is required")
    
    environment = environment or os.getenv("ENVIRONMENT", "development")
    
    # =========================================================================
    # 1. Initialize Sentry SDK (for error reporting and events)
    # =========================================================================
    
    integrations = []
    
    if enable_logging:
        integrations.append(
            LoggingIntegration(
                level=None,  # Capture all levels
                event_level=None  # Don't send logs as events by default
            )
        )
    
    print(f"🔧 DEBUG: About to initialize Sentry SDK (hybrid_config.py version)")
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=f"{service_name}@{service_version}",
        
        # Disable auto integrations to avoid conflicting with OTel instrumentation
        auto_enabling_integrations=False,
        
    )
    
    print(f"✅ Sentry SDK initialized (DSN: {sentry_dsn[:40]}...)")
    print(f"   - auto_enabling_integrations: False")
    print(f"   - traces_sample_rate: 1.0")
    
    # =========================================================================
    # 2. Initialize OpenTelemetry (for distributed tracing)
    # =========================================================================
    
    if otlp_endpoint and sentry_public_key:
        # Configure resource (service metadata)
        resource = Resource(attributes={
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": environment,
        })
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        
        # Configure OTLP exporter to send to Sentry
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers={
                "x-sentry-auth": f"sentry sentry_key={sentry_public_key}"
            }
        )
        
        # Add span processor
        tracer_provider.add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )
        
        # Set as global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        print(f"✅ OpenTelemetry initialized (endpoint: {otlp_endpoint})")
    else:
        print("⚠️  SENTRY_OTLP_ENDPOINT or SENTRY_PUBLIC_KEY not set - OpenTelemetry disabled")
        print("   Falling back to Sentry SDK only mode")
    
    print(f"🚀 Hybrid instrumentation ready for '{service_name}' ({environment})")


def before_send_hook(event, hint):
    """
    Hook to filter or modify events before sending to Sentry.
    
    You can use this to:
    - Filter out certain errors
    - Add custom context
    - Scrub sensitive data
    - Modify event properties
    
    Args:
        event: The event dictionary
        hint: Additional context about the event
        
    Returns:
        Modified event or None to drop the event
    """
    # Example: Filter out specific exception types
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        
        # Don't send KeyboardInterrupt
        if isinstance(exc_value, KeyboardInterrupt):
            return None
    
    # Example: Add custom tags based on event properties
    if "exception" in event:
        # You could add custom logic here
        pass
    
    return event


def get_tracer(name: str = "ai-chat-instrumentation") -> trace.Tracer:
    """
    Get a tracer instance for creating spans.
    
    Args:
        name: Name of the tracer (usually your module name)
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def shutdown_instrumentation():
    """
    Gracefully shutdown instrumentation.
    
    Call this when your application is shutting down to ensure
    all telemetry data is flushed.
    """
    # Flush Sentry
    sentry_sdk.flush(timeout=2.0)
    
    # Shutdown OpenTelemetry
    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, 'shutdown'):
        tracer_provider.shutdown()
    
    print("✅ Instrumentation shutdown complete")


# Example configuration for different environments

def init_development():
    """Initialize with development settings."""
    init_hybrid_instrumentation(
        service_name="ai-chat-service",
        service_version="dev",
        environment="development",
        enable_logging=True,
    )


def init_production():
    """Initialize with production settings."""
    init_hybrid_instrumentation(
        service_name="ai-chat-service",
        service_version=os.getenv("APP_VERSION", "1.0.0"),
        environment="production",
        enable_logging=True,
    )


if __name__ == "__main__":
    # Test initialization
    init_development()
    print("\nConfiguration test successful!")
    print("\nTo use in your application:")
    print("  from hybrid_config import init_hybrid_instrumentation")
    print("  init_hybrid_instrumentation()")
    shutdown_instrumentation()


