#!/usr/bin/env python3
"""
Model Download Script - Download and cache models locally
"""

import json
from pathlib import Path
from typing import Callable, Optional

import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer

MODELS_DIR = Path(__file__).parent.parent / "models"


def get_model_choice():
    """Prompt user to select which model to download"""
    print("\nModel Download Options")
    print("=" * 50)
    print("1. BGE-M3 (Embedding Model) - For text similarity and retrieval")
    print("2. LLaMA 3.2 3B Instruct (Language Model) - For text generation")
    print("=" * 50)

    while True:
        try:
            choice = input("Select model to download (1 or 2): ").strip()
            if choice == "1":
                return "bge_m3"
            if choice == "2":
                return "llama"
            print("Please enter 1 or 2")
        except KeyboardInterrupt:
            print("\n\nOperation cancelled")
            exit(1)


def _is_cached(local_model_path: Path) -> bool:
    """Check whether a model has already been downloaded to local_model_path."""
    return local_model_path.exists() and any(local_model_path.iterdir())


def _try_strategies(strategies: list[tuple[str, Callable]]):
    """Try each (description, fn) strategy in order, falling back on failure."""
    last_error: Optional[Exception] = None
    for description, fn in strategies:
        try:
            print(f"\n{description}...")
            return fn()
        except Exception as e:
            print(f"{description} failed: {e}")
            last_error = e
    raise last_error


# --- BGE-M3 ---------------------------------------------------------------


def _download_bge_m3_via_sentence_transformers(model_name: str, local_model_path: Path):
    model = SentenceTransformer(model_name, trust_remote_code=True)
    model.save(str(local_model_path))
    return model


def _write_bge_m3_sentence_transformer_config(local_model_path: Path):
    """BGE-M3 downloaded via raw transformers classes is missing the
    SentenceTransformer wrapper config (modules.json, pooling config);
    write it so the saved files can be reloaded as a SentenceTransformer."""
    modules_config = [
        {
            "idx": 0,
            "name": "0",
            "path": "",
            "type": "sentence_transformers.models.Transformer",
        },
        {
            "idx": 1,
            "name": "1",
            "path": "1_Pooling",
            "type": "sentence_transformers.models.Pooling",
        },
    ]
    with open(local_model_path / "modules.json", "w") as f:
        json.dump(modules_config, f, indent=2)

    pooling_dir = local_model_path / "1_Pooling"
    pooling_dir.mkdir(exist_ok=True)
    pooling_config = {
        "word_embedding_dimension": 1024,
        "pooling_mode_cls_token": True,
        "pooling_mode_mean_tokens": False,
        "pooling_mode_max_tokens": False,
        "pooling_mode_mean_sqrt_len_tokens": False,
        "pooling_mode_weightedmean_tokens": False,
        "pooling_mode_lasttoken": False,
        "include_prompt": True,
    }
    with open(pooling_dir / "config.json", "w") as f:
        json.dump(pooling_config, f, indent=2)


def _download_bge_m3_via_transformers(model_name: str, local_model_path: Path):
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model_transformer = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.save_pretrained(str(local_model_path))
    model_transformer.save_pretrained(str(local_model_path))

    _write_bge_m3_sentence_transformer_config(local_model_path)
    return SentenceTransformer(str(local_model_path))


def _test_bge_m3(model: SentenceTransformer):
    print("\nTesting model...")
    test_sentences = [
        "This is a test sentence.",
        "BGE-M3 is a powerful embedding model.",
        "It supports multiple languages and long context.",
    ]
    embeddings = model.encode(test_sentences, show_progress_bar=True)

    print("\nModel loaded successfully!")
    print("Model info:")
    print(f"   - Embedding dimension: {embeddings.shape[1]}")
    print(f"   - Max sequence length: {model.max_seq_length}")
    print(f"   - Device: {model.device}")

    print("\nSample embeddings (first 5 dimensions):")
    for i, (sentence, embedding) in enumerate(zip(test_sentences, embeddings)):
        print(f"   {i+1}. '{sentence[:50]}...' -> {embedding[:5].tolist()}")


def download_bge_m3():
    """Download BGE-M3 model (or load it from local cache) and save it locally"""
    model_name = "BAAI/bge-m3"
    local_model_path = MODELS_DIR / "bge-m3"
    print(f"Model will be saved to: {local_model_path}")
    local_model_path.parent.mkdir(exist_ok=True)

    if _is_cached(local_model_path):
        print(f"\nModel already exists at {local_model_path}")
        print("Loading from local cache...")
        model = SentenceTransformer(str(local_model_path))
        _test_bge_m3(model)
        return model, local_model_path

    print(f"\nDownloading model {model_name} from HuggingFace...")
    print("This may take a while on first download...")
    model = _try_strategies(
        [
            (
                "Downloading via SentenceTransformer",
                lambda: _download_bge_m3_via_sentence_transformers(
                    model_name, local_model_path
                ),
            ),
            (
                "Downloading model components separately",
                lambda: _download_bge_m3_via_transformers(
                    model_name, local_model_path
                ),
            ),
        ]
    )
    print(f"\nModel downloaded and saved to {local_model_path}")

    _test_bge_m3(model)
    return model, local_model_path


# --- LLaMA ------------------------------------------------------------------

LLAMA_MODEL_NAME = "context-labs/meta-llama-Llama-3.2-3B-Instruct-FP16"


def _load_llama_from_cache(local_model_path: Path):
    tokenizer = AutoTokenizer.from_pretrained(
        str(local_model_path), trust_remote_code=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(local_model_path),
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True,
    )
    return tokenizer, model


def _download_llama_default(model_name: str, local_model_path: Path):
    print("Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    print("Downloading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True,
    )

    print("Saving model and tokenizer locally...")
    tokenizer.save_pretrained(str(local_model_path))
    model.save_pretrained(str(local_model_path))
    return tokenizer, model


def _download_llama_low_memory(model_name: str, local_model_path: Path):
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        use_fast=False,  # Use slow tokenizer as fallback
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,  # Use float16 to reduce memory
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    tokenizer.save_pretrained(str(local_model_path))
    model.save_pretrained(str(local_model_path))
    return tokenizer, model


def _test_llama(model, tokenizer, local_model_path: Path):
    print("\nTesting model...")
    prompt = "Give me a short introduction to large language models."
    messages = [{"role": "user", "content": prompt}]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    print("Generating response...")
    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=512,  # Limit for testing
            temperature=0.6,
            top_p=0.95,
            top_k=20,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]) :].tolist()

    try:
        index = len(output_ids) - output_ids[::-1].index(151668)  # </think> token
    except ValueError:
        index = 0

    thinking_content = tokenizer.decode(
        output_ids[:index], skip_special_tokens=True
    ).strip("\n")
    content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

    print("\nModel loaded successfully!")
    print("Model info:")
    print(f"   - Device: {model.device}")
    print(f"   - Model path: {local_model_path}")

    print("\nSample response:")
    print(f"Prompt: '{prompt}'")
    if thinking_content:
        print(f"Thinking: '{thinking_content[:200]}...'")
    print(f"Response: '{content[:300]}...'")


def download_llama():
    """Download LLaMA model (or load it from local cache) and save it locally"""
    model_name = LLAMA_MODEL_NAME
    local_model_path = MODELS_DIR / model_name.split("/")[-1]
    print(f"Model will be saved to: {local_model_path}")
    local_model_path.parent.mkdir(exist_ok=True)

    if _is_cached(local_model_path):
        print(f"\nModel already exists at {local_model_path}")
        print("Loading from local cache...")
        tokenizer, model = _load_llama_from_cache(local_model_path)
        _test_llama(model, tokenizer, local_model_path)
        return model, tokenizer, local_model_path

    print(f"\nDownloading model {model_name} from HuggingFace...")
    print("This may take a while on first download (approximately 15-16 GB)...")
    tokenizer, model = _try_strategies(
        [
            (
                "Downloading with default settings",
                lambda: _download_llama_default(model_name, local_model_path),
            ),
            (
                "Downloading with float16 + slow-tokenizer fallback",
                lambda: _download_llama_low_memory(model_name, local_model_path),
            ),
        ]
    )
    print(f"\nModel downloaded and saved to {local_model_path}")

    _test_llama(model, tokenizer, local_model_path)
    return model, tokenizer, local_model_path


# --- CLI ----------------------------------------------------------------

MODEL_OPTIONS = {
    "bge_m3": {
        "label": "BGE-M3 Embedding Model",
        "download": download_bge_m3,
        "usage": (
            "   from sentence_transformers import SentenceTransformer\n"
            "   model = SentenceTransformer('{path}')"
        ),
    },
    "llama": {
        "label": "LLaMA 3.2 3B Instruct Language Model",
        "download": download_llama,
        "usage": (
            "   from transformers import AutoModelForCausalLM, AutoTokenizer\n"
            "   tokenizer = AutoTokenizer.from_pretrained('{path}', trust_remote_code=True)\n"
            "   model = AutoModelForCausalLM.from_pretrained('{path}', torch_dtype='auto',"
            " device_map='auto', trust_remote_code=True)"
        ),
    },
}


def main():
    print("Unified Model Download Script")
    print("=" * 60)

    model_choice = get_model_choice()
    option = MODEL_OPTIONS[model_choice]

    print(f"\nSelected: {option['label']}")
    print("-" * 40)

    try:
        result = option["download"]()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have internet connection")
        print("2. Check if you need to set proxy settings")
        print("3. Ensure you have enough disk space")
        print("4. Try running with: PYTHONWARNINGS='ignore' python3 download.py")
        return 1

    model_path = result[-1]  # download_* always returns local_model_path last
    print(f"\nSuccess! {option['label']} is ready to use.")
    print("\nTo use this model in your code:")
    print(option["usage"].format(path=model_path))

    return 0


if __name__ == "__main__":
    exit(main())
