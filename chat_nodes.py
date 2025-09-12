"""Chat service nodes for StateGraph operations."""
import time
import sentry_sdk
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.base import BaseCallbackHandler
from sentry_config import instrument_node_operation, track_token_timing, add_custom_attributes


class ComprehensiveSentryCallback(BaseCallbackHandler):
    """Comprehensive Sentry callback handler for full LangChain instrumentation."""
    
    def __init__(self):
        self.spans = {}  # Track spans by run_id
        self.start_times = {}
        self.token_counts = {}
        self.first_token_times = {}
    
    def _get_run_id(self, **kwargs) -> str:
        """Get unique run ID for tracking spans."""
        return kwargs.get('run_id', str(time.time()))
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts - create comprehensive Sentry span."""
        run_id = self._get_run_id(**kwargs)
        start_time = time.time()
        self.start_times[run_id] = start_time
        self.token_counts[run_id] = 0
        self.first_token_times[run_id] = None
        
        # Create comprehensive AI span
        span = sentry_sdk.start_span(
            op="ai.chat",
            description=f"LLM: {serialized.get('name', 'unknown')}",
        )
        
        # Set AI-specific attributes
        span.set_data("gen_ai.system", "openai")
        span.set_data("gen_ai.operation.name", "chat")
        span.set_data("gen_ai.model_name", serialized.get('name', 'unknown'))
        span.set_data("gen_ai.provider", "openai")
        span.set_data("gen_ai.request.prompts", prompts)
        span.set_data("gen_ai.request.prompt_count", len(prompts))
        
        # Add timing info
        span.set_data("start_time", start_time)
        
        self.spans[run_id] = span
        
        # Also add to current span context
        add_custom_attributes(
            llm_model=serialized.get('name', 'unknown'),
            prompt_count=len(prompts),
            llm_start_time=start_time
        )
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when a new token is generated."""
        run_id = self._get_run_id(**kwargs)
        
        if run_id in self.token_counts:
            if self.first_token_times[run_id] is None:
                self.first_token_times[run_id] = time.time()
                
                # Track time to first token
                if run_id in self.start_times:
                    time_to_first = self.first_token_times[run_id] - self.start_times[run_id]
                    if run_id in self.spans:
                        self.spans[run_id].set_data("gen_ai.response.time_to_first_token", time_to_first)
                        self.spans[run_id].set_data("time_to_first_token_ms", int(time_to_first * 1000))
            
            self.token_counts[run_id] += 1
    
    def on_llm_end(self, response: Any, **kwargs) -> None:
        """Called when LLM ends - finalize Sentry span with comprehensive data."""
        run_id = self._get_run_id(**kwargs)
        
        if run_id in self.spans:
            span = self.spans[run_id]
            end_time = time.time()
            
            # Calculate metrics
            total_duration = end_time - self.start_times.get(run_id, end_time)
            token_count = self.token_counts.get(run_id, 0)
            
            # Add comprehensive response data
            span.set_data("gen_ai.response.choices", [
                {
                    "message": {
                        "content": str(response),
                        "role": "assistant"
                    }
                }
            ])
            
            # Add token usage (estimated)
            prompt_tokens = sum(len(str(p).split()) for p in span.data.get("gen_ai.request.prompts", []))
            completion_tokens = token_count
            total_tokens = prompt_tokens + completion_tokens
            
            span.set_data("gen_ai.response.usage", {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            })
            
            # Add timing metrics
            span.set_data("gen_ai.response.total_duration", total_duration)
            span.set_data("total_duration_ms", int(total_duration * 1000))
            span.set_data("total_tokens", token_count)
            
            # Finish the span
            span.finish()
            
            # Clean up tracking
            del self.spans[run_id]
            del self.start_times[run_id]
            del self.token_counts[run_id]
            if run_id in self.first_token_times:
                del self.first_token_times[run_id]
        
        add_custom_attributes(
            llm_completion_time=time.time(),
            llm_successful=True
        )
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called when LLM encounters an error."""
        run_id = self._get_run_id(**kwargs)
        
        if run_id in self.spans:
            span = self.spans[run_id]
            span.set_data("gen_ai.error", str(error))
            span.set_data("gen_ai.response.successful", False)
            span.finish()
            
            # Clean up tracking
            del self.spans[run_id]
            if run_id in self.start_times:
                del self.start_times[run_id]
            if run_id in self.token_counts:
                del self.token_counts[run_id]
            if run_id in self.first_token_times:
                del self.first_token_times[run_id]
        
        add_custom_attributes(
            llm_successful=False,
            llm_error=type(error).__name__
        )
        
        sentry_sdk.capture_exception(error)
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Called when a chain starts - create chain span."""
        run_id = self._get_run_id(**kwargs)
        start_time = time.time()
        self.start_times[run_id] = start_time
        
        # Create chain span
        span = sentry_sdk.start_span(
            op="chain.execute",
            description=f"Chain: {serialized.get('name', 'unknown')}",
        )
        
        span.set_data("chain_name", serialized.get('name', 'unknown'))
        span.set_data("chain_inputs", inputs)
        span.set_data("start_time", start_time)
        
        self.spans[run_id] = span
        
        add_custom_attributes(
            chain_name=serialized.get('name', 'unknown'),
            chain_input_count=len(inputs)
        )
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Called when a chain ends - finalize chain span."""
        run_id = self._get_run_id(**kwargs)
        
        if run_id in self.spans:
            span = self.spans[run_id]
            end_time = time.time()
            
            total_duration = end_time - self.start_times.get(run_id, end_time)
            
            span.set_data("chain_outputs", outputs)
            span.set_data("chain_duration", total_duration)
            span.set_data("duration_ms", int(total_duration * 1000))
            
            span.finish()
            
            # Clean up tracking
            del self.spans[run_id]
            if run_id in self.start_times:
                del self.start_times[run_id]
        
        add_custom_attributes(
            chain_completion_time=time.time(),
            chain_successful=True
        )
    
    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Called when a chain encounters an error."""
        run_id = self._get_run_id(**kwargs)
        
        if run_id in self.spans:
            span = self.spans[run_id]
            span.set_data("chain_error", str(error))
            span.set_data("chain_successful", False)
            span.finish()
            
            # Clean up tracking
            del self.spans[run_id]
            if run_id in self.start_times:
                del self.start_times[run_id]
        
        add_custom_attributes(
            chain_successful=False,
            chain_error=type(error).__name__
        )
        
        sentry_sdk.capture_exception(error)


class ChatNodes:
    """Collection of chat operation nodes."""
    
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model="gpt-3.5-turbo",
            temperature=0.7,
            streaming=True
        )
        self.sentry_callback = ComprehensiveSentryCallback()
    
    def input_validation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and preprocess user input."""
        # Create span within transaction context
        with sentry_sdk.start_span(
            op="node_operation",
            name="Node: input_validation"
        ) as span:
            span.set_tag("node_name", "input_validation")
            span.set_tag("operation_type", "validation")
            
            user_input = state.get("user_input", "")
            
            if not user_input.strip():
                raise ValueError("User input cannot be empty")
            
            # Add validation attributes
            add_custom_attributes(
                input_length=len(user_input),
                has_question_mark="?" in user_input,
                word_count=len(user_input.split())
            )
            
            return {
                **state,
                "validated_input": user_input.strip(),
                "validation_timestamp": time.time()
            }
    
    def context_preparation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context and system prompt."""
        # Create span within transaction context
        with sentry_sdk.start_span(
            op="node_operation",
            name="Node: context_preparation"
        ) as span:
            span.set_tag("node_name", "context_preparation")
            span.set_tag("operation_type", "preprocessing")
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
            
            add_custom_attributes(
                context_messages_count=len(messages),
                history_length=len(conversation_history)
            )
            
            return {
                **state,
                "messages": messages,
                "context_prepared_at": time.time()
            }
    
    def llm_generation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using LLM with comprehensive instrumentation."""
        # Create span within transaction context
        with sentry_sdk.start_span(
            op="node_operation",
            name="Node: llm_generation"
        ) as span:
            span.set_tag("node_name", "llm_generation")
            span.set_tag("operation_type", "generation")
            messages = state.get("messages", [])
            
            try:
                # Create manual AI span to ensure proper AI instrumentation
                with sentry_sdk.start_span(
                    op="ai.chat",
                    name="LLM Generation with OpenAI GPT-3.5-turbo"  # Use 'name' instead of 'description'
                ) as ai_span:
                    ai_span.set_data("gen_ai.system", "openai")
                    ai_span.set_data("gen_ai.operation.name", "chat")
                    ai_span.set_data("gen_ai.model_name", "gpt-3.5-turbo")
                    ai_span.set_data("gen_ai.provider", "openai")
                    
                    # Generate response - Sentry LangChain integration handles instrumentation automatically
                    response = self.llm.invoke(messages)
                    
                    generated_text = response.content
                    
                    # Add response data to AI span
                    ai_span.set_data("gen_ai.response.choices", [
                        {
                            "message": {
                                "content": generated_text,
                                "role": "assistant"
                            }
                        }
                    ])
                    ai_span.set_data("gen_ai.response.usage", {
                        "completion_tokens": len(generated_text.split()),
                        "prompt_tokens": sum(len(str(msg).split()) for msg in messages),
                        "total_tokens": len(generated_text.split()) + sum(len(str(msg).split()) for msg in messages)
                    })
                
                add_custom_attributes(
                    response_length=len(generated_text),
                    generation_successful=True,
                    node_name="llm_generation"
                )
                
                return {
                    **state,
                    "generated_response": generated_text,
                    "generation_timestamp": time.time(),
                    "token_timing": {
                        "generation_completed": True,
                        "response_length": len(generated_text)
                    }
                }
                
            except Exception as e:
                # Add error to AI span if it exists
                if 'ai_span' in locals():
                    ai_span.set_data("gen_ai.error", str(e))
                    ai_span.set_data("gen_ai.response.successful", False)
                
                add_custom_attributes(
                    generation_successful=False,
                    error_type=type(e).__name__,
                    node_name="llm_generation"
                )
                sentry_sdk.capture_exception(e)
                raise
    
    def response_processing_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format the response."""
        # Create span within transaction context
        with sentry_sdk.start_span(
            op="node_operation",
            name="Node: response_processing"
        ) as span:
            span.set_tag("node_name", "response_processing")
            span.set_tag("operation_type", "postprocessing")
            generated_response = state.get("generated_response", "")
            
            # Basic response processing
            processed_response = generated_response.strip()
            
            # Add metadata
            response_metadata = {
                "processed_at": time.time(),
                "word_count": len(processed_response.split()),
                "character_count": len(processed_response)
            }
            
            add_custom_attributes(
                processed_response_length=len(processed_response),
                processing_successful=True
            )
            
            return {
                **state,
                "processed_response": processed_response,
                "response_metadata": response_metadata
            }
    
    def conversation_update_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Update conversation history."""
        # Create span within transaction context
        with sentry_sdk.start_span(
            op="node_operation",
            name="Node: conversation_update"
        ) as span:
            span.set_tag("node_name", "conversation_update")
            span.set_tag("operation_type", "state_update")
            user_input = state.get("validated_input", "")
            processed_response = state.get("processed_response", "")
            conversation_history = state.get("conversation_history", [])
            
            # Add new messages to history
            new_messages = [
                {"role": "user", "content": user_input, "timestamp": time.time()},
                {"role": "assistant", "content": processed_response, "timestamp": time.time()}
            ]
            
            updated_history = conversation_history + new_messages
            
            add_custom_attributes(
                conversation_length=len(updated_history),
                update_successful=True
            )
            
            return {
                **state,
                "conversation_history": updated_history,
                "conversation_updated_at": time.time()
            }
    
    def error_handling_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors and provide fallback response."""
        # Create span within transaction context
        with sentry_sdk.start_span(
            op="node_operation",
            name="Node: error_handling"
        ) as span:
            span.set_tag("node_name", "error_handling")
            span.set_tag("operation_type", "error_handling")
            error = state.get("error", None)
            
            if error:
                error_message = f"I apologize, but I encountered an error: {str(error)}. Please try again."
                
                add_custom_attributes(
                    error_handled=True,
                    error_type=type(error).__name__
                )
                
                return {
                    **state,
                    "processed_response": error_message,
                    "error_handled": True,
                    "error_handled_at": time.time()
                }
            
            return state

