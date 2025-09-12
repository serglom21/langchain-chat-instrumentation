"""Sentry configuration and instrumentation setup."""
import time
from typing import Any, Dict, Optional
import sentry_sdk
from sentry_sdk.tracing import Span
from sentry_sdk.integrations.langchain import LangchainIntegration
from sentry_sdk.integrations.openai import OpenAIIntegration
from config import get_settings


def setup_sentry() -> None:
    """Initialize Sentry with custom instrumentation."""
    settings = get_settings()
    
    if not settings.sentry_dsn:
        print("Warning: SENTRY_DSN not provided. Sentry instrumentation will be disabled.")
        return
    
    # Block Flask integration to prevent interference with span creation
    import sys
    if 'flask' in sys.modules:
        del sys.modules['flask']
    sys.modules['flask'] = None
    
    # Initialize Sentry with LangChain integration for AI Agent monitoring
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        send_default_pii=True,  # Enable PII for AI monitoring
        debug=True,  # Enable debug mode to troubleshoot span issues
        integrations=[
            LangchainIntegration(
                include_prompts=True,  # Include LLM inputs/outputs for AI monitoring
            ),
        ],
        disabled_integrations=[
            OpenAIIntegration(),  # Critical for correct token accounting
        ],
    )


def create_root_span(operation_name: str, data: Dict[str, Any] = None):
    """Create a root span for the workflow."""
    transaction = sentry_sdk.start_transaction(
        op=operation_name,
        name=f"Chat Workflow: {operation_name}"
    )
    
    # Add data as tags instead
    if data:
        for key, value in data.items():
            transaction.set_tag(key, value)
    
    return transaction


def instrument_node_operation(node_name: str, operation_data: Dict[str, Any]):
    """Instrument a node operation with custom attributes."""
    span = sentry_sdk.start_span(
        op="node_operation",
        name=f"Node: {node_name}"  # Use 'name' instead of 'description'
    )
    
    # Add custom attributes
    span.set_tag("node_name", node_name)
    span.set_tag("operation_type", operation_data.get("type", "unknown"))
    
    # Return the span as a context manager
    return span


def track_token_timing(start_time: float, first_token_time: Optional[float] = None, 
                      last_token_time: Optional[float] = None) -> None:
    """Track token timing metrics."""
    current_time = time.time()
    
    if first_token_time:
        time_to_first_token = first_token_time - start_time
        sentry_sdk.set_measurement("time_to_first_token", time_to_first_token, "second")
    
    if last_token_time:
        time_to_last_token = last_token_time - start_time
        sentry_sdk.set_measurement("time_to_last_token", time_to_last_token, "second")
    
    # Also set as tags for easier filtering
    if first_token_time:
        sentry_sdk.set_tag("time_to_first_token_ms", int((first_token_time - start_time) * 1000))
    if last_token_time:
        sentry_sdk.set_tag("time_to_last_token_ms", int((last_token_time - start_time) * 1000))


def add_custom_attributes(**kwargs) -> None:
    """Add custom attributes to the current span."""
    for key, value in kwargs.items():
        sentry_sdk.set_tag(key, value)
