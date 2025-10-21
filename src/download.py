#!/usr/bin/env python3
"""
Model Download Script - Download and cache models locally
"""

from pathlib import Path
from sentence_transformers import SentenceTransformer
from transformers import AutoModel, AutoTokenizer, AutoModelForCausalLM

import json
import torch

def get_model_choice():
    """Prompt user to select which model to download"""
    print("\n🚀 Model Download Options")
    print("=" * 50)
    print("1. BGE-M3 (Embedding Model) - For text similarity and retrieval")
    print("2. LLaMA 3.2 3B Instruct (Language Model) - For text generation")
    print("=" * 50)

    while True:
        try:
            choice = input("Select model to download (1 or 2): ").strip()
            if choice == "1":
                return "bge_m3"
            elif choice == "2":
                return "llama"
            else:
                print("❌ Please enter 1 or 2")
        except KeyboardInterrupt:
            print("\n\n❌ Operation cancelled")
            exit(1)

def download_bge_m3():
    """Download BGE-M3 model and save it locally"""

    # Define local model path
    model_name = "BAAI/bge-m3"
    local_model_path = Path(__file__).parent.parent / "models" / "bge-m3"

    print(f"Model will be saved to: {local_model_path}")

    # Create models directory if it doesn't exist
    local_model_path.parent.mkdir(exist_ok=True)

    # Check if model already exists locally
    if local_model_path.exists() and any(local_model_path.iterdir()):
        print(f"\n✅ Model already exists at {local_model_path}")
        print("Loading from local cache...")
        model = SentenceTransformer(str(local_model_path))
    else:
        print(f"\n📥 Downloading model {model_name} from HuggingFace...")
        print("This may take a while on first download...")

        # Try different approaches to download the model
        try:
            # First attempt with trust_remote_code
            model = SentenceTransformer(model_name, trust_remote_code=True)
            model.save(str(local_model_path))
            print(f"\n✅ Model downloaded and saved to {local_model_path}")
        except Exception as e:
            print(f"\n⚠️  First attempt failed: {e}")
            print("Trying alternative download method...")

            # Alternative: Download using transformers directly
            try:
                print("Downloading model components separately...")
                tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
                model_transformer = AutoModel.from_pretrained(model_name, trust_remote_code=True)

                # Save components
                tokenizer.save_pretrained(str(local_model_path))
                model_transformer.save_pretrained(str(local_model_path))

                print("Loading as SentenceTransformer...")

                # Create missing configurations for BGE-M3
                print("Adding BGE-M3 specific configurations...")

                # Create modules.json
                modules_config = [
                    {"idx": 0, "name": "0", "path": "", "type": "sentence_transformers.models.Transformer"},
                    {"idx": 1, "name": "1", "path": "1_Pooling", "type": "sentence_transformers.models.Pooling"}
                ]
                modules_path = local_model_path / "modules.json"
                with open(modules_path, 'w') as f:
                    json.dump(modules_config, f, indent=2)

                # Create pooling configuration
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
                    "include_prompt": True
                }
                with open(pooling_dir / "config.json", 'w') as f:
                    json.dump(pooling_config, f, indent=2)

                model = SentenceTransformer(str(local_model_path))
                print(f"\n✅ Model downloaded and saved to {local_model_path}")
            except Exception as e2:
                print(f"\n❌ Alternative method also failed: {e2}")
                raise

    # Test the model
    print("\n🧪 Testing model...")
    test_sentences = [
        "This is a test sentence.",
        "BGE-M3 is a powerful embedding model.",
        "It supports multiple languages and long context."
    ]

    # Generate embeddings
    embeddings = model.encode(test_sentences, show_progress_bar=True)

    print("\n✅ Model loaded successfully!")
    print("📊 Model info:")
    print(f"   - Embedding dimension: {embeddings.shape[1]}")
    print(f"   - Max sequence length: {model.max_seq_length}")
    print(f"   - Device: {model.device}")

    # Show sample embeddings
    print("\n📝 Sample embeddings (first 5 dimensions):")
    for i, (sentence, embedding) in enumerate(zip(test_sentences, embeddings)):
        print(f"   {i+1}. '{sentence[:50]}...' -> {embedding[:5].tolist()}")

    return model, local_model_path

def download_llama():
    """Download LLaMA model and save it locally"""

    # Configuration: Set the model you want to download here
    MODEL_NAME = "context-labs/meta-llama-Llama-3.2-3B-Instruct-FP16"

    # Define local model path
    model_name = MODEL_NAME
    local_model_path = Path(__file__).parent.parent / "models" / MODEL_NAME.split('/')[-1]

    print(f"Model will be saved to: {local_model_path}")

    # Create models directory if it doesn't exist
    local_model_path.parent.mkdir(exist_ok=True)

    # Check if model already exists locally
    if local_model_path.exists() and any(local_model_path.iterdir()):
        print(f"\n✅ Model already exists at {local_model_path}")
        print("Loading from local cache...")

        tokenizer = AutoTokenizer.from_pretrained(str(local_model_path), trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            str(local_model_path),
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True
        )
    else:
        print(f"\n📥 Downloading model {model_name} from HuggingFace...")
        print("This may take a while on first download (approximately 15-16 GB)...")

        # Try different approaches to download the model
        try:
            # First attempt with trust_remote_code
            print("Downloading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

            print("Downloading model...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype="auto",
                device_map="auto",
                trust_remote_code=True
            )

            # Save both tokenizer and model
            print("Saving model and tokenizer locally...")
            tokenizer.save_pretrained(str(local_model_path))
            model.save_pretrained(str(local_model_path))

            print(f"\n✅ Model downloaded and saved to {local_model_path}")
        except Exception as e:
            print(f"\n⚠️  First attempt failed: {e}")
            print("Trying alternative download method...")

            # Alternative: Download with different parameters
            try:
                print("Trying alternative download method...")
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    use_fast=False  # Use slow tokenizer as fallback
                )

                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16,  # Use float16 to reduce memory
                    device_map="auto",
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )

                # Save both tokenizer and model
                tokenizer.save_pretrained(str(local_model_path))
                model.save_pretrained(str(local_model_path))

                print(f"\n✅ Model downloaded and saved to {local_model_path}")
            except Exception as e2:
                print(f"\n❌ Alternative method also failed: {e2}")
                raise

    # Test the model
    print("\n🧪 Testing model...")

    # Test prompt
    prompt = "Give me a short introduction to large language models."
    messages = [
        {"role": "user", "content": prompt}
    ]

    # Apply chat template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False  # Enable thinking mode for better reasoning
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    print("Generating response...")
    # Generate response
    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=512,  # Limit for testing
            temperature=0.6,
            top_p=0.95,
            top_k=20,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()

    # Parse thinking content and final response
    try:
        # Find </think> token (151668)
        index = len(output_ids) - output_ids[::-1].index(151668)
    except ValueError:
        index = 0

    thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
    content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

    print("\n✅ Model loaded successfully!")
    print("📊 Model info:")
    print(f"   - Device: {model.device}")
    print(f"   - Model path: {local_model_path}")

    # Show sample response
    print("\n📝 Sample response:")
    print(f"Prompt: '{prompt}'")
    if thinking_content:
        print(f"Thinking: '{thinking_content[:200]}...'")
    print(f"Response: '{content[:300]}...'")

    return model, tokenizer, local_model_path

def main():
    print("🚀 Unified Model Download Script")
    print("=" * 60)
    print("=" * 60)

    # Get user choice
    model_choice = get_model_choice()

    try:
        if model_choice == "bge_m3":
            print("\n🔍 Selected: BGE-M3 Embedding Model")
            print("-" * 40)
            model_path = download_bge_m3()
            print("\n✅ Success! BGE-M3 model is ready to use.")
            print("\n💡 To use this model in your code:")
            print("   from sentence_transformers import SentenceTransformer")
            print(f"   model = SentenceTransformer('{model_path}')")
        else:
            print("\n🤖 Selected: LLaMA 3.2 3B Instruct Language Model")
            print("-" * 50)
            model_path = download_llama()
            print("\n✅ Success! LLaMA model is ready to use.")
            print("\n💡 To use this model in your code:")
            print("   from transformers import AutoModelForCausalLM, AutoTokenizer")
            print(f"   tokenizer = AutoTokenizer.from_pretrained('{model_path}', trust_remote_code=True)")
            print(f"   model = AutoModelForCausalLM.from_pretrained('{model_path}', torch_dtype='auto', device_map='auto', trust_remote_code=True)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have internet connection")
        print("2. Check if you need to set proxy settings")
        print("3. Ensure you have enough disk space")
        print("4. Try running with: PYTHONWARNINGS='ignore' python3 download.py")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())