"""StateGraph workflow definition for the chat service."""
import sentry_sdk
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from chat_nodes import ChatNodes
from sentry_config import create_root_span


def create_instrumented_node(node_func, node_name: str):
    """Create an instrumented node function with Sentry spans."""
    def instrumented_node(state: Dict[str, Any]) -> Dict[str, Any]:
        # The node function will create its own spans within the transaction context
        # We just need to execute it and handle errors
        try:
            result = node_func(state)
            return result
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise
    
    return instrumented_node


class ChatStateGraph:
    """StateGraph implementation for chat workflow."""
    
    def __init__(self, openai_api_key: str):
        """Initialize the StateGraph with nodes and edges."""
        self.chat_nodes = ChatNodes(openai_api_key)
        self.graph = self._build_graph()
        
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
        
        # Add simple linear flow first to test
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
        """Process a chat message through the StateGraph workflow."""
        # DON'T create a new transaction - work within existing transaction context
        # The transaction should be created by the caller (e.g., API endpoint)
        
        try:
            # Prepare initial state
            initial_state = {
                "user_input": user_input,
                "conversation_history": conversation_history or [],
                "error": None
            }
            
            # Run the workflow WITHIN the existing transaction context
            # This ensures all node spans are created within the current transaction
            with sentry_sdk.start_span(
                op="workflow.execution",
                name="LangGraph Workflow Execution"
            ) as workflow_span:
                workflow_span.set_data("initial_state_keys", list(initial_state.keys()))
                workflow_span.set_data("user_input_length", len(user_input))
                
                # Execute the graph - nodes will create spans within this context
                result = self.graph.invoke(initial_state)
                
                workflow_span.set_data("result_keys", list(result.keys()) if result else [])
                workflow_span.set_data("execution_successful", True)
                
                # Add token timing metrics to workflow span
                if result and "token_timing" in result:
                    token_timing = result["token_timing"]
                    if "time_to_first_token_ms" in token_timing:
                        workflow_span.set_data("time_to_first_token_ms", token_timing["time_to_first_token_ms"])
                    if "time_to_last_token_ms" in token_timing:
                        workflow_span.set_data("time_to_last_token_ms", token_timing["time_to_last_token_ms"])
                    
                    # Add custom attributes for easy querying
                    sentry_sdk.set_tag("time_to_first_token_ms", token_timing.get("time_to_first_token_ms", "N/A"))
                    sentry_sdk.set_tag("time_to_last_token_ms", token_timing.get("time_to_last_token_ms", "N/A"))
            
            # Add workflow completion attributes
            sentry_sdk.set_tag("workflow_completed", True)
            if result:
                sentry_sdk.set_tag("nodes_executed", len(result))
            else:
                sentry_sdk.set_tag("nodes_executed", 0)
                sentry_sdk.set_tag("workflow_error", "No result returned")
            
            # DON'T finish transaction - let the caller handle it
            return result if result else initial_state
            
        except Exception as e:
            # Handle workflow-level errors
            sentry_sdk.capture_exception(e)
            sentry_sdk.set_tag("workflow_error", True)
            sentry_sdk.set_tag("error_type", type(e).__name__)
            
            # DON'T finish transaction - let the caller handle it
            
            # Return error state
            return {
                "error": str(e),
                "processed_response": "I apologize, but I encountered an error processing your request. Please try again.",
                "conversation_history": conversation_history or []
            }
