# 🎯 Project Execution Plan: AI-Driven E-Waste Management (Maharashtra Education Sector)

This document outlines the roadmap to align the project with the research objective: **Predicting and managing e-waste in Maharashtra's IT labs using integrated AI models.**

---

## 1. Core Objectives (Aligned with PPT)
- **Precision Lifespan Prediction:** Compulsory use of **XGBoost** and **Random Forest** to predict Remaining Useful Life (RUL) of IT lab equipment.
- **IT Lab Hardware Classification:** Specialized CNN to identify: **Motherboard, Hard Disk/SSD, Mouse, Computer (Desktop/Laptop), Monitor, Smartphone.**
- **Environmental Impact Analysis:** Calculate CO2 footprint based on Maharashtra grid intensity (~0.71 kg CO2/kWh) and regional failure factors (Dust, Humidity, Power Quality).

---

## 2. Methodology for High Accuracy

### 📊 Phase 1: Lifespan Prediction (The Prognosis Engine)
We will move beyond simple formulas to real ML models trained on simulated Maharashtra conditions.
- **Models:** XGBoost (Gradient Boosting) + Random Forest (Bagging).
- **Compulsory Input Features (Maharashtra Context):**
    - `Age`: Time since manufacturing.
    - `Environment_Dust`: Regional index (High for rural/semi-urban MH).
    - `Environment_Humidity`: (High for coastal Konkan/Mumbai).
    - `Power_Quality`: Frequency of voltage spikes/outages (High in rural MH).
    - `Usage_Hours`: Daily lab hours.
    - `Maintenance_Score`: Frequency of professional servicing.
- **Accuracy Strategy:** We will use **Cross-Validation (5-fold)** and **Hyperparameter Tuning (GridSearch)** to ensure the models achieve >95% precision.

### 🖼️ Phase 2: AI Classification (The Scanner)
We will transition the current 2-class model to a **10-class "IT Lab Kit"** model.
- **Target Classes:** `Motherboard`, `Hard Disk / SSD`, `Monitor`, `Mouse`, `Keyboard`, `Smartphone`, `Computer`, `Printer`, `Projector`, `Router / Switch`.
- **Classification Output:**
    - **Identification:** What the product is.
    - **E-Waste Status:** E-Waste vs. Recyclable vs. Repairable.
    - **Detailed Info:** Material composition (Lead, Mercury, Gold, Plastic) and recycling path.
- **Accuracy Strategy:** Use a **ResNet50 Backbone** fine-tuned on high-quality hardware failure datasets.

---

## 3. Execution Roadmap

| Step | Action | Tech Stack |
| :--- | :--- | :--- |
| **1** | **Dataset Synthesis** | Create a dataset of 5,000+ IT lab devices representing MH environmental conditions. |
| **2** | **Lifespan Model Training** | Train **XGBoost** and **Random Forest** models. Compare accuracy metrics. |
| **3** | **CNN Expansion** | Fine-tune the CNN for the 6 specific IT lab hardware classes. |
| **4** | **API Integration** | Update FastAPI `/api/v1/predict` to use XGBoost/RF and `/api/v1/scan` for 6 classes. |
| **5** | **UI Maintenance** | Keep the existing UI but update descriptions and result cards for IT lab focus. |

---

## 4. How the Output will be Accurate
1.  **Context-Aware Features:** Unlike generic models, ours will include "Maharashtra Dust Index" and "Power Outage Frequency," which are the actual killers of hardware in Zilla Parishad and local schools.
2.  **Ensemble Approach:** The system will run *both* XGBoost and Random Forest, providing the most stable prediction.
3.  **H200 Inference:** The classification will run on high-performance infrastructure to ensure real-time, high-confidence results.

---

**Next Step:** I will begin by implementing the **XGBoost and Random Forest** training script to replace the current simulation logic.
