# LQIS — Automated Tea Leaf Quality Detection & Monitoring System

Phase 5 production-style polish with advanced analytics, hardened offline sync, and real reporting exports.

## Core capabilities
- Role-based access (`Admin`, `Inspector`, `Supervisor`)
- Factory Intake Sampling with image evidence + AI-assisted baseline pluck prediction
- Quality score/status + alerts + supervisor decision workflow
- Advanced dashboard analytics (center/supplier/factory/decision/quality distribution)
- Offline-first queue (IndexedDB) + reconnect sync + manual sync controls
- Installable PWA (manifest, icons, service worker, offline fallback)
- Reporting with filters + CSV/Excel/PDF exports

## Project structure summary
- `core/` — master data, app shell APIs (manifest, SW route, snapshot)
- `sampling/` — intake submission, sync endpoint, quality/alerts/decisions
- `dashboard/` — analytics views and trend aggregations
- `reporting/` — filtered report pages and export generators
- `static/js/offline_queue.js` — local queue + sync engine
- `templates/core/service_worker.js` — service worker source

## Local setup (Linux/macOS)
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python lqis_project/manage.py makemigrations
python lqis_project/manage.py migrate
python lqis_project/manage.py seed_demo_data
python lqis_project/manage.py runserver
```

## Local setup (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python lqis_project\manage.py makemigrations
python lqis_project\manage.py migrate
python lqis_project\manage.py seed_demo_data
python lqis_project\manage.py runserver
```

## Demo credentials
- `admin / admin123`
- `inspector1 / admin123`
- `supervisor1 / admin123`

## Offline queue behavior
1. Open sampling page while online at least once (master data snapshot is cached).
2. If offline during submit, sample is saved to IndexedDB queue (not lost on refresh).
3. Sync happens on reconnect, on page focus, or via **Sync Now**.
4. Queue panel shows pending/failed status, retry counts, and last sync time.
5. Server-side duplicate prevention uses `client_submission_id`.

## PWA installability test
1. Open app in Chromium browser over local server.
2. Verify manifest and service worker in DevTools Application tab.
3. Use **Install App** button/prompt.
4. Launch installed app and verify offline fallback route (`/offline/`).

## Reporting & exports
- Open `Reporting` page.
- Apply filters: date range, factory, center, supplier, decision, alert type.
- Use export actions:
  - **CSV** (`export=csv`)
  - **Excel** (`export=xlsx`)
  - **PDF** (`export=pdf`)
- Summaries shown: daily totals, weekly quality, rejection summary, alert summary, buying center performance.
