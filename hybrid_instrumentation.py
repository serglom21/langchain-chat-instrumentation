"""
Hybrid OpenTelemetry + Sentry SDK instrumentation.

This module provides instrumentation that uses:
- OpenTelemetry for distributed tracing and spans
- Sentry SDK for error reporting and issue tracking

Errors captured by Sentry will be linked to OTel spans using trace context.
"""

import time
from typing import Any, Dict, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.semconv.trace import SpanAttributes
import sentry_sdk
from sentry_sdk import Hub


def get_otel_span_context() -> Optional[Dict[str, str]]:
    """
    Extract OpenTelemetry span context for linking to Sentry.
    
    Returns dict with trace_id, span_id, and parent_span_id if available.
    """
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return None
    
    span_context = span.get_span_context()
    if not span_context.is_valid:
        return None
    
    # Format trace and span IDs as hex strings (32 and 16 chars respectively)
    return {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
        "trace_flags": format(span_context.trace_flags, "02x"),
    }


def capture_exception_with_span_context(
    exception: Exception,
    level: str = "error",
    tags: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Capture an exception with Sentry SDK and link it to the current OTel span.
    
    This is the recommended way to report errors when using hybrid instrumentation.
    The error will appear in Sentry with full context and be linked to your OTel trace.
    
    Args:
        exception: The exception to capture
        level: Severity level (error, warning, info)
        tags: Additional tags for Sentry
        extra: Additional context data
        
    Returns:
        Event ID from Sentry (or None if not sent)
        
    Example:
        try:
            risky_operation()
        except Exception as e:
            capture_exception_with_span_context(
                e,
                tags={"operation": "risky_operation"},
                extra={"user_id": user_id}
            )
            raise
    """
    # Get OTel span context
    otel_context = get_otel_span_context()
    
    with sentry_sdk.push_scope() as scope:
        # Set level
        scope.level = level
        
        # Link to OpenTelemetry trace
        if otel_context:
            # Add OTel trace ID as tags for searching
            # The 'trace' tag creates a searchable/clickable link in Sentry UI
            scope.set_tag("trace", otel_context["trace_id"])
            scope.set_tag("trace.id", otel_context["trace_id"])
            scope.set_tag("span.id", otel_context["span_id"])
            
            # Also add with otel prefix for clarity
            scope.set_tag("otel.trace_id", otel_context["trace_id"])
            scope.set_tag("otel.span_id", otel_context["span_id"])
            
            # Add full OpenTelemetry context
            scope.set_context("opentelemetry", {
                "trace_id": otel_context["trace_id"],
                "span_id": otel_context["span_id"],
                "trace_flags": otel_context["trace_flags"],
            })
        
        # Add custom tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        # Add extra context
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        
        # Capture the exception
        event_id = sentry_sdk.capture_exception(exception)
        
    # Also record in OTel span (as attributes, since events aren't supported)
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("error.type", type(exception).__name__)
        span.set_attribute("error.message", str(exception))
        span.set_attribute("error.sentry_event_id", event_id or "none")
        span.set_status(Status(StatusCode.ERROR, str(exception)))
    
    return event_id


def capture_message_with_span_context(
    message: str,
    level: str = "info",
    tags: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Capture a message with Sentry SDK and link it to the current OTel span.
    
    Useful for logging important events that aren't errors.
    
    Args:
        message: The message to capture
        level: Severity level (info, warning, error)
        tags: Additional tags for Sentry
        extra: Additional context data
        
    Returns:
        Event ID from Sentry (or None if not sent)
    """
    otel_context = get_otel_span_context()
    
    with sentry_sdk.push_scope() as scope:
        scope.level = level
        
        if otel_context:
            scope.set_tag("otel.trace_id", otel_context["trace_id"])
            scope.set_tag("otel.span_id", otel_context["span_id"])
            scope.set_context("opentelemetry", otel_context)
        
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        
        event_id = sentry_sdk.capture_message(message, level=level)
    
    return event_id


def instrument_node(node_name: str, operation_type: str = "processing"):
    """
    Decorator to instrument node methods with hybrid OTel + Sentry instrumentation.
    
    - Creates OTel spans for distributed tracing
    - Reports errors to Sentry with span context
    - Links errors between both systems
    
    Args:
        node_name: Name of the node being instrumented
        operation_type: Type of operation (validation, processing, generation, etc.)
    
    Example:
        @instrument_node("input_validation", "validation")
        def input_validation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
            # Your node logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, state: Dict[str, Any]) -> Dict[str, Any]:
            tracer = trace.get_tracer("hybrid-instrumentation")
            
            with tracer.start_as_current_span(
                name=f"Node: {node_name}",
                kind=trace.SpanKind.INTERNAL,
            ) as span:
                # Set node attributes
                span.set_attribute("node.name", node_name)
                span.set_attribute("node.operation_type", operation_type)
                span.set_attribute("workflow.step", node_name)
                
                # Also set Sentry transaction name for better grouping
                with sentry_sdk.configure_scope() as scope:
                    scope.set_transaction_name(f"Node: {node_name}")
                    scope.set_tag("node.name", node_name)
                    scope.set_tag("operation_type", operation_type)
                
                try:
                    result = func(self, state)
                    
                    # Mark as successful
                    span.set_attribute("execution.successful", True)
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record in both OTel and Sentry
                    span.set_attribute("execution.successful", False)
                    
                    # Capture with Sentry (linked to OTel span)
                    capture_exception_with_span_context(
                        e,
                        tags={
                            "node_name": node_name,
                            "operation_type": operation_type,
                        },
                        extra={
                            "state_keys": list(state.keys()) if state else [],
                        }
                    )
                    
                    raise
        
        return wrapper
    return decorator


@contextmanager
def create_span(
    name: str,
    operation: str = "internal",
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    capture_errors_to_sentry: bool = True,
):
    """
    Context manager to create a custom span with hybrid instrumentation.
    
    Creates both an OTel span and a Sentry transaction/span.
    Errors are automatically captured by Sentry and linked to the OTel span.
    
    Args:
        name: Name of the span
        operation: Operation type (e.g., "ai.chat", "workflow.execution")
        attributes: Optional dictionary of attributes to set on the span
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER)
        capture_errors_to_sentry: Whether to automatically capture errors to Sentry
    
    Example:
        with create_span("LLM Generation", "ai.chat") as span:
            span.set_attribute("model", "gpt-3.5-turbo")
            response = llm.invoke(messages)
    """
    tracer = trace.get_tracer("hybrid-instrumentation")
    
    with tracer.start_as_current_span(
        name=name,
        kind=kind,
    ) as span:
        # Set operation as an attribute
        span.set_attribute("operation", operation)
        
        # Set additional attributes if provided
        if attributes:
            for key, value in attributes.items():
                set_span_attribute(span, key, value)
        
        # Configure Sentry scope
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("operation", operation)
            if attributes:
                for key, value in attributes.items():
                    if isinstance(value, (str, int, float, bool)):
                        scope.set_tag(key, value)
        
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            # Capture to Sentry with span context
            if capture_errors_to_sentry:
                capture_exception_with_span_context(
                    e,
                    tags={"span_name": name, "operation": operation},
                )
            
            # Also set OTel span status
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.set_status(Status(StatusCode.ERROR, str(e)))
            
            raise


def set_span_attribute(span: Optional[Span], key: str, value: Any) -> None:
    """
    Set an attribute on a span with type handling.
    
    OpenTelemetry attributes must be str, bool, int, float, or sequences thereof.
    This helper handles type conversion.
    
    Args:
        span: The span to set the attribute on (can be None)
        key: Attribute key
        value: Attribute value (will be converted to appropriate type)
    """
    if span is None or not span.is_recording():
        return
    
    # Handle different types
    if value is None:
        span.set_attribute(key, "null")
    elif isinstance(value, (str, bool, int, float)):
        span.set_attribute(key, value)
    elif isinstance(value, (list, tuple)):
        # Convert to list of strings
        span.set_attribute(key, [str(v) for v in value])
    elif isinstance(value, dict):
        # For dicts, convert to JSON string or set individual keys
        import json
        try:
            span.set_attribute(key, json.dumps(value))
        except (TypeError, ValueError):
            span.set_attribute(key, str(value))
    else:
        span.set_attribute(key, str(value))


def add_span_attributes(**kwargs) -> None:
    """
    Add attributes to the current active span (both OTel and Sentry).
    
    Args:
        **kwargs: Key-value pairs to add as attributes
    
    Example:
        add_span_attributes(
            input_length=len(user_input),
            word_count=len(user_input.split())
        )
    """
    # Add to OTel span
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in kwargs.items():
            set_span_attribute(span, key, value)
    
    # Also add to Sentry scope as tags
    with sentry_sdk.configure_scope() as scope:
        for key, value in kwargs.items():
            if isinstance(value, (str, int, float, bool)):
                scope.set_tag(key, value)
            else:
                scope.set_extra(key, value)


def add_span_annotation(
    message: str,
    attributes: Optional[Dict[str, Any]] = None,
    level: str = "info"
) -> None:
    """
    Add an annotation/event to the current span.
    
    Since Sentry OTLP doesn't support span events, this:
    1. Stores it as span attributes in OTel (with timestamp)
    2. Optionally captures as breadcrumb in Sentry
    
    Args:
        message: Annotation message
        attributes: Optional attributes for the annotation
        level: Severity level (info, warning, error)
    
    Example:
        add_span_annotation(
            "Cache hit",
            {"cache_key": key, "latency_saved_ms": 1400},
            level="info"
        )
    """
    timestamp = time.time()
    
    # Add to OTel span as attributes (since events aren't supported by Sentry OTLP)
    span = trace.get_current_span()
    if span and span.is_recording():
        # Create a unique key for this annotation
        annotation_key = f"annotation.{int(timestamp * 1000)}"
        span.set_attribute(f"{annotation_key}.message", message)
        span.set_attribute(f"{annotation_key}.timestamp", timestamp)
        
        if attributes:
            for key, value in attributes.items():
                set_span_attribute(span, f"{annotation_key}.{key}", value)
    
    # Also add as Sentry breadcrumb (these ARE supported)
    sentry_sdk.add_breadcrumb(
        category="annotation",
        message=message,
        level=level,
        data=attributes or {},
    )


def set_ai_attributes(
    span: Span,
    model: str,
    operation: str = "chat",
    provider: str = "openai",
    prompts: Optional[list] = None,
    response: Optional[str] = None,
    token_usage: Optional[Dict[str, int]] = None,
) -> None:
    """
    Set AI/LLM-specific attributes on a span following OpenTelemetry semantic conventions.
    
    Also sets corresponding Sentry tags and context.
    
    Args:
        span: The span to set attributes on
        model: Model name (e.g., "gpt-3.5-turbo")
        operation: Operation type (e.g., "chat", "completion")
        provider: AI provider (e.g., "openai", "anthropic")
        prompts: List of prompt strings
        response: Response text
        token_usage: Dictionary with prompt_tokens, completion_tokens, total_tokens
    """
    # Set AI semantic convention attributes in OTel
    span.set_attribute("gen_ai.system", provider)
    span.set_attribute("gen_ai.operation.name", operation)
    span.set_attribute("gen_ai.request.model", model)
    
    if prompts:
        span.set_attribute("gen_ai.prompt.count", len(prompts))
        # Store first prompt as attribute (truncated)
        if len(prompts) > 0:
            span.set_attribute("gen_ai.prompt.0", str(prompts[0])[:1000])
    
    if response:
        span.set_attribute("gen_ai.response", str(response)[:1000])
        span.set_attribute("gen_ai.response.length", len(response))
    
    if token_usage:
        span.set_attribute("gen_ai.usage.prompt_tokens", token_usage.get("prompt_tokens", 0))
        span.set_attribute("gen_ai.usage.completion_tokens", token_usage.get("completion_tokens", 0))
        span.set_attribute("gen_ai.usage.total_tokens", token_usage.get("total_tokens", 0))
    
    # Also set in Sentry for better visibility
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("ai.model", model)
        scope.set_tag("ai.provider", provider)
        scope.set_tag("ai.operation", operation)
        
        ai_context = {
            "model": model,
            "provider": provider,
            "operation": operation,
        }
        
        if token_usage:
            ai_context["token_usage"] = token_usage
            # Also set as measurements in Sentry
            sentry_sdk.set_measurement("ai.prompt_tokens", token_usage.get("prompt_tokens", 0))
            sentry_sdk.set_measurement("ai.completion_tokens", token_usage.get("completion_tokens", 0))
            sentry_sdk.set_measurement("ai.total_tokens", token_usage.get("total_tokens", 0))
        
        if prompts:
            ai_context["prompt_count"] = len(prompts)
        
        if response:
            ai_context["response_length"] = len(response)
        
        scope.set_context("ai", ai_context)


def track_timing_metric(
    metric_name: str,
    value_ms: float,
    attributes: Optional[Dict[str, Any]] = None
) -> None:
    """
    Track a timing metric in both OTel and Sentry.
    
    Args:
        metric_name: Name of the metric (e.g., "time_to_first_token")
        value_ms: Value in milliseconds
        attributes: Optional additional attributes
    
    Example:
        track_timing_metric("time_to_first_token", 100.5, {"model": "gpt-3.5-turbo"})
    """
    # Set in OTel span
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute(f"metric.{metric_name}_ms", value_ms)
        span.set_attribute(f"metric.{metric_name}_seconds", value_ms / 1000.0)
        
        if attributes:
            for key, value in attributes.items():
                set_span_attribute(span, f"{metric_name}.{key}", value)
    
    # Also set as Sentry measurement
    sentry_sdk.set_measurement(metric_name, value_ms, unit="millisecond")
    
    if attributes:
        with sentry_sdk.configure_scope() as scope:
            for key, value in attributes.items():
                if isinstance(value, (str, int, float, bool)):
                    scope.set_tag(f"{metric_name}.{key}", value)


