# 🧠 E-Waste Management System: Comprehensive AI Hand-Off Guide

This document serves as a complete technical guide for any subsequent AI or developer taking over the project.

## 🚀 Project Overview
The system is built specifically to address **E-Waste in Maharashtra's Educational Sector**. It provides three core functionalities:
1. **Device Lifespan Predictor:** Predicts the Remaining Useful Life (RUL) of IT Lab equipment.
2. **E-Waste Image Scanner:** Classifies images of electronic hardware and assesses environmental/recycling impact.
3. **Automated Compliance Reporting:** Generates professional PDF sustainability reports for institutions.

---

## 🛠️ Key Features
- **Zero-Shot CLIP Classification:** Real-time internet-backed hardware identification.
- **XGBoost Prognosis:** High-precision lifespan regression (R²=0.96).
- **Live Weather Integration:** Real-time environmental stress indexing (Open-Meteo).
- **Financial Analyzer:** Localized Repair vs. Replace cost comparison.
- **PDF Report Engine:** Instant generation of institutional sustainability documents via `html2pdf.js`.
- **Backend:** FastAPI (Python)
- **Frontend:** React + Vite + Tailwind CSS
- **Database/Storage:** SQLite (History logging), local filesystem for images.
- **ML Infrastructure:** PyTorch, XGBoost, Scikit-Learn, Transformers (Hugging Face).

---

## 🧠 Machine Learning Models

### 1. Lifespan Prediction Engine (Prognosis)
*   **Path:** `backend/models/lifespan/xgboost_model.pkl`
*   **Type:** XGBoost Regressor (Trained with R² = ~0.96)
*   **Target:** `Remaining_Useful_Life`
*   **Features Used (Maharashtra Context):** `Device_Type`, `Region`, `Current_Age_Years`, `Usage_Hours_Per_Day`, `Dust_Index`, `Humidity_Index`, `Temperature_Stress`, `Power_Outage_Freq`, `Maintenance_Frequency`.
*   **Additional UI Logic:** A **Deep Diagnostic Assessment** (checkboxes for physical damage, overheating) applies a penalty multiplier (up to 70% RUL reduction) directly on the frontend for immediate conditional adjusting.

### 2. Image Scanner (Classifier)
*   **Path:** `backend/utils/model.py` -> `EfficientNetClassifier`
*   **Type:** Zero-Shot Image Classification (OpenAI CLIP via `transformers` pipeline: `openai/clip-vit-base-patch32`).
*   **Target Classes (10):** `"Motherboard", "Hard Disk / SSD", "Monitor", "Mouse", "Keyboard", "Smartphone", "Computer", "Printer", "Projector", "Router / Switch"`.
*   **Logic:** A confidence threshold of `< 0.10` rejects invalid images, prompting the user to upload correctly. It dynamically maps to `CO2_PROFILES` to generate environmental deltas.

---

## 🌐 External APIs Used
*   **Open-Meteo Weather API:** Fetches live `relative_humidity_2m` and `temperature_2m` based on Maharashtra region selection.
*   **Open-Meteo Air Quality API:** Fetches live `pm10` (Dust Index).
*   **Hugging Face Hub:** Hosted the CLIP weights for Zero-Shot image classification.

---

## 📂 Key File Structure
*   `backend/app/main.py`: FastAPI entry point.
*   `backend/app/routers/prognosis.py`: Houses the XGBoost inference logic, CO2 profiles, and Repair vs. Replace Cost matrices.
*   `backend/app/routers/classifier.py`: Handles file uploads, interfaces with the CLIP model, detects image conditions via pixel intensity.
*   `backend/utils/model.py`: Wraps the Hugging Face pipeline.
*   `frontend/src/components/LifespanPredictor.jsx`: Core UI for lifespan prediction, holds cascading dropdown logic (Brands) and live weather fetch hooks.
*   `frontend/src/components/Scanner.jsx`: UI for the image drag-and-drop classification.

---

## 💡 Future Expansion Ideas (Roadmap)
If continuing development, consider implementing:
1.  **Live Scrap Value Estimator:** Scrape live commodity prices (Copper, Gold) to estimate recovery value for scanned items.
2.  **Automated EPR PDF Reporting:** Generate official Extended Producer Responsibility compliance PDFs for the schools.
3.  **MPCB Geo-Locator:** Map integration showing the nearest Maharashtra Pollution Control Board (MPCB) certified e-waste dismantlers based on the user's location.

**End of Handoff.**
