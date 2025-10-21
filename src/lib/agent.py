"""
Model Wrapper

A flexible wrapper that can automatically detect and load different model types
from the models folder. Supports various transformer models including:
- Qwen, Llama, Mistral, CodeLlama, etc.
- Different model formats (safetensors, pytorch)
- Automatic device detection and optimization
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
import json
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    BitsAndBytesConfig,
)

from .langchain import LangChainOllamaWrapper
from .nvidia import NvidiaWrapper
import config as app_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelWrapper:
    """Generic wrapper for local models, Ollama, or external providers"""
    
    def __init__(
        self,
        model_path: Union[str, Path] = "models",
        use_quantization: bool = True,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 300,
    ):
        """
        Initialize the generic model wrapper.

        Args:
            model_path: Path to the models directory or specific model
            use_quantization: Whether to use 4-bit quantization for faster inference
            base_url: API base URL for API integration
            model: Model name to use with API
            timeout: Timeout in seconds for API requests (default: 300)
        """
        self.model_path = Path(model_path) if isinstance(model_path, str) else model_path
        self.tokenizer = None
        self.model = None
        self.base_url = base_url or "http://localhost:11434"
        self.model = model
        self.timeout = timeout
    
        self.langchain_wrapper = None
        self.nvidia_wrapper = None

        self.provider = getattr(app_config, "PROVIDER", None)
        if self.provider:
            self.provider = self.provider.lower()

        # Generation defaults from config
        self.default_temperature = getattr(app_config, "DEFAULT_TEMPERATURE", 0.4)
        self.default_top_p = getattr(app_config, "DEFAULT_TOP_P", 0.95)
        self.default_max_tokens = getattr(app_config, "DEFAULT_MAX_TOKENS", 4096)

        # Prefer CUDA > MPS (Apple Silicon) > CPU
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
        self.use_quantization = use_quantization and self.device == "cuda"
        self.model_info = {}

        if self.provider == "nvidia":
            self._initialize_nvidia_wrapper()
        elif self.provider == "ollama":
            self._initialize_langchain_ollama()
        else:
            logger.info(f"Initializing Local Model Wrapper on device: {self.device}")
            if self.use_quantization:
                logger.info("Using 4-bit quantization for faster inference")
            # Auto-detect and load the model
            self._auto_detect_and_load()
    
    def _initialize_langchain_ollama(self):
        """Initialize LangChain Ollama wrapper."""
        try:
            self.langchain_wrapper = LangChainOllamaWrapper(
                model=self.model,
                base_url=self.base_url,
                timeout=self.timeout
            )
            logger.info("LangChain Ollama wrapper initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize LangChain Ollama wrapper: {e}")
            raise

    def _initialize_nvidia_wrapper(self):
        """Initialize NVIDIA wrapper."""
        try:
            nvidia_base_url = getattr(app_config, "BASE_URL", None)
            nvidia_provider = getattr(app_config, "PROVIDER", "nvidia")
            nvidia_model = getattr(app_config, "MODEL", None)

            self.nvidia_wrapper = NvidiaWrapper(
                base_url=nvidia_base_url,
                provider=nvidia_provider,
                model=nvidia_model,
                timeout=self.timeout,
                default_temperature=self.default_temperature,
                default_top_p=self.default_top_p,
                default_max_tokens=self.default_max_tokens
            )
            logger.info("NVIDIA wrapper initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize NVIDIA wrapper: {e}")
            raise
    
    def _auto_detect_and_load(self):
        """Automatically detect and load model from the models directory."""
        try:
            models_dir = Path("models")
            if models_dir.exists():
                available_models = self._discover_models(models_dir)
                if available_models:
                    # Use the first available model
                    selected_model = available_models[0]
                    logger.info(f"Auto-selected model: {selected_model}")
                    self._load_specific_model(selected_model)
                else:
                    raise FileNotFoundError("No valid models found in models directory")
            else:
                raise FileNotFoundError("Models directory not found")
                    
        except Exception as e:
            logger.error(f"Failed to auto-detect and load model: {e}")
            raise
    
    def _is_model_folder(self, path: Path) -> bool:
        """Check if a directory contains a valid model."""
        required_files = ["config.json", "tokenizer.json"]
        optional_files = ["model.safetensors", "pytorch_model.bin", "model-*.safetensors"]
        
        # Check for required files
        has_required = all((path / file).exists() for file in required_files)
        
        # Check for at least one model file
        has_model = any(
            any(path.glob(pattern)) for pattern in optional_files
        )
        
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
                with open(config_path, 'r') as f:
                    config = json.load(f)
                self.model_info = config
                logger.info(f"Model type: {config.get('model_type', 'unknown')}")
                logger.info(f"Model architecture: {config.get('architectures', ['unknown'])[0] if config.get('architectures') else 'unknown'}")
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True
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
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
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
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        
        if self.device in ("cpu", "mps"):
            # Keep float16 on MPS for lower memory usage and better performance on Apple Silicon
            dtype = torch.float16 if self.device == "mps" else None
            self.model = self.model.to(self.device, dtype=dtype) if dtype else self.model.to(self.device)
        
        # Ensure eval mode for faster inference
        self.model.eval()

    def generate(self, schema_class, tools: Optional[list] = None, system_message: Optional[str] = None, human_message: str = "", **kwargs):
        """
        Generate structured output based on a Pydantic schema.

        Args:
            schema_class: Pydantic model class for structured output
            tools: List of tools to use for tool calling (optional)
            system_message: System prompt/instruction (optional)
            human_message: User/human message
            **kwargs: Additional generation parameters

        Returns:
            Instance of the Pydantic schema class
        """
        if self.provider == "nvidia" and self.nvidia_wrapper:
            return self.nvidia_wrapper.generate(
                schema_class=schema_class,
                tools=tools,
                system_message=system_message,
                human_message=human_message,
                **kwargs
            )

        elif self.provider == "ollama" and self.langchain_wrapper:
            return self.langchain_wrapper.generate(
                schema_class=schema_class,
                tools=tools,
                system_message=system_message,
                human_message=human_message,
                **kwargs
            )


        raise NotImplementedError("Structured output is not supported for local models. Use 'ollama' or 'nvidia' provider instead.")

    def cleanup(self):
        """Clean up resources, especially GPU memory used by local models."""
        try:
            if hasattr(self, 'model') and self.model is not None:
                logger.info("🧹 Cleaning up local model...")
                # Clear CUDA cache if model was using GPU
                if hasattr(self.model, 'device') and 'cuda' in str(self.model.device):
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        logger.info("✅ CUDA cache cleared")

                # Delete the model and tokenizer to free memory
                del self.model
                self.model = None
                if hasattr(self, 'tokenizer') and self.tokenizer:
                    del self.tokenizer
                    self.tokenizer = None
                logger.info("✅ Local model resources cleaned up")

            if hasattr(self, 'langchain_wrapper') and self.langchain_wrapper:
                # LangChain wrapper cleanup (if needed)
                self.langchain_wrapper = None
                logger.info("✅ LangChain wrapper cleaned up")

            if hasattr(self, 'nvidia_wrapper') and self.nvidia_wrapper:
                # NVIDIA wrapper cleanup (if needed)
                self.nvidia_wrapper = None
                logger.info("✅ NVIDIA wrapper cleaned up")

        except Exception as e:
            logger.error(f"⚠️ Warning during model cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup happens."""
        self.cleanup()
    
    def _detect_chat_format(self) -> str:
        """Detect the chat format based on model configuration."""
        model_type = self.model_info.get('model_type', '').lower()
        architectures = [arch.lower() for arch in self.model_info.get('architectures', [])]
        
        if 'qwen' in model_type or any('qwen' in arch for arch in architectures):
            return 'qwen'
        elif 'llama' in model_type or any('llama' in arch for arch in architectures):
            return 'llama'
        elif 'mistral' in model_type or any('mistral' in arch for arch in architectures):
            return 'mistral'
        else:
            return 'generic'
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if self.provider == "nvidia" and self.nvidia_wrapper:
            return self.nvidia_wrapper.get_model_info()

        elif self.provider == "ollama" and self.langchain_wrapper:
            return {
                "model_type": "ollama",
                "base_url": self.base_url,
                "model": self.model,
                "chat_format": "ollama"
            }

        else:
            return {
                "model_path": str(self.model_path),
                "model_type": self.model_info.get('model_type', 'unknown'),
                "architectures": self.model_info.get('architectures', []),
                "device": self.device,
                "quantization": self.use_quantization,
                "chat_format": self._detect_chat_format()
            }