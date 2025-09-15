"""
Model Wrapper

A flexible wrapper that can automatically detect and load different model types
from the models folder. Supports various transformer models including:
- Qwen, Llama, Mistral, CodeLlama, etc.
- Different model formats (safetensors, pytorch)
- Automatic device detection and optimization
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import requests

try:
    import torch  # type: ignore
except Exception:  # ImportError or others
    torch = None  # type: ignore

try:
    from transformers import (  # type: ignore
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
except Exception:
    AutoTokenizer = None  # type: ignore
    AutoModelForCausalLM = None  # type: ignore
    BitsAndBytesConfig = None  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModelWrapper:
    """Generic wrapper for any transformer model with automatic detection and Ollama API support."""

    def __init__(
        self,
        model_path: Union[str, Path] = "models",
        use_quantization: bool = True,
        ollama_endpoint: Optional[str] = None,
        ollama_model: Optional[str] = None,
        ollama_timeout: int = 300,
    ):
        """
        Initialize the generic model wrapper.

        Args:
            model_path: Path to the models directory or specific model
            use_quantization: Whether to use 4-bit quantization for faster inference
            ollama_endpoint: Ollama API endpoint URL
            ollama_model: Model name to use with Ollama API
            ollama_timeout: Timeout in seconds for Ollama API requests (default: 300)
        """
        self.model_path = (
            Path(model_path) if isinstance(model_path, str) else model_path
        )
        self.tokenizer = None
        self.model = None
        self.ollama_endpoint = ollama_endpoint
        self.ollama_model = ollama_model
        self.ollama_timeout = ollama_timeout
        self.use_ollama = bool(ollama_endpoint and ollama_model)

        # Prefer CUDA > MPS (Apple Silicon) > CPU
        if torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available():
            self.device = "cuda"
        elif (
            torch is not None
            and hasattr(torch, "backends")
            and hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            self.device = "mps"
        else:
            self.device = "cpu"
        self.use_quantization = (
            use_quantization and torch is not None and self.device == "cuda"
        )
        self.model_info = {}

        if self.use_ollama:
            logger.info(
                f"Initializing Ollama API wrapper with endpoint: {self.ollama_endpoint}"
            )
            logger.info(f"Using Ollama model: {self.ollama_model}")
            self._test_ollama_connection()
        else:
            logger.info(f"Initializing Local Model Wrapper on device: {self.device}")
            if self.use_quantization:
                logger.info("Using 4-bit quantization for faster inference")
            # Auto-detect and load the model
            self._auto_detect_and_load()

    def _auto_detect_and_load(self):
        """Automatically detect model type and load it."""
        try:
            if AutoTokenizer is None or AutoModelForCausalLM is None:
                raise ImportError(
                    "Local model load requires 'transformers' and 'torch'. Install with: 'poetry add torch torchvision torchaudio transformers accelerate bitsandbytes --extras cpu' or use Ollama mode."
                )
            # If model_path points to a specific model folder
            if self.model_path.is_dir() and self._is_model_folder(self.model_path):
                logger.info(f"Loading model from: {self.model_path}")
                self._load_specific_model(self.model_path)
            else:
                # Look for models in the models directory
                models_dir = Path("models")
                if models_dir.exists():
                    available_models = self._discover_models(models_dir)
                    if available_models:
                        # Use the first available model
                        first_model = available_models[0]
                        logger.info(f"Auto-selected model: {first_model}")
                        self._load_specific_model(first_model)
                    else:
                        raise FileNotFoundError(
                            "No valid models found in models directory"
                        )
                else:
                    raise FileNotFoundError("Models directory not found")

        except Exception as e:
            logger.error(f"Failed to auto-detect and load model: {e}")
            raise

    def _is_model_folder(self, path: Path) -> bool:
        """Check if a directory contains a valid model."""
        required_files = ["config.json", "tokenizer.json"]
        optional_files = [
            "model.safetensors",
            "pytorch_model.bin",
            "model-*.safetensors",
        ]

        # Check for required files
        has_required = all((path / file).exists() for file in required_files)

        # Check for at least one model file
        has_model = any(any(path.glob(pattern)) for pattern in optional_files)

        return has_required and has_model

    def _discover_models(self, models_dir: Path) -> list[Path]:
        """Discover available models in the models directory."""
        models = []

        for item in models_dir.iterdir():
            if item.is_dir() and self._is_model_folder(item):
                models.append(item)
                logger.info(f"Found model: {item.name}")

        # Sort by name for consistent selection
        models.sort(key=lambda x: x.name)
        return models

    def _load_specific_model(self, model_path: Path):
        """Load a specific model from the given path."""
        try:
            # Load model configuration
            config_path = model_path / "config.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                self.model_info = config
                logger.info(f"Model type: {config.get('model_type', 'unknown')}")
                logger.info(
                    f"Model architecture: {config.get('architectures', ['unknown'])[0] if config.get('architectures') else 'unknown'}"
                )

            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True
            )

            # Set pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Load model
            logger.info("Loading model...")

            if self.use_quantization:
                self._load_quantized_model(model_path)
            else:
                self._load_standard_model(model_path)

            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise

    def _load_quantized_model(self, model_path: Path):
        """Load model with 4-bit quantization."""
        try:
            if BitsAndBytesConfig is None or AutoModelForCausalLM is None:
                raise ImportError("bitsandbytes/transformers not available")
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=(torch.float16 if torch is not None else None),
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )

            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )
        except Exception as e:
            logger.warning(f"Quantized loading failed, falling back to standard: {e}")
            self._load_standard_model(model_path)

    def _load_standard_model(self, model_path: Path):
        """Load model without quantization."""
        # Remove dtype parameter as it's not supported by all model classes
        if AutoModelForCausalLM is None:
            raise ImportError("transformers is required for local model loading")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )

        if torch is not None and self.device in ("cpu", "mps"):
            # Keep float16 on MPS for lower memory usage and better performance on Apple Silicon
            dtype = torch.float16 if self.device == "mps" else None
            self.model = (
                self.model.to(self.device, dtype=dtype)
                if dtype
                else self.model.to(self.device)
            )

        # Ensure eval mode for faster inference
        self.model.eval()

    def _test_ollama_connection(self):
        """Test connection to Ollama API endpoint."""
        try:
            response = requests.get(f"{self.ollama_endpoint}/api/tags", timeout=30)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                logger.info(f"Connected to Ollama. Available models: {model_names}")

                # Check if the specified model is available
                if self.ollama_model not in model_names:
                    logger.warning(
                        f"Model '{self.ollama_model}' not found in Ollama. Available: {model_names}"
                    )
            else:
                logger.warning(
                    f"Ollama API returned status code: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to connect to Ollama API at {self.ollama_endpoint}: {e}"
            )
            raise ConnectionError(f"Cannot connect to Ollama API: {e}")

    def _ollama_generate(
        self,
        prompt: str,
        max_length: int = 256,
        temperature: float = 0.6,
        top_p: float = 0.95,
        **kwargs,
    ) -> str:
        """Generate text using Ollama API."""
        try:
            url = f"{self.ollama_endpoint}/api/generate"

            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": max_length,
                    **kwargs,
                },
            }

            logger.info(
                f"Generating text with Ollama API, prompt length: {len(prompt)}"
            )

            response = requests.post(url, json=payload, timeout=self.ollama_timeout)
            response.raise_for_status()

            result = response.json()
            generated_text = result.get("response", "").strip()

            logger.info(f"Generated text length: {len(generated_text)}")
            return generated_text

        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama API request timed out after 5 minutes: {e}")
            raise ConnectionError(
                "Request timed out - the remote Ollama server may be overloaded or the model is too large. Try a smaller model or check server status."
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ollama API connection failed: {e}")
            raise ConnectionError(
                f"Cannot connect to Ollama server at {self.ollama_endpoint}. Check if the server is running and accessible."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama text generation failed: {e}")
            raise

    def _ollama_chat(
        self, message: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """Generate a chat response using Ollama API."""
        try:
            url = f"{self.ollama_endpoint}/api/chat"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": message})

            payload = {
                "model": self.ollama_model,
                "messages": messages,
                "stream": False,
                "options": kwargs,
            }

            logger.info("Generating chat response with Ollama API")

            response = requests.post(url, json=payload, timeout=self.ollama_timeout)
            response.raise_for_status()

            result = response.json()
            generated_text = result.get("message", {}).get("content", "").strip()

            logger.info(f"Generated chat response length: {len(generated_text)}")
            return generated_text

        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama chat API request timed out after 5 minutes: {e}")
            raise ConnectionError(
                "Chat request timed out - the remote Ollama server may be overloaded or the model is too large. Try a smaller model or check server status."
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ollama chat API connection failed: {e}")
            raise ConnectionError(
                f"Cannot connect to Ollama server at {self.ollama_endpoint}. Check if the server is running and accessible."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama chat API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama chat generation failed: {e}")
            raise

    def generate(
        self,
        prompt: str,
        max_length: int = 256,
        temperature: float = 0.6,
        top_p: float = 0.95,
        **kwargs,
    ) -> str:
        """
        Generate text based on the input prompt.

        Args:
            prompt: Input text prompt
            max_length: Maximum length of generated text
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Top-p sampling parameter
            **kwargs: Additional generation parameters

        Returns:
            Generated text string
        """
        if self.use_ollama:
            return self._ollama_generate(
                prompt, max_length, temperature, top_p, **kwargs
            )

        try:
            if not self.model or not self.tokenizer:
                raise RuntimeError("Model not loaded")

            logger.info(f"Generating text with prompt length: {len(prompt)}")

            # Tokenize input
            inputs = self.tokenizer(
                prompt, return_tensors="pt", padding=True, truncation=True
            )
            if self.device in ("cuda", "mps"):
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generation parameters - filter out unsupported parameters
            generation_kwargs = {
                "max_new_tokens": max_length,
                "do_sample": True,
                "pad_token_id": self.tokenizer.eos_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
                "use_cache": True,
                "repetition_penalty": 1.1,
                **kwargs,
            }

            # Only add temperature and top_p if they're supported
            if temperature > 0:
                generation_kwargs["temperature"] = temperature
            if top_p < 1.0:
                generation_kwargs["top_p"] = top_p

            # Generate text
            if torch is not None:
                with torch.inference_mode():
                    outputs = self.model.generate(**inputs, **generation_kwargs)
            else:
                outputs = self.model.generate(**inputs, **generation_kwargs)

            # Decode output with error handling
            try:
                generated_text = self.tokenizer.decode(
                    outputs[0],
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True,
                )
            except Exception as decode_error:
                logger.error(f"Token decode failed: {decode_error}")
                # Try alternative decode method
                try:
                    generated_text = self.tokenizer.decode(
                        outputs[0], skip_special_tokens=True
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback decode also failed: {fallback_error}")
                    # Last resort: convert to string
                    generated_text = str(outputs[0].tolist())

            # Remove the input prompt from the output
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt) :].strip()

            logger.info(f"Generated text length: {len(generated_text)}")
            return generated_text

        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise

    def chat(self, message: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        Generate a chat response using the model's chat format.

        Args:
            message: User message
            system_prompt: Optional system prompt
            **kwargs: Additional generation parameters

        Returns:
            Generated response
        """
        if self.use_ollama:
            return self._ollama_chat(message, system_prompt, **kwargs)

        # Try to detect chat format from model info
        chat_format = self._detect_chat_format()

        if chat_format == "qwen":
            prompt = (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{message}<|im_end|>\n<|im_start|>assistant\n"
                if system_prompt
                else f"<|im_start|>user\n{message}<|im_end|>\n<|im_start|>assistant\n"
            )
        elif chat_format == "llama":
            prompt = (
                f"[INST] {system_prompt}\n\n{message} [/INST]"
                if system_prompt
                else f"[INST] {message} [/INST]"
            )
        elif chat_format == "mistral":
            prompt = (
                f"<s>[INST] {system_prompt}\n\n{message} [/INST]"
                if system_prompt
                else f"<s>[INST] {message} [/INST]"
            )
        else:
            # Generic format
            prompt = (
                f"System: {system_prompt}\n\nUser: {message}\n\nAssistant:"
                if system_prompt
                else f"User: {message}\n\nAssistant:"
            )

        return self.generate(prompt, **kwargs)

    def _detect_chat_format(self) -> str:
        """Detect the chat format based on model configuration."""
        model_type = self.model_info.get("model_type", "").lower()
        architectures = [
            arch.lower() for arch in self.model_info.get("architectures", [])
        ]

        if "qwen" in model_type or any("qwen" in arch for arch in architectures):
            return "qwen"
        elif "llama" in model_type or any("llama" in arch for arch in architectures):
            return "llama"
        elif "mistral" in model_type or any(
            "mistral" in arch for arch in architectures
        ):
            return "mistral"
        else:
            return "generic"

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if self.use_ollama:
            return {
                "model_type": "ollama",
                "ollama_endpoint": self.ollama_endpoint,
                "ollama_model": self.ollama_model,
                "chat_format": "ollama",
            }
        else:
            return {
                "model_path": str(self.model_path),
                "model_type": self.model_info.get("model_type", "unknown"),
                "architectures": self.model_info.get("architectures", []),
                "device": self.device,
                "quantization": self.use_quantization,
                "chat_format": self._detect_chat_format(),
            }

    def __del__(self):
        """Cleanup when the wrapper is destroyed."""
        if not self.use_ollama:
            if hasattr(self, "model") and self.model is not None:
                del self.model
            if hasattr(self, "tokenizer") and self.tokenizer is not None:
                del self.tokenizer
            try:
                if (
                    torch is not None
                    and hasattr(torch, "cuda")
                    and torch.cuda.is_available()
                ):
                    torch.cuda.empty_cache()
            except Exception:
                pass
