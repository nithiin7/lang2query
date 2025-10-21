"""
NVIDIA Model Wrapper

A wrapper that provides NVIDIA model integration while maintaining
compatibility with the existing ModelWrapper interface.
"""

import logging
import requests
from typing import Optional, Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)


class NvidiaWrapper:
    """
    NVIDIA-based model wrapper that provides a clean interface
    while leveraging NVIDIA API integration.
    """

    def __init__(
        self,
        base_url: str,
        provider: str = "nvidia",
        model: str = None,
        timeout: int = 300,
        default_temperature: float = 0.4,
        default_top_p: float = 0.95,
        default_max_tokens: int = 4096,
        **kwargs
    ):
        """
        Initialize the NVIDIA wrapper.

        Args:
            base_url: NVIDIA proxy base URL
            provider: NVIDIA provider identifier
            model: NVIDIA model name
            timeout: Request timeout in seconds
            default_temperature: Default sampling temperature
            default_top_p: Default top-p sampling parameter
            default_max_tokens: Default maximum tokens
            **kwargs: Additional parameters
        """
        self.base_url = base_url
        self.provider = provider
        self.model = model
        self.timeout = timeout
        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens

        # Validate required parameters
        if not self.base_url:
            raise ValueError("NVIDIA proxy base URL is required")
        if not self.model:
            raise ValueError("NVIDIA model is required")

        logger.info(f"NVIDIA wrapper initialized with model: {self.model}")

    def _nvidia_endpoint(self) -> str:
        """Generate the NVIDIA API endpoint URL."""
        return f"{self.base_url}/proxy?provider={self.provider}&model={self.model}"

    def _schema_info(self, schema_class: type) -> str:
        """Return JSON schema info for a Pydantic class or a fallback string."""
        try:
            if hasattr(schema_class, 'model_json_schema'):
                return str(schema_class.model_json_schema())
            return f"Schema class: {getattr(schema_class, '__name__', str(schema_class))}"
        except Exception:
            return f"Schema class: {getattr(schema_class, '__name__', 'UnknownSchema')}"

    def _build_schema_instruction_for_system(self, schema_class: type) -> str:
        """Create a system-level instruction describing the required JSON schema."""
        return (
            "Your response must be a valid JSON object conforming to this schema: "
            f"{self._schema_info(schema_class)}"
        )

    def _append_schema_instruction_to_user(self, schema_class: type, human_message: str) -> str:
        """Append a user-level instruction requesting JSON that matches the schema."""
        return (
            human_message
            + "\n\nPlease respond with a valid JSON object matching this schema: "
            + f"{self._schema_info(schema_class)}"
        )

    def _maybe_messages(self, system_message: Optional[str], human_message: str) -> Optional[List[Dict[str, str]]]:
        """Return messages list if system_message is provided; otherwise None (basic mode)."""
        if system_message:
            return [
                {"role": "system", "content": system_message},
                {"role": "user", "content": human_message},
            ]
        return None

    def _parse_structured_response(self, result: Any, schema_class: type):
        """Robustly extract and validate JSON according to schema_class."""
        import json
        from pydantic import ValidationError
        import re

        if schema_class is None:
            return result

        try:
            if isinstance(result, str):
                response_text = result.strip()
                if response_text.startswith('{') and response_text.endswith('}'):
                    parsed_data = json.loads(response_text)
                elif response_text.startswith('```json') and response_text.endswith('```'):
                    json_content = response_text[7:-3].strip()
                    parsed_data = json.loads(json_content)
                else:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        parsed_data = json.loads(json_match.group())
                    else:
                        parsed_data = json.loads(response_text)
            else:
                parsed_data = result

            return schema_class(**parsed_data)
        except (json.JSONDecodeError, ValidationError) as parse_error:
            logger.warning(f"Failed to parse structured response: {parse_error}. Returning raw response.")
            return result
        except Exception as parse_error:
            logger.warning(f"Unexpected error parsing structured response: {parse_error}. Returning raw response.")
            return result

    def _nvidia_generate(
        self,
        prompt: str,
        max_length: int,
        temperature: float,
        top_p: float,
        messages: Optional[list] = None,
        tools: Optional[list] = None,
        **kwargs
    ) -> str:
        """
        Generate text using NVIDIA provider.

        Args:
            prompt: Input prompt (used when messages is None)
            max_length: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            messages: Chat messages (optional)
            tools: Tools for function calling (optional, currently ignored)
            **kwargs: Additional request parameters

        Returns:
            Generated text string
        """
        url = self._nvidia_endpoint()
        payload = {
            "model": self.model,
            "messages": messages if messages is not None else [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature if temperature is not None else self.default_temperature,
            "top_p": top_p if top_p is not None else self.default_top_p,
            "max_tokens": max_length if max_length is not None else self.default_max_tokens,
        }

        # Add any additional parameters from kwargs
        payload.update(kwargs)

        try:
            logger.info(f"Making NVIDIA API request to: {url}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Handle various response formats
            if isinstance(data, str):
                return data.strip()
            if isinstance(data, dict):
                if "choices" in data and data["choices"]:
                    msg = data["choices"][0].get("message") or {}
                    content = msg.get("content", "").strip()
                    if content:
                        return content
                if "message" in data and isinstance(data["message"], dict):
                    return data["message"].get("content", "").strip()
                if "content" in data and isinstance(data["content"], str):
                    return data["content"].strip()
                if "response" in data and isinstance(data["response"], str):
                    return data["response"].strip()
                if "text" in data and isinstance(data["text"], str):
                    return data["text"].strip()
                if "result" in data and isinstance(data["result"], str):
                    return data["result"].strip()

            logger.warning(f"NVIDIA proxy: unrecognized response schema keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
            return ""

        except requests.exceptions.Timeout as e:
            logger.error(f"NVIDIA proxy request timed out: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"NVIDIA proxy request failed: {e}")
            raise

    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        tools: Optional[List] = None,
        schema_class: Optional[type] = None,
        max_length: int = 8192,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ):
        """
        Unified generate method supporting basic text, tool-enabled, and structured output generation.
        Can combine tools and structured output for comprehensive functionality.
        Note: Tools are currently ignored as NVIDIA provider doesn't support tool calling yet.

        Args:
            prompt: Input text prompt (used as human message)
            system_message: Optional system prompt/instruction
            tools: Optional list of tools for function calling (currently ignored)
            schema_class: Optional Pydantic model class for structured output
            max_length: Maximum length of generated text
            temperature: Sampling temperature (overrides default if provided)
            top_p: Top-p sampling parameter (overrides default if provided)
            **kwargs: Additional generation parameters

        Returns:
            Generated text string or structured object (depending on schema_class)
        """
        try:
            # Route to appropriate generation method based on parameters
            if tools is not None:
                # Tool-enabled generation (supports structured output if schema_class is provided)
                return self._generate_with_tools(
                    system_message=system_message,
                    human_message=prompt,
                    tools=tools,
                    schema_class=schema_class,
                    max_length=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs
                )
            elif schema_class is not None:
                # Structured output generation without tools
                return self._generate_structured(
                    schema_class=schema_class,
                    system_message=system_message,
                    human_message=prompt,
                    max_length=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs
                )
            else:
                # Basic text generation
                return self._generate_basic(
                    prompt=prompt,
                    system_message=system_message,
                    max_length=max_length,
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
        max_length: int = 8192,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Basic text generation with optional system message support.
        """
        try:
            logger.info(f"Generating text with prompt length: {len(prompt)}")

            # Build messages if system message is provided
            messages = self._maybe_messages(system_message, prompt)

            result = self._nvidia_generate(
                prompt=prompt,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                messages=messages,
                **kwargs
            )

            logger.info(f"Generated text length: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"Basic text generation failed: {e}")
            raise

    def _generate_with_tools(
        self,
        system_message: Optional[str] = None,
        human_message: str = "",
        tools: Optional[List] = None,
        schema_class: Optional[type] = None,
        max_length: int = 8192,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ):
        """
        Tool-enabled generation with optional structured output support.
        Note: Tools are currently ignored as NVIDIA provider doesn't support tool calling.

        Returns:
            str or schema_class instance (depending on schema_class parameter)
        """
        try:
            # Build messages
            messages: List[Dict[str, str]] = []
            if system_message:
                # If structured output is requested, enhance system message
                if schema_class is not None:
                    enhanced_system = system_message + "\n\nIMPORTANT: " + self._build_schema_instruction_for_system(schema_class)
                    messages.append({"role": "system", "content": enhanced_system})
                else:
                    messages.append({"role": "system", "content": system_message})
            elif schema_class is not None:
                # Add schema instruction even without custom system message
                schema_instruction = self._build_schema_instruction_for_system(schema_class)
                messages.append({"role": "system", "content": schema_instruction})

            messages.append({"role": "user", "content": human_message})

            logger.info(f"Generating with tool support. Messages: {len(messages)}, Tools: {len(tools) if tools else 0}")

            # For now, tools are ignored since NVIDIA provider doesn't support tool calling
            # TODO: Implement actual tool calling for NVIDIA provider when supported
            result = self._nvidia_generate(
                prompt=human_message,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                messages=messages,
                tools=tools,
                **kwargs
            )

            # If structured output is requested, parse the response
            if schema_class is not None and result:
                structured = self._parse_structured_response(result, schema_class)
                return structured

            logger.info(f"Final response length: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"Tool-enabled generation failed: {e}")
            raise

    def _generate_structured(
        self,
        schema_class,
        system_message: Optional[str] = None,
        human_message: str = "",
        max_length: int = 8192,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs
    ):
        """
        Structured output generation using NVIDIA provider.

        Returns:
            Instance of the Pydantic schema class
        """
        try:
            # Build messages with schema instruction
            messages: List[Dict[str, str]] = []
            if system_message:
                messages.append({"role": "system", "content": system_message})

            # Add schema instruction to user message
            enhanced_human_message = self._append_schema_instruction_to_user(schema_class, human_message)
            messages.append({"role": "user", "content": enhanced_human_message})

            logger.info(f"Generating structured output with schema {schema_class.__name__}")

            # Generate response
            text_response = self._nvidia_generate(
                prompt=enhanced_human_message,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                messages=messages,
                **kwargs
            )

            # Parse the response as JSON according to schema
            result = self._parse_structured_response(text_response, schema_class)
            return result

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Structured generation failed - JSON parsing error: {e}")
            # Return a default instance if parsing fails
            try:
                return schema_class()
            except Exception:
                raise ValueError(f"Could not generate structured output for {schema_class.__name__}: {e}")
        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            # Return a default instance if parsing fails
            try:
                return schema_class()
            except Exception:
                raise ValueError(f"Could not generate structured output for {schema_class.__name__}: {e}")


    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the NVIDIA model."""
        return {
            "model_type": "nvidia",
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "chat_format": "openai_compatible",
        }