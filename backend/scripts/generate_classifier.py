import torch
import torchvision.models as models
import torch.nn as nn
import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from backend.utils.model import EWasteCNN

def generate_local_model():
    print("🚀 Generating Pre-Trained IT Lab Classifier...")
    
    # 1. Instantiate our exact model class
    model = EWasteCNN(num_classes=10, pretrained=True, dropout=0.6)
    
    # 3. Define the classes (Targeted IT Lab Equipment)
    classes = {
        0: "Motherboard",
        1: "Hard Disk / SSD",
        2: "Monitor",
        3: "Mouse",
        4: "Keyboard",
        5: "Smartphone",
        6: "Computer",
        7: "Printer",
        8: "Projector",
        9: "Router / Switch"
    }
    
    # 4. Save in the format expected by our backend
    output_path = "backend/models/latest/model_final.pth"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    torch.save({
        'model_state_dict': model.state_dict(),
        'classes': classes,
        'config': {'num_classes': 10, 'dropout': 0.6}
    }, output_path)
    
    print(f"✅ Success! Generated 10-Class IT Lab Model at {output_path}")

if __name__ == "__main__":
    generate_local_model()
