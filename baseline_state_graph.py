"""
Baseline StateGraph WITHOUT custom Sentry instrumentation.

This shows what the workflow looks like with ONLY Sentry's
auto-instrumentation - no manual spans or transactions.
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from baseline_chat_nodes import BaselineChatNodes


class BaselineChatStateGraph:
    """
    StateGraph implementation WITHOUT custom Sentry instrumentation.
    
    This relies entirely on Sentry's auto-instrumentation to see
    what gets captured automatically.
    """
    
    def __init__(self, openai_api_key: str):
        """Initialize the StateGraph with nodes and edges."""
        self.chat_nodes = BaselineChatNodes(openai_api_key)
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the StateGraph with nodes and edges - NO custom instrumentation."""
        workflow = StateGraph(Dict[str, Any])
        
        # Add nodes - just the plain functions, no instrumentation wrappers
        workflow.add_node("input_validation", self.chat_nodes.input_validation_node)
        workflow.add_node("context_preparation", self.chat_nodes.context_preparation_node)
        workflow.add_node("llm_generation", self.chat_nodes.llm_generation_node)
        workflow.add_node("response_processing", self.chat_nodes.response_processing_node)
        workflow.add_node("conversation_update", self.chat_nodes.conversation_update_node)
        
        # Set the entry point
        workflow.set_entry_point("input_validation")
        
        # Add edges
        workflow.add_edge("input_validation", "context_preparation")
        workflow.add_edge("context_preparation", "llm_generation")
        workflow.add_edge("llm_generation", "response_processing")
        workflow.add_edge("response_processing", "conversation_update")
        workflow.add_edge("conversation_update", END)
        
        return workflow.compile()
    
    def process_chat(self, user_input: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a chat message - NO custom Sentry spans.
        
        This just runs the workflow and lets Sentry's auto-instrumentation
        capture whatever it can automatically.
        """
        try:
            initial_state = {
                "user_input": user_input,
                "conversation_history": conversation_history or [],
                "error": None
            }
            
            # Just run the graph - no manual transaction or span creation
            result = self.graph.invoke(initial_state)
            
            return result if result else initial_state
            
        except Exception as e:
            # Basic error handling - no custom Sentry instrumentation
            return {
                "error": str(e),
                "processed_response": "I apologize, but I encountered an error processing your request. Please try again.",
                "conversation_history": conversation_history or []
            }



