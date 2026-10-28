# Anveshi (अन्वेषी)

An independent, open-source, self-hostable, identifier-first application intelligence engine.

**Status:** Day 1 skeleton. The current endpoint returns only directly matching synthetic events. Correlation, timeline reconstruction, failure detection, and root-cause analysis are **not implemented**.

## Prerequisites
- Python 3.11+ (recommended: 3.12)
- Node.js 20.19+ or 22.12+

## Backend (PowerShell)
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/api/v1/health

On Linux/macOS, activate with `source .venv/bin/activate` and replace `py` with `python3`.

## Frontend (second terminal)
```powershell
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173

Enter `txn-123` and investigate. The API returns two direct matches; the bank-connector event has only `request_id` and will appear only after correlation is implemented.

## API example
```json
{"identifier_type":"transaction_id","identifier_value":"txn-123"}
```
POST to `/api/v1/investigations`. The request currently supports exact key/value matching against `samples/incident_001.json`.

## Project structure
- `backend/app/models`: normalized event and investigation contracts
- `backend/app/sources`: source adapter interface and synthetic adapter
- `backend/app/engine`: reserved for deterministic investigation logic
- `backend/app/api`: REST routes
- `backend/tests`: backend tests
- `frontend`: React/TypeScript/Vite application
- `samples`: synthetic, non-proprietary incident fixtures

## Principles
Evidence first. Never invent missing identifiers, events, causal relationships, or root causes. Keep the deterministic core independent of AI and source providers.

## Next milestone
Implement bounded identifier correlation with explicit inclusion evidence and deterministic tests.
