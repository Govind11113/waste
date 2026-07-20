# Windows 10/11 x64 installation and operation

This guide applies to the **one-folder Windows release ZIP**, not to a source checkout. The receiving PC does **not** need Python, Node.js, npm, Git, or Hugging Face access. It does need Windows 10/11 x64, a current browser, and internet access for Clerk development authentication and optional weather/map services.

> Build-status boundary: PyInstaller builds are operating-system specific. The source tree contains the Windows spec and build automation, but a Windows executable cannot be produced or truthfully tested on macOS. A release ZIP is acceptable only after `packaging/windows/build-release.ps1` finishes on Windows x64 and the Windows checklist in `WINDOWS_ACCEPTANCE.md` is signed off.

## 1. Verify and extract

1. Obtain both `EWasteManagement-Windows-x64-v3.0.0.zip` and its adjacent `.zip.sha256` file from a trusted transfer.
2. In PowerShell, compare the archive hash:

   ```powershell
   Get-FileHash .\EWasteManagement-Windows-x64-v3.0.0.zip -Algorithm SHA256
   Get-Content .\EWasteManagement-Windows-x64-v3.0.0.zip.sha256
   ```

3. Use **Extract All**. Do not run the application from inside the ZIP. A per-user folder such as `%USERPROFILE%\Applications\EWasteManagement-Windows-x64-v3.0.0` is suitable. Avoid a read-only folder or a network share.
4. Confirm that the extracted folder contains `EWasteManagement.exe`, the four `.cmd` helpers, `frontend`, and `models`.

The executable is not code-signed by these build scripts. If Windows SmartScreen appears, first verify the SHA-256 value and the source of the ZIP. Do not bypass a warning for an unverified archive.

## 2. Prepare Clerk development authentication

The localhost release deliberately accepts only a Clerk **development** publishable key beginning `pk_test_`. Do not use `pk_live_`, a Clerk secret key, or a placeholder.

In the Clerk dashboard for the development instance, obtain:

- the browser publishable key (`pk_test_...`); and
- that same development instance's HTTPS JWKS endpoint, normally ending `/.well-known/jwks.json`.

Clerk dashboard labels can change; use the current values shown for the development instance. The publishable key and JWKS URL are public configuration, but Clerk secret keys must never be entered, copied into `.env`, or bundled.

Double-click **`Configure E-Waste.cmd`** and enter those two values. Issuer and audience are optional exact-claim restrictions; leave them blank unless the Clerk token configuration is known. The wizard:

- rejects live/placeholder/non-HTTPS values;
- preserves unrelated existing configuration and makes a timestamped pre-change copy;
- writes `%LOCALAPPDATA%\EWasteManagement\config\.env`; and
- runs packaged diagnostics without displaying configured values.

Leave `DELETE_API_KEY` unset for the React UI. That option is only for non-browser API clients able to send `X-Delete-Key`; putting a server secret in browser JavaScript would be unsafe.

## 3. Start and stop

Double-click **`Start E-Waste.cmd`**. The server binds only to `127.0.0.1` (not the LAN). It verifies state directories, initializes SQLite, loads the bundled classifier offline, and opens `http://127.0.0.1:8000` only after `/health/ready` succeeds. First startup can take longer while the model loads.

Keep the console window open. Stop the server with **Ctrl+C** in that window or by closing it. A second launch is rejected by the per-user instance lock. If port 8000 belongs to another program, diagnostics reports a port conflict rather than binding to another interface.

Useful local endpoints:

- App: `http://127.0.0.1:8000`
- Liveness: `http://127.0.0.1:8000/health/live`
- Readiness: `http://127.0.0.1:8000/health/ready`
- API documentation: `http://127.0.0.1:8000/docs`

Protected API operations still require a valid Clerk session.

## 4. Data locations

The extracted program folder is treated as immutable. Per-user mutable data stays under `%LOCALAPPDATA%\EWasteManagement`:

| Path | Purpose |
|---|---|
| `config\.env` | Clerk public configuration and optional backend settings |
| `data\scan_history.db` | SQLite scan, lifespan, and carbon history |
| `logs\ewaste.log` | Rotating application log |
| `backups\` | Backup ZIPs |
| `server.lock` | Running-instance lock; removed on clean shutdown |

Do not move `.env`, the database, logs, or backups into the extracted application folder. Never send a backup or log publicly without reviewing it.

## 5. Diagnostics

Run **`Diagnose E-Waste.cmd`**. It verifies Windows architecture, configuration presence/shape, writable state, SQLite, SPA files, classifier and lifespan SHA-256 manifests, and port status. It does not print publishable-key values, JWKS values, `DELETE_API_KEY`, JWTs, or image data.

Common results:

- **Configuration fails:** rerun the configuration wizard with a real `pk_test_` key and matching HTTPS JWKS URL.
- **Classifier/lifespan fails:** re-extract a verified release ZIP. The frozen app never downloads missing model files.
- **Port occupied:** stop the other local program or launch `scripts\Start-EWaste.ps1 -Port <unused-port>` from PowerShell. Clerk must permit that localhost origin if its policy requires explicit ports.
- **Authentication UI/API fails:** confirm internet access, system clock, Clerk development-instance status, and that the key/JWKS belong to the same instance.
- **Weather or tiles fail:** the map keeps city locations and shows a warning. Check access to Open-Meteo and the selected public tile provider.
- **Browser does not open:** readiness failed; run diagnostics and inspect `%LOCALAPPDATA%\EWasteManagement\logs\ewaste.log`.

## 6. Back up and restore

Run **`Backup E-Waste.cmd`**. The executable uses SQLite's online backup API, so the database copy is consistent even if WAL mode is active. A timestamped ZIP is written to `%LOCALAPPDATA%\EWasteManagement\backups` and contains, when present:

- `data/scan_history.db`;
- `config/.env`; and
- `backup_manifest.json`.

Backups contain user history and may contain configuration secrets. Store and transmit them accordingly.

Restore is intentionally manual because it replaces user state:

1. Stop E-Waste Management completely.
2. Run a fresh backup and copy it somewhere safe.
3. Inspect the selected backup's `backup_manifest.json`.
4. Rename the current `%LOCALAPPDATA%\EWasteManagement\data\scan_history.db` rather than deleting it.
5. Extract the backed-up `data\scan_history.db` into that `data` folder. Restore `config\.env` only if the older Clerk/settings configuration is also intended.
6. Do not restore `-wal` or `-shm` sidecars; the backup ZIP intentionally does not contain them.
7. Run diagnostics, then start the application and verify history.

## 7. Update, rollback, and uninstall

To update safely:

1. Create and preserve a backup.
2. Verify and extract the new release into a **new** folder; do not overwrite files while the app is running.
3. Stop the old version, run the new version's diagnostics, then start the new version.
4. Do not copy mutable data into the new folder. Both versions use the same `%LOCALAPPDATA%` state.
5. Keep the prior extracted folder and pre-update backup until all workflows pass. A database migration may not be backward-compatible, so restore the backup before rolling back if necessary.

Deleting only the extracted release uninstalls the executable but intentionally preserves data. Permanent data removal is destructive: after making any required backup and stopping the app, delete `%LOCALAPPDATA%\EWasteManagement` manually.

## 8. Network and privacy boundary

The classifier and lifespan artifacts are local and manifest-verified; the receiving PC makes no Hugging Face model download. Ordinary browser/service traffic still occurs:

- Clerk development authentication and JWKS retrieval;
- Open-Meteo weather requests; and
- OpenStreetMap/OpenTopoMap/CARTO tile requests selected by the user.

Uploaded classifier image bytes are processed locally in memory. History stores submitted filenames and calculated results in local SQLite; it does not intentionally store the uploaded image bytes. Review the in-app Privacy, Terms, and Methodology pages before operational use.
