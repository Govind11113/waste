import os

# Pin native thread libs to a single thread BEFORE importing anything that
# pulls in numpy/sklearn/xgboost. Loading the saved xgboost Pipeline via
# pickle while uvicorn is starting up segfaults on macOS when these are
# left at the default multi-threaded values (OpenMP / OpenBLAS / MKL
# initialize conflicting thread pools).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import classifier, carbon, history, prognosis
from app.db import init_db  # noqa: F401 — triggers table creation on import

app = FastAPI(
    title="E-Waste Management Backend",
    description="Precision sustainability metrics and hardware prognosis.",
    version="3.0.0"
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prognosis.router, prefix="/api/v1")
app.include_router(carbon.router, prefix="/api/v1")
app.include_router(classifier.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"status": "online", "engine": "E-Waste Management v3", "version": "3.0.0"}
