"""
Baseline chat nodes WITHOUT custom Sentry instrumentation.

This shows what the nodes look like with ONLY Sentry's auto-instrumentation.
No manual spans, no decorators, no custom callbacks - just plain code.
"""
import time
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage


class BaselineChatNodes:
    """Collection of chat operation nodes WITHOUT custom Sentry instrumentation."""
    
    def __init__(self, openai_api_key: str):
        # Simple response cache to avoid redundant calls
        self.response_cache = {}
        
        # Basic LLM configuration - NO custom callbacks
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model="gpt-3.5-turbo",
            temperature=0.7,
            streaming=True,
            max_retries=2,
            request_timeout=30,
            max_tokens=1000,
            model_kwargs={
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
        )
        # NO Sentry callback handler
    
    def input_validation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and preprocess user input - NO custom instrumentation."""
        user_input = state.get("user_input", "")
        
        if not user_input.strip():
            raise ValueError("User input cannot be empty")
        
        # Just return the validated state - no Sentry spans or attributes
        return {
            **state,
            "validated_input": user_input.strip(),
            "validation_timestamp": time.time()
        }
    
    def context_preparation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context and system prompt - NO custom instrumentation."""
        validated_input = state.get("validated_input", "")
        conversation_history = state.get("conversation_history", [])
        
        # Prepare system message
        system_prompt = """You are a helpful AI assistant. Provide clear, concise, and accurate responses. 
        If you don't know something, say so rather than making up information."""
        
        # Prepare messages
        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history
        for msg in conversation_history[-5:]:  # Keep last 5 messages for context
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current user input
        messages.append(HumanMessage(content=validated_input))
        
        # Just return the state - no Sentry instrumentation
        return {
            **state,
            "messages": messages,
            "context_prepared_at": time.time()
        }
    
    def llm_generation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using LLM - NO custom instrumentation."""
        messages = state.get("messages", [])
        
        try:
            # Simple caching for repeated queries
            cache_key = str([msg.content for msg in messages])
            if cache_key in self.response_cache:
                response = self.response_cache[cache_key]
            else:
                # Just call the LLM - NO custom spans, NO callbacks
                response = self.llm.invoke(messages)
                
                # Cache the response (limit cache size)
                if len(self.response_cache) < 10:
                    self.response_cache[cache_key] = response
            
            generated_text = response.content
            
            # Just return the result - no custom Sentry attributes
            return {
                **state,
                "generated_response": generated_text,
                "generation_timestamp": time.time()
            }
            
        except Exception as e:
            # Basic error handling - no custom Sentry capture
            raise
    
    def response_processing_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format the response - NO custom instrumentation."""
        generated_response = state.get("generated_response", "")
        
        # Basic response processing
        processed_response = generated_response.strip()
        
        # Add metadata
        response_metadata = {
            "processed_at": time.time(),
            "word_count": len(processed_response.split()),
            "character_count": len(processed_response)
        }
        
        # Just return the state - no Sentry instrumentation
        return {
            **state,
            "processed_response": processed_response,
            "response_metadata": response_metadata
        }
    
    def conversation_update_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Update conversation history - NO custom instrumentation."""
        user_input = state.get("validated_input", "")
        processed_response = state.get("processed_response", "")
        conversation_history = state.get("conversation_history", [])
        
        # Add new messages to history
        new_messages = [
            {"role": "user", "content": user_input, "timestamp": time.time()},
            {"role": "assistant", "content": processed_response, "timestamp": time.time()}
        ]
        
        updated_history = conversation_history + new_messages
        
        # Just return the state - no Sentry instrumentation
        return {
            **state,
            "conversation_history": updated_history,
            "conversation_updated_at": time.time()
        }
