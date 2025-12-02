"""OpenTelemetry instrumentation helpers for custom spans and attributes."""
import time
from typing import Any, Dict, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.semconv.trace import SpanAttributes
from otel.otel_config import get_tracer


def instrument_node(node_name: str, operation_type: str = "processing"):
    """
    Decorator to automatically instrument node methods with OpenTelemetry spans.
    
    This is the OpenTelemetry equivalent of the Sentry @instrument_node decorator.
    
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
            tracer = get_tracer()
            
            with tracer.start_as_current_span(
                name=f"Node: {node_name}",
                kind=trace.SpanKind.INTERNAL,
            ) as span:
                # Set node attributes
                span.set_attribute("node.name", node_name)
                span.set_attribute("node.operation_type", operation_type)
                span.set_attribute("workflow.step", node_name)
                
                try:
                    result = func(self, state)
                    
                    # Mark as successful
                    span.set_attribute("execution.successful", True)
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record exception details
                    span.set_attribute("execution.successful", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                    # Record exception in span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    raise
        
        return wrapper
    return decorator


@contextmanager
def create_span(
    name: str,
    operation: str = "internal",
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL
):
    """
    Context manager to create a custom span.
    
    This is the OpenTelemetry equivalent of sentry_sdk.start_span().
    
    Args:
        name: Name of the span
        operation: Operation type (e.g., "ai.chat", "workflow.execution")
        attributes: Optional dictionary of attributes to set on the span
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER)
    
    Example:
        with create_span("LLM Generation", "ai.chat") as span:
            span.set_attribute("model", "gpt-3.5-turbo")
            response = llm.invoke(messages)
    """
    tracer = get_tracer()
    
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
        
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.record_exception(e)
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
    Add attributes to the current active span.
    
    This is the OpenTelemetry equivalent of sentry_sdk.set_tag().
    
    Args:
        **kwargs: Key-value pairs to add as attributes
    
    Example:
        add_span_attributes(
            input_length=len(user_input),
            word_count=len(user_input.split())
        )
    """
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    
    for key, value in kwargs.items():
        set_span_attribute(span, key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.
    
    Events are timestamped annotations on a span.
    
    Args:
        name: Name of the event
        attributes: Optional attributes for the event
    
    Example:
        add_span_event("cache_hit", {"cache_key": key, "performance_gain": "1400ms"})
    """
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    
    if attributes:
        # Convert attributes to proper types
        converted_attrs = {}
        for key, value in attributes.items():
            if isinstance(value, (str, bool, int, float)):
                converted_attrs[key] = value
            else:
                converted_attrs[key] = str(value)
        span.add_event(name, attributes=converted_attrs)
    else:
        span.add_event(name)


def record_exception(exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Record an exception in the current span.
    
    This is the OpenTelemetry equivalent of sentry_sdk.capture_exception().
    
    Args:
        exception: The exception to record
        attributes: Optional additional attributes
    
    Example:
        try:
            risky_operation()
        except Exception as e:
            record_exception(e, {"operation": "risky_operation"})
            raise
    """
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    
    # Record the exception
    span.record_exception(exception)
    
    # Set error status
    span.set_status(Status(StatusCode.ERROR, str(exception)))
    
    # Add additional attributes if provided
    if attributes:
        for key, value in attributes.items():
            set_span_attribute(span, key, value)


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
    
    Args:
        span: The span to set attributes on
        model: Model name (e.g., "gpt-3.5-turbo")
        operation: Operation type (e.g., "chat", "completion")
        provider: AI provider (e.g., "openai", "anthropic")
        prompts: List of prompt strings
        response: Response text
        token_usage: Dictionary with prompt_tokens, completion_tokens, total_tokens
    
    Example:
        with create_span("LLM Call", "ai.chat") as span:
            set_ai_attributes(
                span,
                model="gpt-3.5-turbo",
                prompts=["Hello, world!"],
                token_usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            )
    """
    # Set AI semantic convention attributes
    span.set_attribute("gen_ai.system", provider)
    span.set_attribute("gen_ai.operation.name", operation)
    span.set_attribute("gen_ai.request.model", model)
    
    if prompts:
        span.set_attribute("gen_ai.prompt.count", len(prompts))
        # Store prompts as events to avoid attribute size limits
        for i, prompt in enumerate(prompts):
            span.add_event(f"gen_ai.prompt.{i}", {"content": str(prompt)[:1000]})  # Limit size
    
    if response:
        # Store response as event to avoid attribute size limits
        span.add_event("gen_ai.response", {"content": str(response)[:1000]})  # Limit size
        span.set_attribute("gen_ai.response.length", len(response))
    
    if token_usage:
        span.set_attribute("gen_ai.usage.prompt_tokens", token_usage.get("prompt_tokens", 0))
        span.set_attribute("gen_ai.usage.completion_tokens", token_usage.get("completion_tokens", 0))
        span.set_attribute("gen_ai.usage.total_tokens", token_usage.get("total_tokens", 0))


def track_timing_metric(
    metric_name: str,
    value_ms: float,
    attributes: Optional[Dict[str, Any]] = None
) -> None:
    """
    Track a timing metric as a span attribute.
    
    This is the OpenTelemetry equivalent of sentry_sdk.set_measurement().
    
    Args:
        metric_name: Name of the metric (e.g., "time_to_first_token")
        value_ms: Value in milliseconds
        attributes: Optional additional attributes
    
    Example:
        track_timing_metric("time_to_first_token", 100.5, {"model": "gpt-3.5-turbo"})
    """
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    
    # Set the metric as an attribute
    span.set_attribute(f"metric.{metric_name}_ms", value_ms)
    
    # Also set as seconds for compatibility
    span.set_attribute(f"metric.{metric_name}_seconds", value_ms / 1000.0)
    
    # Add additional attributes if provided
    if attributes:
        for key, value in attributes.items():
            set_span_attribute(span, f"{metric_name}.{key}", value)


