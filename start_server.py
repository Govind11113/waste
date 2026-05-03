#!/usr/bin/env python3
"""
E-Waste Management System - Server Entry Point
Starts the FastAPI backend server
"""

import sys
import os

# Set local cache for transformers to avoid /tmp permission issues
cache_dir = os.path.join(os.path.dirname(__file__), "backend", "cache")
os.makedirs(cache_dir, exist_ok=True)
os.environ["TRANSFORMERS_CACHE"] = cache_dir
os.environ["HF_HOME"] = cache_dir

# Suppress OpenMP warnings and potential conflicts
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

if __name__ == "__main__":
    import uvicorn
    # Ignore cache directory in reload
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["backend/app", "backend/utils"])
