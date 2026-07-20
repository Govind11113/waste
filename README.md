# E-Waste Management System

A full-stack decision-support prototype for electronic-waste workflows in Maharashtra educational institutions. The application classifies device images with a pre-trained vision-language model, estimates remaining device life, calculates scenario-based carbon footprints, projects submitted inventory cohorts through an assumption-based survival curve, stores per-user activity history, and produces PDF reports. A separate command-line tool computes ISM/MICMAC outputs from user-supplied judgments.

> **Evidence boundary:** this repository is a working software prototype, not a completed empirical study. The lifespan training data are synthetic, the image classifier has no committed held-out real-image benchmark, carbon outputs are deterministic planning estimates, the cohort forecast uses a fixed uncalibrated survival assumption, and the ISM tool contains no survey responses. No research hypothesis should be reported as confirmed from this code alone.

## Implemented capabilities

- **Zero-shot image classifier:** a three-stage pipeline (image-quality gate → electronics gate → canonical device classification) in `backend/app/model.py`. It performs inference with a pre-trained Google SigLIP 2 or OpenAI CLIP vision-language model; it is **not a locally trained CNN**.
- **20 canonical classifier outputs:** Laptop, Computer, Smartphone, Monitor, Keyboard, Mouse, Printer, Projector, Router / Switch, Motherboard, Hard Disk / SSD, Air Conditioner, Television, Microwave, Camera, Smartwatch, Battery, Washing Machine, Refrigerator, and Remote Control. Prompt aliases do not create additional output classes.
- **Lifespan estimator:** the API defaults to a transparent seven-factor weighted formula. Optional Random Forest, XGBoost, and LightGBM pipelines are available for comparison, but their committed artifacts were fitted to synthetic data.
- **Carbon calculator:** deterministic embodied-plus-operational calculations using device profiles, user inputs, energy-rating multipliers, and postal-code/prefix grid-intensity lookups. This is arithmetic estimation, not a trained carbon-prediction model or certified life-cycle assessment.
- **Cohort planning forecast:** authenticated `POST /api/v1/generation/forecast` projects user-submitted, currently in-service cohorts with a conditional Weibull curve, profile lifespan/weight, and a lifespan-sensitivity envelope. It fits no model and is not calibrated to observed failures or disposal records.
- **ISM/MICMAC calculation tool:** `backend/scripts/ism_micmac.py` validates a complete user-supplied SSIM or binary relationship matrix, then calculates transitive reachability, ISM levels, driving/dependence power, and MICMAC classes. It generates or imputes no expert response.
- **History, reports, and regional UI:** Clerk-authenticated activity history in local SQLite, downloadable reports, and a Leaflet-based Maharashtra view.

## Method terminology

### Seven lifespan factors

The implemented health score is:

```text
H = Σ(i=1..7) w_i f_i, where Σw_i = 1
Remaining life = clamp(base lifespan × H − current age, 0, base lifespan − current age)
```

The seven factors are **age/manufacturing (A), usage (U), temperature (T), power quality (P), environment (E), maintenance/service (M), and software/workload (S)**. Use `f_i(A,U,T,P,E,M,S)` or name the factors explicitly. The older six-symbol notation `f_i(M,T,E,U,P,S)` omitted or conflated a factor and must not be described as seven-factor.

### Class and dataset counts

The runtime classifier and shared device profiles contain **20** canonical device categories. The current synthetic lifespan generator contains **19** device types because it does not generate Remote Control rows. The formula still has a Remote Control profile, while an ML prediction for that unseen category relies on the encoder's unknown-category behavior. Keep these counts distinct in reports.

## Technology

- Backend: Python 3.11, FastAPI, PyTorch, Hugging Face Transformers, scikit-learn, XGBoost, LightGBM, SQLite
- Frontend: React 19, Vite, Tailwind CSS 4, Clerk, Leaflet, html2pdf.js

## Self-contained Windows localhost release

The Windows design uses a PyInstaller **one-folder** build: one extracted folder contains the Python runtime, FastAPI backend, production React SPA, lifespan artifacts, and a pinned SigLIP 2 snapshot. The receiving Windows 10/11 x64 PC needs no Python or Node.js. FastAPI serves the SPA and `/api` from `http://127.0.0.1:8000`; mutable configuration, SQLite data, logs, and backups stay under `%LOCALAPPDATA%\EWasteManagement`.

Builds must run natively on Windows x64 with `packaging/windows/build-release.ps1`; PyInstaller cannot produce a Windows executable on macOS. See [WINDOWS_INSTALL.md](WINDOWS_INSTALL.md) for receiving-PC setup and [WINDOWS_ACCEPTANCE.md](WINDOWS_ACCEPTANCE.md) for the explicit validation boundary and workflow checklist. The localhost release requires an online Clerk development (`pk_test_`) instance; classifier weights are bundled and integrity-verified offline.

## Reproducible local setup

Use Python **3.11**. The requirements files pin direct dependencies to versions observed in the project environments; they are not a complete hash-locked record of every transitive wheel.

### Backend — macOS

```bash
cd backend
python3.11 -m venv .venv
./.venv/bin/python -m pip install -r requirements-mac.txt
cp .env.example .env
# Replace the Clerk placeholder values in .env.
cd ..
./run_backend.sh
```

### Backend — Linux CPU

```bash
cd backend
python3.11 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Replace the Clerk placeholder values in .env.
cd ..
./run_backend.sh
```

`run_backend.sh` prefers `backend/.venv`, then `backend/venv`, and otherwise uses `python3`. It defaults to `http://127.0.0.1:8000`, loads `backend/.env` through Uvicorn before importing the app, and does **not** force Hugging Face offline mode. See `./run_backend.sh --help` for host, port, and reload options.

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env
# Set a valid VITE_CLERK_PUBLISHABLE_KEY.
cd ..
./run_frontend.sh
```

The frontend defaults to `http://127.0.0.1:5173`. See `./run_frontend.sh --help` to change the host or port. The backend API documentation is at `http://127.0.0.1:8000/docs`; protected routes require a valid Clerk session. Liveness and readiness are exposed at `/health/live` and `/health/ready`. If `frontend/dist` exists, FastAPI also serves the production SPA and deep links from `/`.

## Hugging Face model behavior

`EWASTE_MODEL=siglip2-base` is the default. Primary alternatives in the code are `siglip2-so400m-256`, `siglip2-so400m-384`, `siglip2-so400m-512`, `siglip2-large-512`, `siglip2-giant-384`, and `clip-base`. Larger names indicate larger model presets, not measured superiority in this project; no comparative classifier benchmark is committed.

On first use, missing weights are downloaded from Hugging Face. To prepare an offline run, cache the exact selected model while online, for example:

```bash
cd backend
./.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('google/siglip2-base-patch16-224')"
cd ..
HF_HUB_OFFLINE=1 ./run_backend.sh
```

Offline source mode succeeds only when all selected model files are already present in the cache. The Windows release is stricter: `scripts/prepare_classifier_model.py` downloads exact revision `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2` into a flat snapshot, adds license/metadata, and hashes every file. The frozen app sets `HF_HUB_OFFLINE=1`, requires that local snapshot, and never falls back to a receiving-PC download.

## Research and model workflows

### Synthetic lifespan benchmark

From `backend/`:

```bash
./.venv/bin/python scripts/generate_dataset.py --rows 2000 --seed 42
./.venv/bin/python scripts/train_lifespan_v2.py
# Explicitly replace v2 artifacts only when intended:
./.venv/bin/python scripts/train_lifespan_v2.py --write-artifacts
```

The generator uses a fixed reference year, seeded category sampling, hand-authored priors, a rule-based target, and injected random noise. The trainer compares the unfit seven-factor formula with Linear Regression, Random Forest, XGBoost, and LightGBM on a holdout from that same synthetic process. `training_metrics.json` therefore records **synthetic holdout behavior only**; it cannot establish external validity, causal effects, field accuracy, or a tested hypothesis. The legacy `scripts/train_lifespan.py` is disabled and cannot write artifacts.

When `--write-artifacts` is supplied, the v2 trainer writes the three deployed pipelines, feature metadata, synthetic metrics, and a SHA-256 manifest containing only current v2 pickle artifacts. Run `python3 scripts/train_lifespan_v2.py --help` for path and determinism options.

### Classifier diagnostics and evaluation

```bash
# Deterministic local quality-gate checks; no model download:
./.venv/bin/python scripts/test_classifier.py

# Optional inference smoke check (may download the selected model):
./.venv/bin/python scripts/test_classifier.py --model

# Per-stage scores for a local image:
./.venv/bin/python scripts/diag_classifier.py --image /path/to/device.jpg
```

These commands are diagnostics, not accuracy studies. For an actual benchmark, prepare a fixed held-out CSV with `path,label` columns and run:

```bash
./.venv/bin/python scripts/evaluate_classifier.py \
  --manifest /path/to/held_out_labels.csv \
  --output /path/to/evaluation.json
```

The evaluator reports all-image accuracy, recognized-image accuracy, coverage/rejection, and per-class counts. Those values are meaningful only to the extent that the supplied real-image set is representative and was not used to tune prompts or thresholds.

### Cohort generation planning

The forecast accepts one or more cohorts with canonical device type, in-service quantity, and current average age. For quantity `Q`, current age `a`, profile lifespan `L`, elapsed year `t`, and fixed shape `k=3`:

```text
R(t|a) = exp[-ln(2) × (((a+t)/L)^k − (a/L)^k)]
annual expected EOL(t) = Q × (R(t−1|a) − R(t|a))
```

`L` is treated as median end-of-life age by assumption. Device mass comes from the shared profile. The API also varies lifespan by the submitted sensitivity fraction (default ±20%) to produce a scenario envelope. That envelope is **not** a probability/confidence interval. The curve is not estimated from data, no future purchases are added, and projected end-of-life is not the same as observed waste collection.

### ISM/MICMAC calculation

Copy `backend/data/templates/ism_ssim_template.csv`, add exactly one real judgment for every unordered factor pair using `V`, `A`, `X`, or `O`, then run:

```bash
cd backend
./.venv/bin/python scripts/ism_micmac.py \
  --input /path/to/completed_ssim.csv \
  --format ssim \
  --json-output /path/to/ism.json \
  --csv-output-dir /path/to/ism_tables
```

The tool rejects missing, duplicate, or invalid judgments. It can also accept a complete labeled binary matrix. Its outputs are deterministic transformations of supplied relationships; without genuine, appropriately collected expert responses they are not empirical ISM findings.

## Carbon calculation scope

For a request, the backend deterministically computes:

```text
embodied kgCO2e = device-profile embodied factor × units
operational kgCO2e = (TDP W / 1000) × hours/day × 365
                     × energy-rating factor × grid factor
                     × units × lifespan years
total tCO2e = (embodied + operational) / 1000
```

The same inputs and lookup tables produce the same result. Device-profile factors, Maharashtra postal-prefix grid factors, the comparison baseline, and tree equivalence are tunable planning assumptions. They are not observations, uncertainty intervals, certified product LCAs, or forecasts learned from data.

The source families documented in code are the Central Electricity Authority CO₂ Baseline Database for the Indian Power Sector, Ember's India electricity data, manufacturer product environmental reports (including Apple reports), and the US EPA/USDA basis noted for tree equivalence. Verify the exact edition and bibliographic details before using them in an academic reference list.

## Environment variables

`backend/.env.example` contains every application/process key currently used by the backend setup:

| Key | Purpose |
|---|---|
| `EWASTE_CLERK_PUBLISHABLE_KEY` | Browser-safe Clerk development (`pk_test_`) key returned by runtime config |
| `CLERK_JWKS_URL` | Required HTTPS JWKS endpoint for protected API authentication |
| `CLERK_ISSUER`, `CLERK_AUDIENCE` | Optional exact JWT claim checks |
| `DELETE_API_KEY` | Optional additional `X-Delete-Key` requirement for non-browser clients; leave unset for the React UI |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `EWASTE_DATA_DIR`, `EWASTE_CONFIG_PATH` | Optional portable state/config root overrides |
| `EWASTE_DB_PATH`, `EWASTE_LOG_DIR`, `EWASTE_BACKUP_DIR` | Optional mutable file/directory overrides |
| `EWASTE_FRONTEND_DIR`, `EWASTE_LIFESPAN_MODEL_DIR`, `EWASTE_CLASSIFIER_MODEL_PATH` | Optional packaged resource overrides |
| `EWASTE_REQUIRE_FRONTEND` | Require SPA assets for readiness; enabled in frozen releases |
| `EWASTE_MODEL` | Pre-trained classifier preset |
| `CLASSIFY_THRESHOLD`, `ELECTRONIC_THRESHOLD`, `MARGIN_THRESHOLD` | Optional finite `[0,1]` overrides for model-family rejection heuristics; not calibrated probabilities |
| `SCAN_RATE_LIMIT` | Per-user scans per 60-second in-process window |
| `CACHE_MAX_MEMORY_MB` | Classifier result-cache accounting limit |
| `LOG_LEVEL` | Backend logging level |
| `EWASTE_SKIP_MODEL_PRELOAD` | Test/diagnostic switch; normal value is `0` |
| `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` | Native numerical thread limits |
| `HF_HUB_OFFLINE` | Optional upstream Hugging Face offline switch; leave unset until cached |

Classifier rejection thresholds default to code-level, model-family heuristics in `app/model.py`. The three optional overrides above are validated as finite values in `[0,1]`; they remain tuning controls, not calibrated probabilities, and any changes should be recorded with evaluation results.

Frontend build/runtime keys:

| Key | Purpose |
|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | Source-development fallback only; production uses same-origin runtime config |
| `VITE_API_URL` | Vite development proxy target; defaults to `http://127.0.0.1:8000` |

## Operational limitations

- Source development defaults to `backend/scan_history.db`; the Windows release stores durable per-user SQLite state under `%LOCALAPPDATA%\EWasteManagement\data`. Public-cloud durability is not implemented.
- DELETE operations are scoped to the authenticated Clerk user. If `DELETE_API_KEY` is configured, non-browser clients must send it; leave it unset for the React UI.
- Scanner condition (`good`, `damaged`, or `burnt`) is a global-image-statistics heuristic, not a validated physical-damage detector.
- The in-process cache and rate limiter are per worker, not distributed controls.
- Cohort projections require actual inventory inputs for practical use and require observed retirement/disposal data for calibration and validation.
- ISM/MICMAC outputs require real expert judgments and a documented sampling/consensus protocol before they can be research findings.
- Setup and tests do not by themselves establish production readiness, security certification, model accuracy, forecast accuracy, or research validity.

For the explicit research status and presentation-safe wording, see [docs/RESEARCH_ALIGNMENT.md](docs/RESEARCH_ALIGNMENT.md) and [docs/PPT_CORRECTED_CONTENT.md](docs/PPT_CORRECTED_CONTENT.md).
