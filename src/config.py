"""
Configuration settings for the text2query application.
"""

from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "docs"

# Knowledge Base paths
MD_DIRECTORY = BASE_DIR / "src" / "retriever" / "input"
KB_DIRECTORY = BASE_DIR / "src" / "kb"
COLLECTION_NAME = "sql_generation_kb"

# Embedding model path (None = auto-detect from models/bge-m3)
EMBEDDING_MODEL_PATH = None

# LLM provider configuration
# Options: "ollama", "local", "nvidia", "chatgpt"
PROVIDER = "ollama"
BASE_URL = "http://localhost:11434"
MODEL = "gpt-oss:20b" # "qwen2.5:14b"

# ChatGPT/OpenAI configuration
OPENAI_API_KEY = None  # Set your OpenAI API key here or via environment variable
OPENAI_MODEL = "gpt-4o"  # Options: gpt-4o, gpt-4o-mini, gpt-4, gpt-3.5-turbo
OPENAI_BASE_URL = None  # Optional: for OpenAI-compatible APIs

# Shared generation defaults
DEFAULT_TEMPERATURE = 0.6
DEFAULT_TOP_P = 0.7
DEFAULT_MAX_TOKENS = 8192