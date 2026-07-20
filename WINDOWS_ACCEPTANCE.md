# Windows release acceptance checklist

## Current verification boundary

The Windows packaging design, scripts, model snapshot, tests, and documentation were prepared on macOS. **No Windows `.exe` or final ZIP is claimed as built or tested in this repository session.** PyInstaller cannot cross-build a Windows executable from macOS. A release becomes acceptable only after the Windows x64 build and checks below complete with recorded evidence.

The build command on a Windows 10/11 x64 build PC is:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\packaging\windows\build-release.ps1
```

The build PC requires Python 3.11 x64, Node.js/npm, internet access for dependencies and the pinned model if not already prepared, and enough free disk/RAM. The receiving PC requires none of those development runtimes.

## Automated gates

Record the command output or attach it to the release record.

- [ ] Frontend `npm ci`, strict typecheck, Vitest suite, and production build pass.
- [ ] Backend full pytest suite and `scripts/test_classifier.py` quality gates pass.
- [ ] Pinned classifier snapshot revision is `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2`.
- [ ] Classifier and lifespan manifests verify before freezing.
- [ ] PyInstaller one-folder build completes on Windows x64.
- [ ] Frozen smoke test reaches ready state with `HF_HUB_OFFLINE=1` and no browser.
- [ ] Frozen liveness, runtime config, `/privacy` deep link, and SPA index checks pass.
- [ ] Release staging contains no `.env`, SQLite database, or log file.
- [ ] ZIP integrity test and archive SHA-256 generation pass.
- [ ] A second clean Windows user/VM with no Python or Node can run the extracted ZIP.

## Installation and runtime

- [ ] ZIP hash matches the `.zip.sha256` sidecar before extraction.
- [ ] App runs from a path containing spaces and from a standard per-user folder.
- [ ] `Configure E-Waste.cmd` rejects `pk_live_`, placeholders, malformed URLs, and newline input.
- [ ] Configuration is stored only under `%LOCALAPPDATA%\EWasteManagement\config`.
- [ ] `Diagnose E-Waste.cmd` reports all components ready and reveals no key/token/secret values.
- [ ] `Start E-Waste.cmd` binds only `127.0.0.1`; no listener appears on `0.0.0.0`, LAN IP, or IPv6 wildcard.
- [ ] Browser opens only after readiness and serves SPA/API from the same origin.
- [ ] A second start is refused without corrupting the first process.
- [ ] A deliberate port collision produces an actionable diagnostic.
- [ ] Restart preserves SQLite history and configuration.
- [ ] Logs rotate under `%LOCALAPPDATA%\EWasteManagement\logs`.

## Authentication and navigation

Use a Clerk development instance and test accounts—not production credentials.

- [ ] Sign-up, verification (if enabled), sign-in, session refresh, sign-out, and sign-in-again work on localhost.
- [ ] Signed-out users cannot load protected routes or protected API data.
- [ ] Two test users cannot view or delete one another's history.
- [ ] Home, Dashboard, Scanner, Lifespan, Carbon Calculator, Generation Forecast, History, Privacy, Terms, and Methodology deep links survive refresh.
- [ ] Footer policy links stay local and contain no placeholder domain.
- [ ] Configuration failure renders the setup screen rather than a blank page.
- [ ] A simulated render error reaches the global recovery screen.

## Website workflows

### Classifier

- [ ] JPEG, PNG, and WebP inputs within limits can be scanned.
- [ ] Unsupported formats, oversized files, tiny images, corrupt files, poor-quality images, and non-electronics receive understandable results/errors.
- [ ] A recognized electronic device returns canonical category, confidence/heuristic context, condition, and recovery guidance.
- [ ] An unavailable/corrupt classifier returns HTTP 503—not a misleading successful “Unrecognized” result.
- [ ] With network blocked after Clerk session establishment, inference still uses the local model and makes no Hugging Face request.

### Lifespan

- [ ] Seven-factor formula inputs validate and produce transparent score, remaining life, and scenario range.
- [ ] Available RF/XGBoost/LightGBM selections either produce results from verified artifacts or degrade clearly.
- [ ] Results and method labels do not present synthetic holdout metrics as field validity or sensitivity as confidence.

### Carbon and generation planning

- [ ] Carbon form validates values and produces embodied, operational, total, comparison, and tree-equivalence outputs.
- [ ] Cohort forecast handles one and multiple cohorts, sensitivity, tables/charts, and invalid inputs.
- [ ] Wording preserves the planning-assumption/evidence boundaries documented in Methodology.

### History and reports

- [ ] Scan, lifespan, and carbon records appear only for the signed-in user.
- [ ] Search, status filter, tab switching, pagination, empty states, error/retry states, and statistics work.
- [ ] PDF/report export completes and labels assumptions correctly.
- [ ] Per-category delete works when `DELETE_API_KEY` is unset; cancellation leaves records intact.

### Map, resilience, responsive UI

- [ ] Live Open-Meteo readings and each map tile style load when services are available.
- [ ] Complete weather failure leaves the Maharashtra map/city locations visible with a warning.
- [ ] Boundary/tile failure is understandable and does not crash the page.
- [ ] Light/dark theme, reduced-motion behavior, keyboard focus, mobile/tablet/desktop layouts, and major browser zoom levels are usable.

## Backup, update, and failure recovery

- [ ] Backup ZIP opens, has a manifest, and contains a consistent SQLite database plus intended config.
- [ ] Backup is treated as sensitive and is never placed in the program/release ZIP.
- [ ] Documented restore succeeds on a disposable test profile after preserving current state.
- [ ] Side-by-side update keeps state under `%LOCALAPPDATA%` and can be rolled back using the backup.
- [ ] Tampering with one classifier file and one lifespan artifact makes diagnostics/readiness fail by hash.
- [ ] Missing frontend assets make a frozen release not ready; API/asset misses remain 404 rather than SPA 200.
- [ ] Weather/map outage does not affect local API/model workflows.

## Browser automation and accessibility

The committed Playwright suite deliberately has no authentication bypass. On a validation PC with Node available:

```powershell
cd frontend
npx playwright install chromium
# Create a development-Clerk storage state interactively, for example:
npx playwright codegen --save-storage=playwright-auth.json http://127.0.0.1:8000/login
$env:EWASTE_E2E_BASE_URL='http://127.0.0.1:8000'
$env:EWASTE_E2E_AUTH_STATE=(Resolve-Path .\playwright-auth.json)
npm run test:e2e
Remove-Item .\playwright-auth.json
```

- [ ] Public policy/deep-link smoke and axe scan pass.
- [ ] Every protected page loads with the real development Clerk storage state.
- [ ] Manual keyboard/screen-reader review covers controls that automated axe cannot assess.
- [ ] `playwright-auth.json` is deleted after validation and never committed or put in a release.

## Sign-off

| Field | Value |
|---|---|
| Release version | |
| ZIP SHA-256 | |
| Windows edition/build | |
| Clean receiving-PC/VM identifier | |
| Clerk development instance (non-secret identifier only) | |
| Tester | |
| Test date | |
| Exceptions/known limitations | |
| Decision | Accept / Reject |
