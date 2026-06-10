import hashlib
import time
import uuid
import io
from collections import OrderedDict
from typing import Optional

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from PIL import Image

from app.db import log_scan
from utils.model import EWasteClassifier, classifier

router = APIRouter(prefix="/classifier", tags=["Classifier"])

# Lazy load — model is only initialized on first scan request
_model = None
_model_load_failed = False


def get_model():
    """Get or initialize the e-waste classifier model."""
    global _model, _model_load_failed
    if _model is None and not _model_load_failed:
        try:
            _model = EWasteClassifier()
        except Exception as e:
            print(f"Failed to load model: {e}")
            _model_load_failed = True
    return _model


E_WASTE_CLASSES = [
    "Motherboard", "Hard Disk / SSD", "Monitor", "Mouse",
    "Keyboard", "Smartphone", "Computer", "Printer",
    "Projector", "Router / Switch", "Air Conditioner"
]

# Carbon profile per device — single source of truth shared with carbon.py and prognosis.py
CO2_PROFILES = {
    "Motherboard": {"manufacturing": 80, "annual": 10, "recycling": 5},
    "Hard Disk / SSD": {"manufacturing": 40, "annual": 5, "recycling": 2},
    "Monitor": {"manufacturing": 180, "annual": 40, "recycling": 18},
    "Mouse": {"manufacturing": 15, "annual": 1, "recycling": 1},
    "Keyboard": {"manufacturing": 20, "annual": 2, "recycling": 2},
    "Smartphone": {"manufacturing": 80, "annual": 20, "recycling": 10},
    "Computer": {"manufacturing": 300, "annual": 80, "recycling": 25},
    "Printer": {"manufacturing": 120, "annual": 30, "recycling": 15},
    "Projector": {"manufacturing": 150, "annual": 40, "recycling": 20},
    "Router / Switch": {"manufacturing": 50, "annual": 15, "recycling": 5},
    "Air Conditioner": {"manufacturing": 600, "annual": 250, "recycling": 60},
    "Microwave": {"manufacturing": 90, "annual": 25, "recycling": 8},
    "Television": {"manufacturing": 220, "annual": 60, "recycling": 22},
    "Camera": {"manufacturing": 60, "annual": 5, "recycling": 6},
    "Smartwatch": {"manufacturing": 30, "annual": 3, "recycling": 3},
    "Laptop": {"manufacturing": 200, "annual": 50, "recycling": 18},
}

# All e-waste devices contain hazardous components under E-Waste (Management) Rules, 2022.
# Lead (solder/PCBs), Mercury (CCFL backlights), Cadmium (batteries/chips),
# Lithium (batteries — fire hazard), Brominated Flame Retardants (plastics).
E_WASTE_HAZARD = [
    "Motherboard", "Smartphone", "Computer", "Printer", "Monitor",
    "Television", "Air Conditioner", "Laptop", "Hard Disk / SSD",
    "Keyboard", "Mouse", "Projector", "Router / Switch",
    "Microwave", "Camera", "Smartwatch", "Battery",
]

# Recyclability tier per device — High = standard e-waste recycling recovers most materials.
# Medium = needs specialized handling (refrigerants, toner, lamps). Low = limited recovery (burnt/composite).
RECYCLABILITY = {
    "Motherboard": "High",
    "Hard Disk / SSD": "High",
    "Monitor": "Medium",
    "Mouse": "High",
    "Keyboard": "High",
    "Smartphone": "High",
    "Computer": "High",
    "Printer": "Medium",
    "Projector": "Medium",
    "Router / Switch": "High",
    "Air Conditioner": "Medium",
    "Microwave": "Medium",
    "Television": "Medium",
    "Camera": "High",
    "Smartwatch": "High",
    "Laptop": "High",
}

# ── Map expanded zero-shot model labels → canonical CO2_PROFILES entity ───
LABEL_TO_ENTITY = {
    # Computing
    "laptop": "Laptop",
    "desktop computer": "Computer",
    "computer": "Computer",
    "motherboard": "Motherboard",
    "computer processor": "Motherboard",
    "ram module": "Motherboard",
    "graphics card": "Motherboard",
    "solid state drive": "Hard Disk / SSD",
    "hard disk drive": "Hard Disk / SSD",
    "hdd": "Hard Disk / SSD",
    "ssd": "Hard Disk / SSD",
    # Peripherals
    "computer mouse": "Mouse",
    "mouse": "Mouse",
    "mechanical keyboard": "Keyboard",
    "keyboard": "Keyboard",
    "computer monitor": "Monitor",
    "monitor": "Monitor",
    "display": "Monitor",
    "computer printer": "Printer",
    "printer": "Printer",
    "3d printer": "Printer",
    "computer projector": "Projector",
    "projector": "Projector",
    "webcam": "Camera",
    "computer speakers": "Smartwatch",
    "headphones": "Smartwatch",
    "computer headset": "Smartwatch",
    # Networking
    "wireless router": "Router / Switch",
    "router": "Router / Switch",
    "network switch": "Router / Switch",
    "modem": "Router / Switch",
    "network cable": "Router / Switch",
    # Mobile & Wearables
    "smartphone": "Smartphone",
    "mobile phone": "Smartphone",
    "phone": "Smartphone",
    "tablet": "Smartphone",
    "smartwatch": "Smartwatch",
    "fitness tracker": "Smartwatch",
    "wireless earbuds": "Smartwatch",
    "bluetooth earbuds": "Smartwatch",
    "earbuds": "Smartwatch",
    # Home Electronics
    "television": "Television",
    "led tv": "Television",
    "smart tv": "Television",
    "tv": "Television",
    "microwave oven": "Microwave",
    "microwave": "Microwave",
    "air conditioner": "Air Conditioner",
    "ac": "Air Conditioner",
    "washing machine": "Air Conditioner",
    "refrigerator": "Air Conditioner",
    "camera": "Camera",
    "digital camera": "Camera",
    "dslr camera": "Camera",
    "action camera": "Camera",
    # Power & Accessories
    "power bank": "Smartphone",
    "portable charger": "Smartphone",
    "battery pack": "Smartphone",
    "lithium battery": "Smartphone",
    "usb cable": "Router / Switch",
    "power adapter": "Router / Switch",
    "extension cord": "Router / Switch",
    "power strip": "Router / Switch",
    # Components
    "circuit board": "Motherboard",
    "electronic cable": "Router / Switch",
    "hdmi cable": "Router / Switch",
}


CACHE_MAX_SIZE = 500


class LRUCache(OrderedDict):
    def __init__(self, maxsize=CACHE_MAX_SIZE):
        super().__init__()
        self.maxsize = maxsize

    def get_item(self, key):
        if key not in self:
            return None
        self.move_to_end(key)
        return self[key]

    def set_item(self, key, value):
        if key in self:
            self.move_to_end(key)
        self[key] = value
        if len(self) > self.maxsize:
            self.popitem(last=False)


cache = LRUCache()


class ScanResponse(BaseModel):
    analysis_id: str
    waste_status: str
    hazard_level: str
    recyclable: bool
    recyclability: str
    confidence: float
    entity: str
    group: str
    condition: str
    co2_delta: float
    processing_time: float
    model_used: str
    disposal_advice: str
    rejection_reason: Optional[str] = None


def detect_condition(image: Image.Image) -> str:
    try:
        img_gray = image.convert("L")
        pixels = list(img_gray.getdata())
        avg_intensity = sum(pixels) / len(pixels)
        if avg_intensity < 40:
            return "burnt"
        elif avg_intensity < 100:
            return "damaged"
        return "good"
    except Exception:
        return "good"


def get_recyclability(entity: str, condition: str) -> tuple[bool, str]:
    """Return (is_recyclable, tier). Burnt items drop one tier."""
    if entity == "Unrecognized":
        return False, "Unknown"
    base = RECYCLABILITY.get(entity, "Medium")
    if condition == "burnt":
        downgrade = {"High": "Medium", "Medium": "Low", "Low": "Low"}
        base = downgrade.get(base, "Low")
    return True, base


def get_disposal_advice(entity: str, hazard_level: str, condition: str, recyclability: str) -> str:
    if entity == "Unrecognized":
        return "Image was not clear enough to identify the device. Please upload a clearer photo."

    if recyclability == "High":
        recover = " Most materials can be recovered through standard e-waste recycling."
    elif recyclability == "Medium":
        recover = " Requires specialized handling (e.g., refrigerants, toner, lamps) — use a certified recycler."
    else:
        recover = " Material recovery is limited; ensure hazardous components are isolated."

    base = f"This {entity} contains hazardous components (lead, mercury, cadmium, lithium, or flame retardants). Hand it over to a certified e-waste recycler authorized under E-Waste (Management) Rules, 2022."

    if condition == "burnt":
        return base + recover + " Note: The device appears burnt — handle with care during transport."
    if condition == "damaged":
        return base + recover + " Note: The device appears damaged — repair may not be feasible."
    return base + recover


def real_classification(contents: bytes, filename: str) -> dict:
    model = get_model()

    if model is None:
        return {
            "entity": "Unrecognized",
            "group": "Unknown",
            "condition": "model unavailable",
            "confidence": 0.0,
            "waste_status": "Unknown",
            "hazard_level": "Unknown",
            "co2_delta": 0.0,
            "model_used": "none",
            "rejection_reason": "model_unavailable",
        }

    try:
        image = Image.open(io.BytesIO(contents))
        entity, confidence, model_used = model.predict(image, return_confidence=True)

        # Handle 3-stage pipeline rejections
        if entity == "Unrecognized" or model_used.startswith("rejected_"):
            rejection_messages = {
                "rejected_image_too_small": "Image is too small to analyze. Please upload a larger photo.",
                "rejected_image_too_dark": "Image is too dark. Please upload a brighter photo.",
                "rejected_image_too_blurry": "Image is too blurry. Please upload a clearer photo.",
                "rejected_image_low_contrast": "Image has very low contrast. Please upload a clearer photo.",
                "rejected_non_electronic": "This image does not appear to contain an electronic device or e-waste item.",
                "siglip_low_confidence": "Could not identify the device with enough confidence. Please upload a clearer photo of the device.",
                "siglip_ambiguous": "The image is ambiguous — could not confidently determine the device type. Please try a different angle.",
                "clip_low_confidence": "Could not identify the device with enough confidence. Please upload a clearer photo of the device.",
                "clip_ambiguous": "The image is ambiguous — could not confidently determine the device type. Please try a different angle.",
                "none": "Image could not be processed. Please upload a valid image.",
                "error": "An error occurred during classification. Please try again.",
            }
            rejection_reason = model_used.replace("rejected_", "") if model_used.startswith("rejected_") else model_used
            return {
                "entity": "Unrecognized",
                "group": "Unknown",
                "condition": rejection_messages.get(model_used, "Image could not be classified."),
                "confidence": round(float(confidence), 3),
                "waste_status": "Unknown",
                "hazard_level": "Unknown",
                "co2_delta": 0.0,
                "model_used": model_used,
                "rejection_reason": rejection_reason,
            }

        # Successful classification — normalize entity
        entity = LABEL_TO_ENTITY.get(entity.lower(), entity)
        entity_map = {k.lower(): k for k in CO2_PROFILES.keys()}
        normalized_entity = entity_map.get(entity.lower(), entity)

        condition = detect_condition(image)
        confidence = round(float(confidence), 3)

        co2_profile = CO2_PROFILES.get(normalized_entity, {"recycling": 10})
        co2_delta = co2_profile.get("recycling", 10)

        waste_status = "E-Waste" if normalized_entity in CO2_PROFILES else "Non-E-Waste"
        hazard_level = "Hazardous" if normalized_entity in E_WASTE_HAZARD else "Non-Hazardous"

        return {
            "entity": normalized_entity,
            "group": "Electronics",
            "condition": condition,
            "confidence": confidence,
            "waste_status": waste_status,
            "hazard_level": hazard_level,
            "co2_delta": co2_delta,
            "model_used": model_used,
            "rejection_reason": None,
        }
    except Exception as e:
        print(f"Model prediction failed: {e}")
        return {
            "entity": "Unrecognized",
            "group": "Unknown",
            "condition": "An error occurred during classification.",
            "confidence": 0.0,
            "waste_status": "Unknown",
            "hazard_level": "Unknown",
            "co2_delta": 0.0,
            "model_used": "error",
            "rejection_reason": "error",
        }


@router.post("/scan", response_model=ScanResponse)
def scan_image(file: UploadFile = File(...)):
    start_time = time.time()
    contents = file.file.read()

    file_hash = hashlib.md5(contents).hexdigest()

    cached = cache.get_item(file_hash)
    if cached is not None:
        result = cached.copy()
        result["analysis_id"] = str(uuid.uuid4())
        result["processing_time"] = round(time.time() - start_time, 3)
        if result.get("entity") and result["entity"] != "Unrecognized":
            log_scan(
                filename=file.filename,
                waste_status=result["waste_status"],
                hazard_level=result["hazard_level"],
                confidence=result["confidence"],
                entity=result["entity"],
                group_name=result["group"],
                condition=result["condition"],
                co2_delta=result["co2_delta"],
                processing_time=result["processing_time"],
                recyclability=result.get("recyclability"),
                model_used=result.get("model_used"),
            )
        return ScanResponse(**result)

    cls = real_classification(contents, file.filename)

    recyclable, recyclability = get_recyclability(cls["entity"], cls["condition"])
    advice = get_disposal_advice(cls["entity"], cls["hazard_level"], cls["condition"], recyclability)

    result = {
        "analysis_id": str(uuid.uuid4()),
        "waste_status": cls["waste_status"],
        "hazard_level": cls["hazard_level"],
        "recyclable": recyclable,
        "recyclability": recyclability,
        "confidence": cls["confidence"],
        "entity": cls["entity"],
        "group": cls["group"],
        "condition": cls["condition"],
        "co2_delta": cls["co2_delta"],
        "processing_time": round(time.time() - start_time, 3),
        "model_used": cls["model_used"],
        "disposal_advice": advice,
        "rejection_reason": cls.get("rejection_reason"),
    }

    cache.set_item(file_hash, result.copy())

    if cls["entity"] != "Unrecognized":
        log_scan(
            filename=file.filename,
            waste_status=cls["waste_status"],
            hazard_level=cls["hazard_level"],
            confidence=cls["confidence"],
            entity=cls["entity"],
            group_name=cls["group"],
            condition=cls["condition"],
            co2_delta=cls["co2_delta"],
            processing_time=result["processing_time"],
            recyclability=recyclability,
            model_used=cls["model_used"],
        )

    return ScanResponse(**result)


@router.get("/classes")
async def get_classes():
    return {"classes": E_WASTE_CLASSES}
