# Running E-Waste Management on Windows (source setup)

You received the project as a ZIP from macOS and want to run the website on a Windows 10/11 x64 PC. Follow every step in order. Every command is copy-pasteable into **PowerShell**.

Estimated time: 15–25 minutes on a normal internet connection. Most of that is the one-time `pip install` for PyTorch (~250 MB) and `npm ci` (~350 MB).

---

## TL;DR — the fast path

If you already have **Python 3.11 x64** and **Node.js 20+** installed, extract the ZIP, open PowerShell inside the extracted folder, and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\setup-windows.ps1
```

That single command cleans the ZIP, creates the Python virtualenv, installs every backend and frontend dependency, and builds the frontend.

When it finishes, edit `backend\.env` and `frontend\.env` with your Clerk keys (step 2 below explains where to get them), then start the app with:

```powershell
.\run-windows.ps1
```

Open **http://127.0.0.1:8000** — done.

The rest of this document is the same steps done by hand, plus troubleshooting.

---

## 0. What you need before starting

| Requirement | Version | Download |
|---|---|---|
| Windows | 10 or 11, 64-bit | — |
| Python | **3.11.x** (not 3.12, not 3.13) | https://www.python.org/downloads/release/python-3119/ — pick "Windows installer (64-bit)" |
| Node.js | 20 LTS or newer | https://nodejs.org/en/download |
| Clerk account | free | https://clerk.com |

During Python install, **tick "Add python.exe to PATH"**. During Node install, accept defaults.

Open a fresh PowerShell window and verify:

```powershell
py -3.11 --version
node --version
npm --version
```

You must see `Python 3.11.x`, a Node version `v20` or higher, and a working npm. If any command errors, reinstall that runtime before continuing.

---

## 1. Extract the ZIP and delete Mac leftovers

Extract the ZIP anywhere you like (avoid OneDrive-synced folders and paths with special characters — `C:\dev\E-waste` is a good choice).

The ZIP was created on macOS, so it contains a Python virtualenv and Node modules built for macOS. **These will not run on Windows and must be deleted first.**

```powershell
cd C:\dev\E-waste           # change to wherever you extracted it

Remove-Item -Recurse -Force .\backend\venv -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\backend\.venv -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\frontend\node_modules -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\frontend\dist -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Force -Include __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
```

Do **not** delete `backend\models\` — those pre-trained model files are cross-platform and are required for the classifier and lifespan features to work.

---

## 2. Get your Clerk keys

The app uses Clerk for user login. You need a free development instance.

1. Sign up at https://clerk.com and create a new application.
2. On the left sidebar go to **API Keys**. Copy the **Publishable key** — it starts with `pk_test_`.
3. On the left sidebar go to **Configure → Sessions → Show JWT public key** and copy the **JWKS URL**. It looks like:
   `https://your-something.clerk.accounts.dev/.well-known/jwks.json`
4. Under **Paths / Redirect / Domains**, add the following as allowed origins so login works from your PC:
   - `http://localhost:5173` and `http://127.0.0.1:5173` (dev mode, two windows)
   - `http://localhost:8000` and `http://127.0.0.1:8000` (single-server mode, one window)

Keep both values (`pk_test_...` and the JWKS URL) open in Notepad. You will paste them into two files below.

---

## 3. Backend setup (Python + FastAPI)

Open a PowerShell window at the project root (`C:\dev\E-waste`), then:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements-windows.txt
```

The last line takes 5–10 minutes the first time (downloading PyTorch, transformers, scikit-learn, etc.). Wait for it to finish with no red errors.

Then create the backend config file:

```powershell
Copy-Item .env.example .env
notepad .env
```

In Notepad, replace these two lines with your real Clerk values, then save and close:

```
EWASTE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
CLERK_JWKS_URL=https://YOUR-INSTANCE.clerk.accounts.dev/.well-known/jwks.json
```

Leave every other line as-is.

---

## 4. Frontend setup (React + Vite)

Open a **new** PowerShell window at the project root:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
notepad .env
```

In Notepad, set the publishable key (same `pk_test_...` value as the backend), then save and close:

```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
```

---

## 5. Run the website

You have two ways to run the app. Pick **one**:

- **Option A (recommended for normal use)** — single server, one PowerShell window. Backend serves both the API and the built React app on the same port. Best if you just want to use the website.
- **Option B (for development)** — two PowerShell windows, hot reload on frontend edits. Best if you plan to change React code.

---

### Option A — Single server (one window)

Build the frontend once, then run the backend which auto-serves it.

```powershell
# One-time: build the React app
cd C:\dev\E-waste\frontend
npm run build
```

That creates `frontend\dist\`. You only rebuild if you change frontend source code.

Now start the server:

```powershell
cd C:\dev\E-waste\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

Wait for `Uvicorn running on http://127.0.0.1:8000`, then open in your browser:

```
http://127.0.0.1:8000
```

The React app, all pages, and the API all live at that one URL. To stop the server, press **Ctrl+C** in the PowerShell window.

> **Important:** in the Clerk dashboard, `http://localhost:8000` and `http://127.0.0.1:8000` must be in the allowed origins for this mode to log you in. (You already added them in step 2.)

The first image scan will download the SigLIP2 vision model from Hugging Face (~400 MB, one time) — that is expected.

---

### Option B — Dev mode (two windows, hot reload)

Use this only if you are actively editing React code and want changes to appear instantly.

**Window 1 — backend:**
```powershell
cd C:\dev\E-waste\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

**Window 2 — frontend dev server:**
```powershell
cd C:\dev\E-waste\frontend
npm run dev
```

Open http://localhost:5173. Vite proxies API calls to the backend on port 8000 automatically. Stop each server with **Ctrl+C** in its own window.

---

## 6. Everyday use (after the first setup)

You only do steps 1–4 once. From then on, running the site is just:

**Option A (single window):**
```powershell
cd C:\dev\E-waste\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
```
Open http://127.0.0.1:8000. If you changed React code, rerun `npm run build` in the frontend folder first.

**Option B (two windows):** run the two commands from step 5 Option B, open http://localhost:5173.

---

## Troubleshooting

**`py -3.11` says "No suitable Python runtime found"**
Python 3.11 is not installed, or you installed a different version. Reinstall from the link in step 0 and tick "Add python.exe to PATH".

**`.\.venv\Scripts\python` says "cannot be loaded because running scripts is disabled"**
PowerShell script execution is blocked. Run this once:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Answer `Y` when prompted.

**`pip install` fails with a torch or wheel error**
The `requirements-windows.txt` file pins PyTorch CPU wheels from `https://download.pytorch.org/whl/cpu`. Make sure your PC has internet and no proxy blocking that host. Delete `.venv` and retry step 3.

**Backend starts, but browser shows "Configuration errors" screen**
Your Clerk keys in `backend\.env` or `frontend\.env` are wrong, placeholder, or the JWKS URL is not `https://`. Reopen both `.env` files, fix the values, then restart both windows.

**Login redirects fail or Clerk shows "Origin not allowed"**
Go back to the Clerk dashboard and add `http://localhost:5173` and `http://127.0.0.1:5173` to the allowed origins for your development instance.

**Port 8000 or 5173 is already in use**
Another program is using it. Either close that program or change the port:
- Backend: change `--port 8000` to `--port 8010`
- Frontend: run `npm run dev -- --port 5174` and update Clerk allowed origins accordingly.

**Scanner returns 503 or "model not ready"**
The first startup downloads the classifier model. Watch the backend PowerShell window — it should show download progress, then `Model loaded`. Wait for that before scanning. If your PC is offline, the download cannot complete.

**Everything worked before but broke after moving folders**
The venv stores absolute paths to your Python install. If you moved the project folder or reinstalled Python, delete `backend\.venv` and repeat step 3.

---

## What each folder is (quick reference)

| Path | What it is | Safe to delete? |
|---|---|---|
| `backend\` | FastAPI server, ML models, database | Keep |
| `backend\models\` | Pre-trained SigLIP2 + lifespan models (~1.5 GB) | **Never delete** — required |
| `backend\.venv\` | Windows Python virtualenv (created by you) | Yes — rerun step 3 to rebuild |
| `backend\scan_history.db` | Your local user scan history | Deleting wipes your history |
| `frontend\` | React app | Keep |
| `frontend\node_modules\` | Installed npm packages | Yes — rerun `npm ci` to rebuild |
| `frontend\dist\` | Production build output | Yes — regenerates with `npm run build` |
| `packaging\windows\` | Files for building the standalone `.exe` release | Only needed if building a distributable ZIP |
