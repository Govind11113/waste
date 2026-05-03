"""
Vision Model wrapper for inference and deployment.
Now upgraded to use Zero-Shot CLIP for maximum accuracy on custom classes.
"""

from typing import Union, Tuple
from PIL import Image
from transformers import pipeline
import torch

class EfficientNetClassifier:
    """High-Accuracy Zero-Shot IT Lab classifier using CLIP."""

    def __init__(self, model_path=None, device="auto"):
        print("🚀 Initializing High-Accuracy Zero-Shot Vision Model (CLIP)...")
        dev_id = 0 if torch.cuda.is_available() else -1
        self.classifier = pipeline(
            "zero-shot-image-classification", 
            model="openai/clip-vit-base-patch32", 
            device=dev_id
        )
        self.candidate_labels = [
            "Motherboard", "Hard Disk / SSD", "Monitor", "Mouse", 
            "Keyboard", "Smartphone", "Computer", "Printer", 
            "Projector", "Router / Switch"
        ]

    def predict(self, image: Image.Image, return_confidence=True) -> Union[str, Tuple[str, float]]:
        """Predict class for single image."""
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        results = self.classifier(image, candidate_labels=self.candidate_labels)
        
        best_match = results[0]
        label = best_match['label']
        confidence = best_match['score']
        
        if return_confidence:
            return label, confidence
        return label
