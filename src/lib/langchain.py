"""
LangChain Ollama Integration

A wrapper that uses LangChain's Ollama integration with custom JSON parsing for structured outputs
and tool calling support
"""

from typing import Optional, List
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import BaseTool
import logging
import json
import re

# Configure logging
logger = logging.getLogger(__name__)


class LangChainOllamaWrapper:
    """
    LangChain-based Ollama wrapper that provides a clean interface
    while leveraging LangChain's Ollama integration.
    """
    
    def __init__(
        self,
        model: str = "gpt-oss:20b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.6,
        top_p: float = 0.95,
        timeout: int = 300,
        **kwargs
    ):
        """
        Initialize the LangChain Ollama wrapper.
        
        Args:
            model: Ollama model name
            base_url: Ollama API base URL
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            timeout: Request timeout in seconds
            **kwargs: Additional ChatOllama parameters
        """
        self.model_name = model
        self.base_url = base_url
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout
        
        # Initialize ChatOllama with LangChain
        self.llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            top_p=top_p,
            timeout=timeout,
            **kwargs
        )
        
        # Create output parser
        self.output_parser = StrOutputParser()
        
        # Create chains for different use cases
        self._setup_chains()

    def _create_llm(
        self,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        filter_keys: Optional[set] = None,
        **kwargs
    ) -> ChatOllama:
        """Create a ChatOllama with consistent defaults and optional kwargs filtering."""
        filtered_kwargs = kwargs
        if filter_keys:
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in filter_keys}

        return ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=temperature if temperature is not None else self.temperature,
            top_p=top_p if top_p is not None else self.top_p,
            timeout=self.timeout,
            **filtered_kwargs
        )

    def _build_messages(
        self,
        system_message: Optional[str],
        human_message: str
    ) -> List:
        """Build LangChain message list from optional system and required human content."""
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=human_message))
        return messages

    def _schema_info(self, schema_class: type) -> str:
        """Return JSON schema info for a Pydantic class or a fallback string."""
        if hasattr(schema_class, 'model_json_schema'):
            schema_dict = schema_class.model_json_schema()
            return json.dumps(schema_dict, indent=2)
        return f"Schema class: {schema_class.__name__}"

    def _build_schema_instruction(self, schema_class: type, variant: str) -> str:
        """Create JSON instruction text for two variants: 'final' and 'must'."""
        schema_info = self._schema_info(schema_class)
        if variant == 'final':
            return f"""
CRITICAL: Based on the conversation above, provide your final answer as valid JSON that matches this schema.
ALL fields in the schema are REQUIRED. Do not omit any fields.

Schema:
{schema_info}

**CRITICAL: Response Format Requirements:**
- Return ONLY the JSON data object, NOT the schema definition
- Your response must be valid JSON that matches the schema above
- Do NOT include any schema definitions, descriptions, or metadata
- Do NOT wrap your response in markdown code blocks
- Do NOT include keys like "properties", "required", "type", "title", "description", or "$schema"
- The response must be parseable JSON that directly matches the required fields
- Include ALL fields from the schema in your response
- Each field must have a value (no null or undefined)
- Output only the JSON object, no additional text or explanation
- Ensure the JSON is properly formatted and valid
"""
        # default to 'must' variant
        return f"""
CRITICAL: You must respond with valid JSON that matches the following schema.
ALL fields in the schema are REQUIRED. Do not omit any fields.

Schema:
{schema_info}

**CRITICAL: Response Format Requirements:**
- Return ONLY the JSON data object, NOT the schema definition
- Your response must be valid JSON that matches the schema above
- Do NOT include any schema definitions, descriptions, or metadata
- Do NOT wrap your response in markdown code blocks
- Do NOT include keys like "properties", "required", "type", "title", "description", or "$schema"
- The response must be parseable JSON that directly matches the required fields
- Include ALL fields from the schema in your response
- Each field must have a value (no null or undefined)
- Output only the JSON object, no additional text or explanation
- Ensure the JSON is properly formatted and valid
"""

    def _run_tool_loop(
        self,
        llm_with_tools,
        messages: List,
        tools: Optional[List[BaseTool]],
        max_iterations: int,
        return_text_when_no_tools: bool,
    ):
        """Run a standardized tool-calling loop. Returns (final_text_or_None, messages)."""
        for iteration in range(max_iterations):
            logger.info(f"Iteration {iteration + 1}: Getting response from model")

            response = llm_with_tools.invoke(messages)

            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"Iteration {iteration + 1}: Found {len(response.tool_calls)} tool calls")

                messages.append(AIMessage(
                    content=response.content or "",
                    tool_calls=response.tool_calls
                ))

                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    tool = next((t for t in tools if t.name == tool_name), None)
                    if tool:
                        try:
                            logger.info(f"Executing tool: {tool_name}")
                            tool_result = tool.invoke(tool_args)
                            messages.append(ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_call['id']
                            ))
                            logger.info(f"Tool {tool_name} executed successfully")
                        except Exception as e:
                            logger.error(f"Tool execution failed for {tool_name}: {e}")
                            messages.append(ToolMessage(
                                content=f"Error executing tool {tool_name}: {str(e)}",
                                tool_call_id=tool_call['id']
                            ))
                    else:
                        logger.error(f"Tool {tool_name} not found")
                        messages.append(ToolMessage(
                            content=f"Tool {tool_name} not available",
                            tool_call_id=tool_call['id']
                        ))
            else:
                logger.info(f"Iteration {iteration + 1}: Final response" if return_text_when_no_tools else f"Iteration {iteration + 1}: Proceed to structured output")
                if return_text_when_no_tools:
                    messages.append(AIMessage(content=response.content))
                    final_response = messages[-1].content if messages else ""
                    return final_response, messages
                return None, messages

        logger.warning("Reached maximum iterations without finalizing tool loop")
        return None, messages

    def _parse_json_response(self, response_text: str, schema_class: type):
        """
        Parse JSON response with fallback handling.
        Returns parsed object or None if parsing fails.
        """
        try:
            # First try direct JSON parsing
            data = json.loads(response_text.strip())
            # Try to create the schema object
            return schema_class(**data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Direct JSON parsing failed: {e}")

            # Fallback: try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1).strip())
                    return schema_class(**data)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    logger.warning(f"JSON code block parsing failed: {e}")

            # Final fallback: return None
            logger.error(f"All JSON parsing attempts failed for schema {schema_class.__name__}")
            return None

    def _setup_chains(self):
        """Setup LangChain runnable chains for different use cases."""
        # Basic generation chain
        self.generation_chain = self.llm | self.output_parser
        
        # Chat chain with system prompt support
        self.chat_chain = self._create_chat_chain()
    
    def _create_chat_chain(self):
        """Create a chat chain that handles system prompts."""
        def format_messages(data):
            messages = []
            if data.get("system_prompt"):
                messages.append(SystemMessage(content=data["system_prompt"]))
            messages.append(HumanMessage(content=data["message"]))
            return messages
        
        return RunnableLambda(format_messages) | self.llm | self.output_parser
    
    def generate(
        self,
        prompt: Optional[str] = None,
        human_message: Optional[str] = None,
        system_message: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        schema_class: Optional[type] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ):
        """
        Unified generate method supporting basic text, tool-enabled, and structured output generation.
        Structured outputs via format parameter, tool calling via tools parameter.

        Args:
            prompt: Input text prompt (used as human message)
            human_message: Human message content
            system_message: Optional system prompt/instruction
            tools: Optional list of LangChain tools for function calling
            schema_class: Optional Pydantic model class for structured output
            temperature: Sampling temperature (set to 0 for structured outputs)
            top_p: Top-p sampling parameter
            **kwargs: Additional generation parameters

        Returns:
            Generated text string or structured object (depending on schema_class)
        """
        try:
            message = human_message or prompt
            if not message:
                raise ValueError("Either prompt or human_message must be provided")

            # Route to appropriate generation method based on parameters
            if tools is not None and schema_class is not None:
                # Combined tool calling with structured final output
                return self._generate_with_tools_and_structure(
                    system_message=system_message,
                    human_message=message,
                    tools=tools,
                    schema_class=schema_class,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs
                )
            elif tools is not None:
                # Tool-enabled generation only
                return self._generate_with_tools(
                    system_message=system_message,
                    human_message=message,
                    tools=tools,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs
                )
            elif schema_class is not None:
                # Structured output generation using Ollama's format parameter
                return self._generate_structured(
                    schema_class=schema_class,
                    system_message=system_message,
                    human_message=message,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs
                )
            else:
                # Basic text generation
                return self._generate_basic(
                    prompt=message,
                    system_message=system_message,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs
                )

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    def _generate_basic(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Basic text generation with optional system message support.
        """
        try:
            # Create LLM instance with custom parameters if needed
            if temperature is not None or top_p is not None or kwargs or system_message:
                temp_llm = self._create_llm(temperature=temperature, top_p=top_p, **kwargs)

                if system_message:
                    def format_messages(data):
                        messages = []
                        if data.get("system_prompt"):
                            messages.append(SystemMessage(content=data["system_prompt"]))
                        messages.append(HumanMessage(content=data["message"]))
                        return messages

                    chain = RunnableLambda(format_messages) | temp_llm | self.output_parser
                    result = chain.invoke({"system_prompt": system_message, "message": prompt})
                else:
                    chain = temp_llm | self.output_parser
                    result = chain.invoke(prompt)
            else:
                chain = self.generation_chain
                result = chain.invoke(prompt)

            logger.info(f"Generated text length: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"Basic text generation failed: {e}")
            raise

    def _generate_with_tools(
        self,
        system_message: Optional[str] = None,
        human_message: str = "",
        tools: Optional[List[BaseTool]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ):
        """
        Tool-enabled generation using Ollama's tools parameter.
        Uses LangChain's bind_tools which internally uses Ollama's tools parameter.
        """
        try:
            llm = self._create_llm(temperature=temperature, top_p=top_p, **kwargs)

            llm_with_tools = llm.bind_tools(tools) if tools else llm

            messages = self._build_messages(system_message, human_message)

            logger.info(f"Generating with tool support using Ollama tools parameter. Tools: {len(tools) if tools else 0}")

            max_iterations = kwargs.get('max_tool_iterations', 5)

            final_text, messages = self._run_tool_loop(
                llm_with_tools=llm_with_tools,
                messages=messages,
                tools=tools,
                max_iterations=max_iterations,
                return_text_when_no_tools=True,
            )

            final_response = final_text or ""
            logger.info(f"Tool generation completed. Final response length: {len(final_response) if isinstance(final_response, str) else 'N/A'}")
            return final_response

        except Exception as e:
            logger.error(f"Tool-enabled generation failed: {e}")
            raise

    def _generate_with_tools_and_structure(
        self,
        system_message: Optional[str] = None,
        human_message: str = "",
        tools: Optional[List[BaseTool]] = None,
        schema_class: Optional[type] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ):
        """
        Combined tool calling with structured final output.
        Uses tools during reasoning, then uses Ollama's structured output for the final response.
        """
        try:
            effective_temperature = temperature if temperature is not None else 0.0

            llm = self._create_llm(temperature=effective_temperature, top_p=top_p, **kwargs)
            llm_with_tools = llm.bind_tools(tools) if tools else llm

            messages = self._build_messages(system_message, human_message)

            logger.info(f"Generating with tools + structured output. Tools: {len(tools) if tools else 0}, Schema: {schema_class.__name__ if schema_class else 'None'}")

            max_iterations = kwargs.get('max_tool_iterations', 5)

            final_text, messages = self._run_tool_loop(
                llm_with_tools=llm_with_tools,
                messages=messages,
                tools=tools,
                max_iterations=max_iterations,
                return_text_when_no_tools=False,
            )

            # After tool loop, request structured JSON as final output
            json_instruction = self._build_schema_instruction(schema_class, variant='final')
            messages.append(SystemMessage(content=json_instruction))

            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            final_response = self._parse_json_response(response_text, schema_class)
            return final_response

        except Exception as e:
            logger.error(f"Combined tool + structured generation failed: {e}")
            raise

    def _generate_structured(
        self,
        schema_class,
        system_message: Optional[str] = None,
        human_message: str = "",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ):
        """
        Structured output generation using custom JSON parsing.
        Instructs the model to output JSON and parses the response.
        """
        try:
            effective_temperature = temperature if temperature is not None else 0.0

            # Filter kwargs like previous implementation did for certain keys
            filter_keys = {'max_length', 'temperature', 'top_p'}
            llm = self._create_llm(
                temperature=effective_temperature,
                top_p=top_p,
                filter_keys=filter_keys,
                **kwargs
            )

            json_instruction = self._build_schema_instruction(schema_class, variant='must')
            enhanced_system = system_message + "\n\n" + json_instruction if system_message else json_instruction

            messages = self._build_messages(enhanced_system, human_message)

            logger.info(f"Generating structured output with schema {schema_class.__name__}")

            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)

            result = self._parse_json_response(response_text, schema_class)
            return result

        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            raise
