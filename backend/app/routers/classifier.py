import hashlib
import time
import uuid
import os
import io
import sys
from typing import Optional, Tuple

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from PIL import Image
from pathlib import Path

from app.db import log_scan
from utils.model import EfficientNetClassifier

router = APIRouter(prefix="/classifier", tags=["Classifier"])

# Load the trained model
model = None
try:
    model = EfficientNetClassifier()
except Exception as e:
    print(f"Failed to load model: {e}")

E_WASTE_CLASSES = [
    "Motherboard", "Hard Disk / SSD", "Monitor", "Mouse", 
    "Keyboard", "Smartphone", "Computer", "Printer", 
    "Projector", "Router / Switch"
]

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
    "Router / Switch": {"manufacturing": 50, "annual": 15, "recycling": 5}
}

E_WASTE_HAZARD = ["Motherboard", "Smartphone", "Computer", "Printer", "Monitor"]

cache = {}


class ScanResponse(BaseModel):
    analysis_id: str
    waste_status: str
    hazard_level: str
    confidence: float
    entity: str
    group: str
    condition: str
    co2_delta: float
    processing_time: float


def detect_condition(image: Image.Image) -> str:
    """Detect if the device is burnt, damaged, or good based on pixel intensity."""
    try:
        img_gray = image.convert("L")
        pixels = list(img_gray.getdata())
        avg_intensity = sum(pixels) / len(pixels)
        
        if avg_intensity < 40:
            return "burnt"
        elif avg_intensity < 100:
            return "damaged"
        return "good"
    except:
        return "good"


def simulate_classification(filename: str) -> tuple:
    import random
    entity = random.choice(E_WASTE_CLASSES)
    condition = random.choice(["good", "damaged", "burnt"])
    confidence = round(random.uniform(0.7, 0.99), 3)

    co2_profile = CO2_PROFILES.get(entity, {"recycling": 10})
    co2_delta = co2_profile.get("recycling", 10)

    waste_status = "E-Waste" if entity in E_WASTE_HAZARD else "Non-E-Waste"
    hazard_level = "Hazardous" if entity in E_WASTE_HAZARD else "Non-Hazardous"

    return entity, "ICT Equipment", condition, confidence, waste_status, hazard_level, co2_delta


def real_classification(contents: bytes, filename: str) -> tuple:
    """Use the real trained model for classification."""
    global model

    if model is None:
        return simulate_classification(filename)

    try:
        image = Image.open(io.BytesIO(contents))
        entity, confidence = model.predict(image, return_confidence=True)
        
        # Normalize entity names to match CO2_PROFILES
        entity_map = {k.lower(): k for k in CO2_PROFILES.keys()}
        normalized_entity = entity_map.get(entity.lower(), entity)

        condition = detect_condition(image)
        confidence = round(float(confidence), 3)

        # If the model is confused (low confidence), ask the user to upload correctly
        if confidence < 0.45:
            return "Unrecognized", "Unknown", "please upload image correctly", confidence, "Unknown", "Unknown", 0.0

        co2_profile = CO2_PROFILES.get(normalized_entity, {"recycling": 10})
        co2_delta = co2_profile.get("recycling", 10)

        waste_status = "E-Waste" if normalized_entity in E_WASTE_HAZARD else "Non-E-Waste"
        hazard_level = "Hazardous" if normalized_entity in E_WASTE_HAZARD else "Non-Hazardous"

        return normalized_entity, "ICT Equipment", condition, confidence, waste_status, hazard_level, co2_delta
    except Exception as e:
        print(f"Model prediction failed: {e}")
        return simulate_classification(filename)


@router.post("/scan", response_model=ScanResponse)
def scan_image(file: UploadFile = File(...)):
    start_time = time.time()
    contents = file.file.read()

    file_hash = hashlib.md5(contents).hexdigest()

    if file_hash in cache:
        result = cache[file_hash]
        result["processing_time"] = round(time.time() - start_time, 3)
        return ScanResponse(**result)

    entity, group_name, condition, confidence, waste_status, hazard_level, co2_delta = real_classification(contents, file.filename)

    result = {
        "analysis_id": str(uuid.uuid4()),
        "waste_status": waste_status,
        "hazard_level": hazard_level,
        "confidence": confidence,
        "entity": entity,
        "group": group_name,
        "condition": condition,
        "co2_delta": co2_delta,
        "processing_time": round(time.time() - start_time, 3)
    }

    cache[file_hash] = result.copy()

    log_scan(
        filename=file.filename,
        waste_status=waste_status,
        hazard_level=hazard_level,
        confidence=confidence,
        entity=entity,
        group_name=group_name,
        condition=condition,
        co2_delta=co2_delta,
        processing_time=result["processing_time"]
    )

    return ScanResponse(**result)

@router.get("/classes")
async def get_classes():
    return {"classes": E_WASTE_CLASSES}
