"""
E-Waste Data Preprocessing Pipeline
====================================
Loads, cleans, merges, and augments all e-waste datasets.

Unified label mapping:
- laptop: laptop, notebook, netbook
- mobile: mobile, smartphone, phone, tablet
- printer: printer, scanner, copier, fax
- components: pcb, battery, cpu, ram, hdd, ssd, cable, power_supply, etc.

Example:
    from scripts.data_loader import EwasteDataLoader

    loader = EwasteDataLoader("data/processed")
    train_loader, val_loader, test_loader = loader.load_all()

    for images, labels in train_loader:
        print(images.shape, labels.shape)  # [64, 3, 224, 224], [64]
"""

import json
import os
import pickle
import random
import shutil
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
from tqdm import tqdm

import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler, Subset
from torchvision import transforms

# Try to import albumentations, but it's optional
try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    HAS_ALBUMENTATIONS = True
except ImportError:
    HAS_ALBUMENTATIONS = False
    A = None
    ToTensorV2 = None

HAS_TORCH = True

import logging


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create a module-level logger with a consistent format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


# Unified label mapping - 8 e-waste categories
UNIFIED_LABELS = {
    "laptop": ["laptop", "Laptop", "LAPTOP", "notebook", "netbook", "laptops", "macbook", "computer_laptop"],
    "Mobile": ["Mobile", "mobile", "MOBILE", "cellphone", "cell_phone", "smartphone", "phone", "cellular", "iphone", "android", "ipad", "samsung", "tablet", "tablet_pc"],
    "Mouses": ["Mouses", "Mouse", "mouse", "Mice", "mice", "trackball", "track_pad"],
    "TV": ["TV", "tv", "Television", "television"],
    "camera": ["camera", "Camera", "webcam", "web_cam", "digital_camera", "photo_camera", "video_camera"],
    "microwave": ["microwave", "Microwave", "MICROWAVE", "microwave_oven"],
    "smartwatch": ["smartwatch", "Smartwatch", "SMARTWATCH", "watch", "fitness_tracker", "wearable"],
    "Keyboards": ["Keyboards", "Keyboard", "keyboard", "keyboards"]
}

# Dataset-specific label mappings
DATASET_LABELS = {
    "e_waste_net": {
        "laptop": ["laptop"],
        "Mobile": ["Mobile"],
        "Mouses": ["Mouses"],
        "TV": ["TV"],
        "camera": ["camera"],
        "microwave": ["microwave"],
        "smartwatch": ["smartwatch"],
        "Keyboards": ["Keyboards"]
    },
    "synthetic": {
        "laptop": ["laptop"],
        "Mobile": ["mobile"]
    }
}

IMAGE_SIZE = 224
MEAN = [0.485, 0.456, 0.406]  # ImageNet mean
STD = [0.229, 0.224, 0.225]   # ImageNet std


class EwasteImageDataset(Dataset):
    """PyTorch Dataset for e-waste images."""

    def __init__(
        self,
        image_paths: List[Path],
        labels: List[int],
        transform: Optional = None,
        cache_dir: Optional[Path] = None
    ):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform
        self.cache_dir = cache_dir

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        img_path = self.image_paths[idx]
        label = self.labels[idx]

        # Load image
        try:
            image = self._load_image(img_path)
        except Exception as e:
            # Return a placeholder if image fails to load
            print(f"Failed to load {img_path}: {e}")
            image = Image.new('RGB', (IMAGE_SIZE, IMAGE_SIZE), color='gray')

        # Apply transforms
        if self.transform:
            if HAS_TORCH and self.transform is not None:
                # Check if we have albumentations available
                if HAS_ALBUMENTATIONS and A is not None and isinstance(self.transform, A.Compose):
                    import numpy as np
                    # Albumentations expects numpy array
                    image = np.array(image)
                    image = self.transform(image=image)['image']
                else:
                    # Use torchvision transforms
                    image = self.transform(image)

        return image, label

    def _load_image(self, img_path: Path) -> Image.Image:
        """Load and preprocess image."""
        with Image.open(img_path) as img:
            # Convert to RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return img.copy()

    def get_class_distribution(self) -> Dict[int, int]:
        """Get number of samples per class."""
        return dict(Counter(self.labels))


class EwasteDataLoader:
    """Main data loader for e-waste classification."""

    LABEL_MAP = {i: name for i, name in enumerate(UNIFIED_LABELS.keys())}
    REVERSE_LABEL_MAP = {name: i for i, name in enumerate(UNIFIED_LABELS.keys())}

    def __init__(
        self,
        data_dir: Union[str, Path] = "data/processed",
        batch_size: int = 64,
        num_workers: int = 4,
        balance_classes: bool = True,
        cache_dir: Optional[Union[str, Path]] = None,
        seed: int = 42
    ):
        """
        Initialize data loader.

        Args:
            data_dir: Path to processed data directory
            batch_size: Batch size for training
            num_workers: Number of data loading workers
            balance_classes: Whether to use weighted sampler for class balancing
            cache_dir: Directory to cache processed data
            seed: Random seed for reproducibility
        """
        if not HAS_TORCH:
            raise ImportError("Install PyTorch: pip install torch torchvision")

        self.data_dir = Path(data_dir).resolve()
        self.batch_size = batch_size
        # Mac M5 fix: use 0 workers to avoid multiprocessing issues
        import sys
        self.logger = setup_logger("ewaste_dataloader")
        if sys.platform == 'darwin':
            self.num_workers = 0
            self.logger.info("Mac detected: using num_workers=0 for stability")
        else:
            self.num_workers = num_workers
        self.balance_classes = balance_classes
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.seed = seed

        # Set seeds
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)

        self.train_transform = None
        self.val_transform = None
        self._setup_transforms()

    def _setup_transforms(self):
        """Setup image augmentation transforms."""
        if HAS_ALBUMENTATIONS:
            # Training transforms with augmentation (Albumentations)
            self.train_transform = A.Compose([
                A.Resize(IMAGE_SIZE, IMAGE_SIZE),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.2),
                A.RandomRotate90(p=0.3),
                A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.2,
                                  rotate_limit=30, p=0.5),
                A.OneOf([
                    A.RandomBrightnessContrast(p=1.0),
                    A.RandomGamma(p=1.0),
                    A.CLAHE(p=1.0),
                ], p=0.5),
                A.OneOf([
                    A.GaussNoise(var_limit=(10, 50), p=1.0),
                    A.ISONoise(intensity=(0.1, 0.3), p=1.0),
                    A.GaussianBlur(blur_limit=(3, 7), p=1.0),
                ], p=0.3),
                A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30,
                                    val_shift_limit=20, p=0.3),
                A.Normalize(mean=MEAN, std=STD),
                ToTensorV2()
            ])

            # Validation transforms (no augmentation)
            self.val_transform = A.Compose([
                A.Resize(IMAGE_SIZE, IMAGE_SIZE),
                A.Normalize(mean=MEAN, std=STD),
                ToTensorV2()
            ])
        else:
            # Fallback to torchvision transforms
            self.logger.warning("Albumentations not available, using torchvision")

            self.train_transform = transforms.Compose([
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomRotation(30),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
                transforms.ToTensor(),
                transforms.Normalize(mean=MEAN, std=STD)
            ])

            self.val_transform = transforms.Compose([
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(mean=MEAN, std=STD)
            ])

    def _map_label(self, original_label: str, dataset_name: str) -> Optional[int]:
        """Map original dataset label to unified label."""
        original_lower = original_label.lower().replace(' ', '_')

        # Check dataset-specific mapping first
        if dataset_name in DATASET_LABELS:
            for unified_name, originals in DATASET_LABELS[dataset_name].items():
                if original_lower in [o.lower() for o in originals]:
                    return self.REVERSE_LABEL_MAP[unified_name]

        # Fallback to general mapping
        for unified_name, aliases in UNIFIED_LABELS.items():
            if any(alias.lower().replace(' ', '_') in original_lower
                   or original_lower in alias.lower()
                   for alias in aliases):
                return self.REVERSE_LABEL_MAP[unified_name]

        return None

    def _get_label_from_path(self, img_path: Path) -> Optional[str]:
        """Extract label from directory structure."""
        # Try parent directory name as label
        parent = img_path.parent.name
        if parent not in ['processed', 'raw', 'images']:
            return parent

        # Try grandparent
        grandparent = img_path.parent.parent.name
        if grandparent not in ['processed', 'raw', 'images']:
            return grandparent

        return None

    def load_dataset(
        self,
        split: str = "train",
        datasets: Optional[List[str]] = None
    ) -> EwasteImageDataset:
        """
        Load dataset for given split.

        Args:
            split: 'train', 'val', or 'test'
            datasets: List of dataset names to include (None = all)

        Returns:
            EwasteImageDataset instance
        """
        cache_file = self.data_dir / f"{split}_data.pkl"

        # Try to load from cache
        if cache_file.exists():
            self.logger.info(f"Loading {split} data from cache...")
            with open(cache_file, 'rb') as f:
                paths, labels = pickle.load(f)
            self.logger.info(f"Loaded {len(paths)} images")
            transform = self.train_transform if split == "train" else self.val_transform
            return EwasteImageDataset(paths, labels, transform)

        # Load and process
        image_paths = []
        labels = []

        datasets_to_load = datasets or self._discover_datasets()

        for dataset_name in datasets_to_load:
            dataset_dir = self.data_dir / dataset_name
            if not dataset_dir.exists():
                self.logger.warning(f"Dataset directory not found: {dataset_dir}")
                continue

            self.logger.info(f"Loading {dataset_name}...")

            # Walk directory looking for images
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                for img_path in dataset_dir.rglob(f'*{ext}'):
                    if img_path.is_file():
                        # Try to extract label from path
                        original_label = self._get_label_from_path(img_path)
                        if original_label:
                            unified_idx = self._map_label(original_label, dataset_name)
                            if unified_idx is not None:
                                image_paths.append(img_path)
                                labels.append(unified_idx)

        self.logger.info(f"Found {len(image_paths)} valid images for {split}")

        # Split data
        if split == "all":
            paths = image_paths
            labs = labels
        else:
            paths, labs = self._split_data(image_paths, labels, split)

        # Cache processed data
        with open(cache_file, 'wb') as f:
            pickle.dump((paths, labs), f)
        self.logger.info(f"Cached {split} data to {cache_file}")

        transform = self.train_transform if split == "train" else self.val_transform
        return EwasteImageDataset(paths, labs, transform)

    def _discover_datasets(self) -> List[str]:
        """Discover available datasets in data directory."""
        datasets = []
        for item in self.data_dir.iterdir():
            if item.is_dir() and item.name not in ['logs', '__pycache__']:
                if any(f.suffix.lower() in ['.jpg', '.jpeg', '.png']
                       for f in item.rglob('*')):
                    datasets.append(item.name)
        return datasets

    def _split_data(
        self,
        paths: List[Path],
        labels: List[int],
        split: str,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15
    ) -> Tuple[List[Path], List[int]]:
        """Split data into train/val/test."""
        # Group by label for stratified split
        label_to_indices = {}
        for i, lbl in enumerate(labels):
            label_to_indices.setdefault(lbl, []).append(i)

        train_idx, val_idx, test_idx = [], [], []

        for lbl, indices in label_to_indices.items():
            n = len(indices)
            random.shuffle(indices)

            n_train = int(n * train_ratio)
            n_val = int(n * val_ratio)

            train_idx.extend(indices[:n_train])
            val_idx.extend(indices[n_train:n_train + n_val])
            test_idx.extend(indices[n_train + n_val:])

        if split == "train":
            return [paths[i] for i in train_idx], [labels[i] for i in train_idx]
        elif split == "val":
            return [paths[i] for i in val_idx], [labels[i] for i in val_idx]
        else:  # test
            return [paths[i] for i in test_idx], [labels[i] for i in test_idx]

    def load_all(
        self,
        datasets: Optional[List[str]] = None,
        train_split: float = 0.7,
        val_split: float = 0.15
    ) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """
        Load train/val/test data loaders.

        Args:
            datasets: List of dataset names to include
            train_split: Fraction for training
            val_split: Fraction for validation

        Returns:
            Tuple of (train_loader, val_loader, test_loader)
        """
        self.logger.info("Loading all datasets...")

        # Load or cache split indices
        split_cache = self.data_dir / "splits.pkl"

        if split_cache.exists():
            self.logger.info("Loading cached train/val/test splits...")
            with open(split_cache, 'rb') as f:
                all_data = pickle.load(f)
        else:
            # Load all data
            all_dataset = self.load_dataset("all", datasets)
            self.logger.info(f"Total samples: {len(all_dataset)}")

            # Split
            total = len(all_dataset)
            train_size = int(train_split * total)
            val_size = int(val_split * total)

            indices = list(range(total))
            random.shuffle(indices)

            train_idx = indices[:train_size]
            val_idx = indices[train_size:train_size + val_size]
            test_idx = indices[train_size + val_size:]

            all_data = {
                'image_paths': all_dataset.image_paths,
                'labels': all_dataset.labels,
                'train_idx': train_idx,
                'val_idx': val_idx,
                'test_idx': test_idx
            }

            with open(split_cache, 'wb') as f:
                pickle.dump(all_data, f)

        # Create datasets
        train_dataset = EwasteImageDataset(
            [all_data['image_paths'][i] for i in all_data['train_idx']],
            [all_data['labels'][i] for i in all_data['train_idx']],
            self.train_transform
        )
        val_dataset = EwasteImageDataset(
            [all_data['image_paths'][i] for i in all_data['val_idx']],
            [all_data['labels'][i] for i in all_data['val_idx']],
            self.val_transform
        )
        test_dataset = EwasteImageDataset(
            [all_data['image_paths'][i] for i in all_data['test_idx']],
            [all_data['labels'][i] for i in all_data['test_idx']],
            self.val_transform
        )

        # Log distributions
        for name, ds in [("Train", train_dataset), ("Val", val_dataset), ("Test", test_dataset)]:
            dist = ds.get_class_distribution()
            self.logger.info(f"{name}: {len(ds)} samples, " +
                           f"class dist: {dist}")

        # Get data loaders
        train_loader = self._get_dataloader(train_dataset, is_train=True)
        val_loader = self._get_dataloader(val_dataset, is_train=False)
        test_loader = self._get_dataloader(test_dataset, is_train=False)

        return train_loader, val_loader, test_loader

    def _get_dataloader(
        self,
        dataset: EwasteImageDataset,
        is_train: bool
    ) -> DataLoader:
        """Create DataLoader with optional class balancing."""
        sampler = None
        shuffle = is_train

        if is_train and self.balance_classes:
            # Compute class weights
            dist = dataset.get_class_distribution()
            total = len(dataset)
            num_classes = len(UNIFIED_LABELS)
            weights = [total / (num_classes * dist.get(i, 1)) for i in range(num_classes)]
            sample_weights = [weights[label] for label in dataset.labels]
            sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)
            shuffle = False  # Sampler handles shuffling

        return DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=shuffle,
            sampler=sampler,
            num_workers=self.num_workers,
            pin_memory=False,  # Disabled for MPS compatibility
            drop_last=is_train
        )

    def get_label_name(self, idx: int) -> str:
        """Get unified label name from index."""
        return self.LABEL_MAP.get(idx, "unknown")

    def get_num_classes(self) -> int:
        """Get number of unified classes."""
        return len(UNIFIED_LABELS)

    @staticmethod
    def clear_cache(data_dir: Union[str, Path]):
        """Clear all cached files."""
        data_path = Path(data_dir)
        for cache_file in data_path.glob("*.pkl"):
            cache_file.unlink()
        print(f"Cleared cache in {data_dir}")
