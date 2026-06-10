"""
DEPRECATED: This script is no longer needed.

The e-waste classifier now uses Google's SigLIP-So400M model for zero-shot classification,
which works out of the box without requiring any local model training or generation.

The model is automatically downloaded and cached on first use from Hugging Face:
  https://huggingface.co/google/siglip-so400m-patch14-384

For reference, this script previously generated an untrained ResNet-50 model that was
never actually used for classification (the system always fell through to the zero-shot fallback).

The new implementation is in:
  backend/utils/model.py

To use the classifier, simply:
  1. Install dependencies: pip install -r requirements.txt
  2. Start the backend: uvicorn app.main:app --host 0.0.0.0 --port 8001
  3. The model will be downloaded automatically on first /scan request
"""

import sys


def generate_local_model():
    print("DEPRECATED: This script is no longer needed.")
    print("The e-waste classifier now uses Google's SigLIP-So400M for zero-shot classification.")
    print("No local model generation required.")
    print("")
    print("The model is automatically downloaded and cached on first use.")
    print("See backend/utils/model.py for the new implementation.")


if __name__ == "__main__":
    generate_local_model()
