from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import classifier, carbon, history, prognosis
from app.db import init_db

app = FastAPI(
    title="E-Waste Management Backend",
    description="Precision sustainability metrics and hardware prognosis.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prognosis.router, prefix="/api/v1")
app.include_router(carbon.router, prefix="/api/v1")
app.include_router(classifier.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")


@app.on_event("startup")
async def preload():
    init_db()


@app.get("/")
async def root():
    return {"status": "online", "engine": "E-Waste Management v3", "version": "3.0.0"}
