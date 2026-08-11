"""
LLM Generation Engine

Stateless tool-calling loop, structured-output JSON parsing, and the four
generation strategies (basic / tools / structured / tools+structured) shared
by every LangChain chat-wrapper provider (ChatGPT, Ollama, ...).

Every method takes the pieces it needs (a `create_llm` factory, `output_parser`,
etc.) as explicit arguments rather than owning a model instance, so the engine
stays provider-agnostic and is reused by composition, not inheritance.
"""

import json
import logging
import re
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class GenerationEngine:
    """Generation strategies shared by every LangChain chat wrapper."""

    @staticmethod
    def build_messages(system_message: Optional[str], human_message: str) -> List:
        """Build LangChain message list from optional system and required human content."""
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=human_message))
        return messages

    @staticmethod
    def schema_info(schema_class: type) -> str:
        """Return JSON schema info for a Pydantic class or a fallback string."""
        if hasattr(schema_class, "model_json_schema"):
            schema_dict = schema_class.model_json_schema()
            return json.dumps(schema_dict, indent=2)
        return f"Schema class: {schema_class.__name__}"

    @staticmethod
    def build_schema_instruction(schema_class: type, variant: str) -> str:
        """Create JSON instruction text for two variants: 'final' and 'must'."""
        schema_info = GenerationEngine.schema_info(schema_class)
        lead = (
            "Based on the conversation above, provide your final answer as valid JSON that matches this schema."
            if variant == "final"
            else "You must respond with valid JSON that matches the following schema."
        )
        return f"""
CRITICAL: {lead}
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

    @staticmethod
    def _execute_tool_call(tool_call: dict, tools: List[BaseTool]) -> ToolMessage:
        """Invoke a single requested tool call and wrap the outcome as a ToolMessage."""
        tool_name = tool_call["name"]
        tool = next((t for t in tools if t.name == tool_name), None)
        if not tool:
            logger.error(f"Tool {tool_name} not found")
            return ToolMessage(
                content=f"Tool {tool_name} not available", tool_call_id=tool_call["id"]
            )

        try:
            logger.info(f"Executing tool: {tool_name}")
            tool_result = tool.invoke(tool_call["args"])
            logger.info(f"Tool {tool_name} executed successfully")
            return ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return ToolMessage(
                content=f"Error executing tool {tool_name}: {str(e)}",
                tool_call_id=tool_call["id"],
            )

    @staticmethod
    def run_tool_loop(
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

            if not (hasattr(response, "tool_calls") and response.tool_calls):
                logger.info(
                    f"Iteration {iteration + 1}: Final response"
                    if return_text_when_no_tools
                    else f"Iteration {iteration + 1}: Proceed to structured output"
                )
                if not return_text_when_no_tools:
                    return None, messages
                messages.append(AIMessage(content=response.content))
                return response.content, messages

            logger.info(
                f"Iteration {iteration + 1}: Found {len(response.tool_calls)} tool calls"
            )
            messages.append(
                AIMessage(content=response.content or "", tool_calls=response.tool_calls)
            )
            for tool_call in response.tool_calls:
                messages.append(GenerationEngine._execute_tool_call(tool_call, tools))

        logger.warning("Reached maximum iterations without finalizing tool loop")
        return None, messages

    @staticmethod
    def _try_parse_json(text: str, schema_class: type):
        """Attempt one JSON parse + schema coercion. Returns the object, or None on failure."""
        try:
            return schema_class(**json.loads(text.strip()))
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"JSON parsing failed: {e}")
            return None

    @staticmethod
    def parse_json_response(response_text: str, schema_class: type):
        """
        Parse JSON response with fallback handling.
        Returns parsed object or None if parsing fails.
        """
        result = GenerationEngine._try_parse_json(response_text, schema_class)
        if result is not None:
            return result

        # Fallback: try to extract JSON from markdown code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if json_match:
            result = GenerationEngine._try_parse_json(json_match.group(1), schema_class)
            if result is not None:
                return result

        logger.error(
            f"All JSON parsing attempts failed for schema {schema_class.__name__}"
        )
        return None

    @staticmethod
    def _response_text(response) -> str:
        """Extract text content from a LangChain model response."""
        return response.content if hasattr(response, "content") else str(response)

    @staticmethod
    def generate_basic(
        create_llm,
        output_parser,
        generation_chain,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Basic text generation with optional system message support."""
        try:
            if temperature is not None or top_p is not None or kwargs or system_message:
                llm = create_llm(temperature=temperature, top_p=top_p, **kwargs)
                if system_message:
                    messages = GenerationEngine.build_messages(system_message, prompt)
                    result = (llm | output_parser).invoke(messages)
                else:
                    result = (llm | output_parser).invoke(prompt)
            else:
                result = generation_chain.invoke(prompt)

            logger.info(f"Generated text length: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"Basic text generation failed: {e}")
            raise

    @staticmethod
    def _run_tools_phase(
        create_llm,
        system_message: Optional[str],
        human_message: str,
        tools: Optional[List[BaseTool]],
        temperature: Optional[float],
        top_p: Optional[float],
        return_text_when_no_tools: bool,
        **kwargs,
    ):
        """Bind tools, build the message list, and run the tool loop. Returns (llm, final_text, messages)."""
        llm = create_llm(temperature=temperature, top_p=top_p, **kwargs)
        llm_with_tools = llm.bind_tools(tools) if tools else llm

        messages = GenerationEngine.build_messages(system_message, human_message)
        max_iterations = kwargs.get("max_tool_iterations", 5)

        final_text, messages = GenerationEngine.run_tool_loop(
            llm_with_tools=llm_with_tools,
            messages=messages,
            tools=tools,
            max_iterations=max_iterations,
            return_text_when_no_tools=return_text_when_no_tools,
        )
        return llm, final_text, messages

    @staticmethod
    def generate_with_tools(
        create_llm,
        system_message: Optional[str] = None,
        human_message: str = "",
        tools: Optional[List[BaseTool]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ):
        """
        Tool-enabled generation using the provider's function/tool calling.
        Uses LangChain's bind_tools, which internally uses the provider's native tool-calling support.
        """
        try:
            logger.info(
                f"Generating with tool support. Tools: {len(tools) if tools else 0}"
            )
            _, final_text, _ = GenerationEngine._run_tools_phase(
                create_llm,
                system_message,
                human_message,
                tools,
                temperature,
                top_p,
                return_text_when_no_tools=True,
                **kwargs,
            )

            final_response = final_text or ""
            logger.info(
                f"Tool generation completed. Final response length: {len(final_response)}"
            )
            return final_response

        except Exception as e:
            logger.error(f"Tool-enabled generation failed: {e}")
            raise

    @staticmethod
    def generate_with_tools_and_structure(
        create_llm,
        system_message: Optional[str] = None,
        human_message: str = "",
        tools: Optional[List[BaseTool]] = None,
        schema_class: Optional[type] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ):
        """
        Combined tool calling with structured final output.
        Uses tools during reasoning, then uses custom JSON parsing for the final response.
        """
        try:
            effective_temperature = temperature if temperature is not None else 0.0

            logger.info(
                f"Generating with tools + structured output. Tools: {len(tools) if tools else 0}, Schema: {schema_class.__name__ if schema_class else 'None'}"
            )
            llm, _, messages = GenerationEngine._run_tools_phase(
                create_llm,
                system_message,
                human_message,
                tools,
                effective_temperature,
                top_p,
                return_text_when_no_tools=False,
                **kwargs,
            )

            # After tool loop, request structured JSON as final output
            json_instruction = GenerationEngine.build_schema_instruction(
                schema_class, variant="final"
            )
            messages.append(SystemMessage(content=json_instruction))

            response = llm.invoke(messages)
            response_text = GenerationEngine._response_text(response)
            return GenerationEngine.parse_json_response(response_text, schema_class)

        except Exception as e:
            logger.error(f"Combined tool + structured generation failed: {e}")
            raise

    @staticmethod
    def generate_structured(
        create_llm,
        schema_class,
        system_message: Optional[str] = None,
        human_message: str = "",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ):
        """
        Structured output generation using custom JSON parsing.
        Instructs the model to output JSON and parses the response.
        """
        try:
            effective_temperature = temperature if temperature is not None else 0.0

            # Filter kwargs like previous implementation did for certain keys
            filter_keys = {"max_length", "temperature", "top_p"}
            llm = create_llm(
                temperature=effective_temperature,
                top_p=top_p,
                filter_keys=filter_keys,
                **kwargs,
            )

            json_instruction = GenerationEngine.build_schema_instruction(
                schema_class, variant="must"
            )
            enhanced_system = (
                system_message + "\n\n" + json_instruction
                if system_message
                else json_instruction
            )

            messages = GenerationEngine.build_messages(enhanced_system, human_message)

            logger.info(
                f"Generating structured output with schema {schema_class.__name__}"
            )

            response = llm.invoke(messages)
            response_text = GenerationEngine._response_text(response)

            return GenerationEngine.parse_json_response(response_text, schema_class)

        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            raise
