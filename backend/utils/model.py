"""
Vision model wrapper with two-tier classification:
  Tier 1: Local trained ResNet-50 model (10 IT-lab classes)
  Tier 2: CLIP zero-shot fallback (broader e-waste coverage)
"""

import os
from pathlib import Path
from typing import Tuple, Union

import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image


LOCAL_CLASSES = [
    "Motherboard", "Hard Disk / SSD", "Monitor", "Mouse",
    "Keyboard", "Smartphone", "Computer", "Printer",
    "Projector", "Router / Switch"
]

# CLIP fallback covers items not in the local model — AC, Microwave, etc.
CLIP_LABELS = LOCAL_CLASSES + [
    "Air Conditioner", "Microwave", "Television", "Camera", "Smartwatch", "Laptop"
]

LOCAL_CONF_THRESHOLD = 0.55
CLIP_CONF_THRESHOLD = 0.45

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class EWasteCNN(nn.Module):
    """ResNet-50 backbone (bb) with a 2-layer classifier head matching the saved checkpoint."""

    def __init__(self, num_classes: int = 10, dropout: float = 0.6):
        super().__init__()
        self.bb = tv_models.resnet50(weights=None)
        # The saved checkpoint replaces bb.fc with: Dropout → Linear(2048,512) → ReLU → Dropout → Linear(512, num_classes)
        in_features = self.bb.fc.in_features  # 2048
        self.bb.fc = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        return self.bb(x)


class EfficientNetClassifier:
    """Two-tier classifier: local ResNet-50 first, CLIP zero-shot fallback for broader coverage."""

    def __init__(self, model_path: str = None, device: str = "auto"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Resolve checkpoint path
        if model_path is None:
            here = Path(__file__).resolve().parent
            model_path = str(here.parent / "models" / "latest" / "model_final.pth")
        self.model_path = model_path

        self.preprocess = T.Compose([
            T.Resize(256),
            T.CenterCrop(224),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])

        self.local_model = None
        self.local_classes = LOCAL_CLASSES
        self._load_local_model()

        self.clip_pipeline = None  # Lazy-initialized on first fallback use

    def _load_local_model(self):
        if not os.path.exists(self.model_path):
            print(f"Trained model not found at {self.model_path} — fallback only")
            return
        try:
            ckpt = torch.load(self.model_path, map_location="cpu", weights_only=False)
            if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
                state_dict = ckpt["model_state_dict"]
                config = ckpt.get("config", {})
                num_classes = config.get("num_classes", 10)
                dropout = config.get("dropout", 0.6)
                if "classes" in ckpt and isinstance(ckpt["classes"], list):
                    self.local_classes = ckpt["classes"]
            else:
                state_dict = ckpt
                num_classes = 10
                dropout = 0.6

            model = EWasteCNN(num_classes=num_classes, dropout=dropout)
            model.load_state_dict(state_dict, strict=False)
            model.eval()
            model.to(self.device)
            self.local_model = model
            print(f"Loaded trained ResNet from {self.model_path}")
        except Exception as e:
            print(f"Failed to load local trained model: {e}")
            self.local_model = None

    def _ensure_clip(self):
        if self.clip_pipeline is None:
            # CLIP fallback ~600MB; on by default, opt out on memory-constrained hosts
            # by setting ENABLE_CLIP_FALLBACK=0 (e.g. Render free tier).
            if os.getenv("ENABLE_CLIP_FALLBACK", "1") == "0":
                self.clip_pipeline = False
                return
            try:
                from transformers import pipeline
                dev_id = 0 if torch.cuda.is_available() else -1
                self.clip_pipeline = pipeline(
                    "zero-shot-image-classification",
                    model="openai/clip-vit-base-patch32",
                    device=dev_id,
                )
                print("Initialized CLIP fallback pipeline")
            except Exception as e:
                print(f"CLIP fallback unavailable: {e}")
                self.clip_pipeline = False  # Sentinel for "tried and failed"

    def _predict_local(self, image: Image.Image) -> Tuple[str, float]:
        if self.local_model is None:
            return None, 0.0
        try:
            tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = self.local_model(tensor)
                probs = torch.softmax(logits, dim=1)
                conf, idx = probs.max(dim=1)
            label = self.local_classes[idx.item()]
            return label, float(conf.item())
        except Exception as e:
            print(f"Local model inference failed: {e}")
            return None, 0.0

    def _predict_clip(self, image: Image.Image) -> Tuple[str, float]:
        self._ensure_clip()
        if not self.clip_pipeline:
            return None, 0.0
        try:
            results = self.clip_pipeline(image, candidate_labels=CLIP_LABELS)
            best = results[0]
            return best["label"], float(best["score"])
        except Exception as e:
            print(f"CLIP inference failed: {e}")
            return None, 0.0

    def predict(self, image: Image.Image, return_confidence: bool = True):
        """
        Returns (label, confidence, model_used) when return_confidence=True.
        model_used ∈ {"local", "clip_fallback", "none"}
        """
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Tier 1: local trained model
        local_label, local_conf = self._predict_local(image)
        if local_label is not None and local_conf >= LOCAL_CONF_THRESHOLD:
            return (local_label, local_conf, "local") if return_confidence else local_label

        # Tier 2: CLIP fallback for broader coverage
        clip_label, clip_conf = self._predict_clip(image)
        if clip_label is not None and clip_conf >= CLIP_CONF_THRESHOLD:
            return (clip_label, clip_conf, "clip_fallback") if return_confidence else clip_label

        # Neither tier confident enough
        if local_label is not None:
            # Surface the low-confidence local result for the caller to decide
            return (local_label, local_conf, "local_low_confidence") if return_confidence else local_label
        return ("Unrecognized", 0.0, "none") if return_confidence else "Unrecognized"
