# PyInstaller one-folder build for Windows 10/11 x64.
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
LIFESPAN_MODELS = BACKEND_ROOT / "models" / "lifespan"
CLASSIFIER_MODEL = BACKEND_ROOT / "models" / "classifier" / "siglip2-base"

required = (
    FRONTEND_DIST / "index.html",
    LIFESPAN_MODELS / "model_manifest.json",
    CLASSIFIER_MODEL / "model_manifest.json",
)
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Missing release inputs:\n  " + "\n  ".join(missing))

datas = [
    (str(FRONTEND_DIST), "frontend"),
    (str(LIFESPAN_MODELS), "models/lifespan"),
    (str(CLASSIFIER_MODEL), "models/classifier/siglip2-base"),
]
datas += collect_data_files("transformers", excludes=["**/tests/**"])
for distribution in (
    "transformers",
    "huggingface-hub",
    "safetensors",
    "torch",
    "torchvision",
    "scikit-learn",
    "xgboost",
    "lightgbm",
):
    datas += copy_metadata(distribution)

hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("sklearn")
hiddenimports += collect_submodules("transformers.pipelines")
hiddenimports += collect_submodules("transformers.models.siglip2")
hiddenimports += [
    "app.main",
    "app.routers.carbon",
    "app.routers.classifier",
    "app.routers.generation",
    "app.routers.history",
    "app.routers.prognosis",
    "lightgbm",
    "numpy._core.multiarray",
    "pandas",
    "sklearn.compose._column_transformer",
    "sklearn.ensemble._forest",
    "sklearn.pipeline",
    "sklearn.preprocessing._encoders",
    "xgboost",
]

analysis = Analysis(
    [str(BACKEND_ROOT / "run_server.py")],
    pathex=[str(BACKEND_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython",
        "jupyter",
        "matplotlib.tests",
        "pytest",
        "tkinter",
        "torch.testing",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="EWasteManagement",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory=".",
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EWasteManagement",
)
