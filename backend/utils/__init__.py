"""Utility modules for E-Waste AI."""

from .logger import setup_logger
from .data_loader import EwasteDataLoader, EwasteImageDataset, UNIFIED_LABELS

try:
    from .model import EfficientNetClassifier, EnsembleClassifier
    from .yolo_detector import ComponentDetector, MultiModelDetector
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    EfficientNetClassifier = EnsembleClassifier = ComponentDetector = MultiModelDetector = None

__all__ = [
    "setup_logger",
    "EwasteDataLoader",
    "EwasteImageDataset",
    "UNIFIED_LABELS",
    "EfficientNetClassifier",
    "EnsembleClassifier",
    "ComponentDetector",
    "MultiModelDetector"
]
