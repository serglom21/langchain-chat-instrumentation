"""OpenTelemetry configuration with Sentry OTLP exporter."""
import os
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.semconv.resource import ResourceAttributes
from config import get_settings


# Global tracer instance
_tracer: Optional[trace.Tracer] = None
_instrumented: bool = False


def setup_opentelemetry() -> trace.Tracer:
    """
    Initialize OpenTelemetry with Sentry OTLP exporter.
    
    This replaces the Sentry SDK setup with native OpenTelemetry instrumentation
    that sends data to Sentry via OTLP protocol.
    
    Returns:
        Tracer instance for creating spans
    """
    global _tracer, _instrumented
    
    if _tracer is not None:
        return _tracer
    
    settings = get_settings()
    
    # Sentry OTLP endpoint configuration
    # Format: https://o{org_id}.ingest.{region}.sentry.io/api/{project_id}/integration/otlp/v1/traces
    sentry_otlp_endpoint = "https://o88872.ingest.us.sentry.io/api/4509997697073152/integration/otlp/v1/traces"
    sentry_auth_header = "sentry sentry_key=691b07f94dbbca9171ae9995b25dc778"
    
    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: "langchain-chat-instrumentation",
        SERVICE_VERSION: "1.0.0",
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.sentry_environment,
        "service.namespace": "ai-chat",
        "telemetry.sdk.language": "python",
    })
    
    # Create TracerProvider with resource
    provider = TracerProvider(resource=resource)
    
    # Configure OTLP exporter for Sentry
    otlp_exporter = OTLPSpanExporter(
        endpoint=sentry_otlp_endpoint,
        headers={
            "x-sentry-auth": sentry_auth_header,
            "Content-Type": "application/json",
        },
    )
    
    # Add BatchSpanProcessor to export spans in batches
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    
    # Instrument HTTP clients for OpenAI API calls (if not already done)
    if not _instrumented:
        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            RequestsInstrumentor().instrument()
            print("✅ Instrumented requests library for HTTP client spans")
        except Exception as e:
            print(f"⚠️  Could not instrument requests: {e}")
        
        try:
            from opentelemetry.instrumentation.httpx import HTTPXInstrumentor
            HTTPXInstrumentor().instrument()
            print("✅ Instrumented httpx library for HTTP client spans")
        except Exception as e:
            print(f"⚠️  Could not instrument httpx: {e}")
        
        _instrumented = True
    
    # Create and cache tracer
    _tracer = trace.get_tracer(
        instrumenting_module_name="langchain_chat_instrumentation",
        instrumenting_library_version="1.0.0",
    )
    
    print("✅ OpenTelemetry initialized with Sentry OTLP exporter")
    print(f"   Service: langchain-chat-instrumentation")
    print(f"   Environment: {settings.sentry_environment}")
    print(f"   Endpoint: {sentry_otlp_endpoint}")
    print("   All traces will be sent to Sentry via OTLP protocol")
    
    return _tracer


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance.
    
    Returns:
        Tracer instance for creating spans
    """
    global _tracer
    if _tracer is None:
        return setup_opentelemetry()
    return _tracer


def shutdown_opentelemetry():
    """Shutdown OpenTelemetry and flush all pending spans."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, 'shutdown'):
        provider.shutdown()
        print("✅ OpenTelemetry shutdown complete - all spans flushed")


