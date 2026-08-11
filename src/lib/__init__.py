# __init__.py

from .agent import ModelWrapper
from .ollama import LangChainOllamaWrapper

__all__ = ["ModelWrapper", "LangChainOllamaWrapper"]