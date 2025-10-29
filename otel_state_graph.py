"""StateGraph workflow definition with OpenTelemetry instrumentation."""
from typing import Dict, Any, List
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from otel_chat_nodes import OtelChatNodes
from otel_instrumentation import (
    create_span,
    add_span_attributes,
    record_exception,
    track_timing_metric,
)
from otel_config import get_tracer


def create_instrumented_node(node_func, node_name: str):
    """
    Create an instrumented node function with OpenTelemetry spans.
    
    The node function is decorated with @instrument_node, so it handles its own instrumentation.
    We just need to execute it and handle any additional errors.
    """
    def instrumented_node(state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = node_func(state)
            return result
        except Exception as e:
            record_exception(e)
            raise
    
    return instrumented_node


class OtelChatStateGraph:
    """StateGraph implementation for chat workflow with OpenTelemetry instrumentation."""
    
    def __init__(self, openai_api_key: str):
        """Initialize the StateGraph with nodes and edges."""
        self.chat_nodes = OtelChatNodes(openai_api_key)
        self.graph = self._build_graph()
        self.tracer = get_tracer()
        
    def _build_graph(self) -> StateGraph:
        """Build the StateGraph with nodes and edges."""
        # Create a new StateGraph
        workflow = StateGraph(Dict[str, Any])
        
        # Add instrumented nodes to the graph
        workflow.add_node("input_validation", create_instrumented_node(
            self.chat_nodes.input_validation_node, "input_validation"
        ))
        workflow.add_node("context_preparation", create_instrumented_node(
            self.chat_nodes.context_preparation_node, "context_preparation"
        ))
        workflow.add_node("llm_generation", create_instrumented_node(
            self.chat_nodes.llm_generation_node, "llm_generation"
        ))
        workflow.add_node("response_processing", create_instrumented_node(
            self.chat_nodes.response_processing_node, "response_processing"
        ))
        workflow.add_node("conversation_update", create_instrumented_node(
            self.chat_nodes.conversation_update_node, "conversation_update"
        ))
        
        # Set the entry point
        workflow.set_entry_point("input_validation")
        
        # Add simple linear flow
        workflow.add_edge("input_validation", "context_preparation")
        workflow.add_edge("context_preparation", "llm_generation")
        workflow.add_edge("llm_generation", "response_processing")
        workflow.add_edge("response_processing", "conversation_update")
        workflow.add_edge("conversation_update", END)
        
        # Compile the graph
        return workflow.compile()
    
    def _should_handle_error(self, state: Dict[str, Any]) -> str:
        """Determine if we should handle an error or continue."""
        return "error" if state.get("error") else "continue"
    
    def process_chat(self, user_input: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a chat message through the StateGraph workflow with OpenTelemetry instrumentation.
        
        This method creates spans that mirror the Sentry instrumentation but use OpenTelemetry.
        """
        try:
            # Prepare initial state
            initial_state = {
                "user_input": user_input,
                "conversation_history": conversation_history or [],
                "error": None
            }
            
            # Run the workflow WITHIN the existing transaction/span context
            # This ensures all node spans are created within the current trace
            
            # Add LangGraph agent span (matches Sentry SDK's gen_ai.invoke_agent)
            with create_span(
                "invoke_agent LangGraph",
                "gen_ai.invoke_agent",
                kind=trace.SpanKind.INTERNAL
            ) as agent_span:
                agent_span.set_attribute("gen_ai.system", "langgraph")
                agent_span.set_attribute("gen_ai.operation.name", "invoke_agent")
                agent_span.set_attribute("agent.type", "state_graph")
                
                with create_span(
                    "LangGraph Workflow Execution",
                    "workflow.execution",
                    kind=trace.SpanKind.INTERNAL
                ) as workflow_span:
                    workflow_span.set_attribute("initial_state_keys", str(list(initial_state.keys())))
                    workflow_span.set_attribute("user_input_length", len(user_input))
                    
                    # Execute the graph - nodes will create spans within this context
                    with create_span(
                        "LangGraph Graph Invoke",
                        "workflow.langgraph_invoke",
                        kind=trace.SpanKind.INTERNAL
                    ) as graph_invoke_span:
                        graph_invoke_span.set_attribute("description", 
                            "LangGraph internal processing during graph.invoke()")
                        graph_invoke_span.set_attribute("state_keys", str(list(initial_state.keys())))
                        
                        result = self.graph.invoke(initial_state)
                        
                        graph_invoke_span.set_attribute("result_keys", str(list(result.keys())) if result else "[]")
                        graph_invoke_span.set_attribute("invoke_successful", True)
                    
                    workflow_span.set_attribute("result_keys", str(list(result.keys())) if result else "[]")
                    workflow_span.set_attribute("execution_successful", True)
                
                # Add token timing metrics to workflow span
                if result and "token_timing" in result:
                    token_timing = result["token_timing"]
                    
                    first_token_ms = token_timing.get("time_to_first_token_ms")
                    last_token_ms = token_timing.get("time_to_last_token_ms")
                    
                    if first_token_ms is not None:
                        workflow_span.set_attribute("time_to_first_token_ms", first_token_ms)
                        track_timing_metric("time_to_first_token", first_token_ms)
                    
                    if last_token_ms is not None:
                        workflow_span.set_attribute("time_to_last_token_ms", last_token_ms)
                        track_timing_metric("time_to_last_token", last_token_ms)
            
            # Add workflow completion attributes
            add_span_attributes(
                workflow_completed=True,
                nodes_executed=len(result) if result else 0
            )
            
            return result if result else initial_state
            
        except Exception as e:
            # Handle workflow-level errors
            record_exception(e)
            add_span_attributes(
                workflow_error=True,
                error_type=type(e).__name__
            )
            
            # Return error state
            return {
                "error": str(e),
                "processed_response": "I apologize, but I encountered an error processing your request. Please try again.",
                "conversation_history": conversation_history or []
            }


