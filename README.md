# Anveshi (अन्वेषी)

An independent, open-source, self-hostable, identifier-first application intelligence engine.

**Status:** Investigation Intelligence v0.1. The investigation endpoint performs deterministic, bounded identifier correlation, time-window filtering, chronological timeline reconstruction, and evidence-based failure detection over synthetic events. Root-cause analysis is not implemented.

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

Enter `txn-123` and investigate. The UI shows the three connected events across the API gateway, payment service, and bank connector. The unrelated `req-999` event is excluded.

## API example
```json
{"identifier_type":"transaction_id","identifier_value":"txn-123"}
```
POST to `/api/v1/investigations`. The request currently supports exact key/value matching against `samples/incident_001.json`.
The response includes the original event fields plus correlation evidence (`correlation_type`, `depth`, parent event, and matched identifier), aggregate statistics, findings, a chronological timeline, investigation status, and an effective time window. The optional `reference_timestamp` request field overrides the default anchor; otherwise, the earliest direct match anchors the inclusive 15-minute window. Correlation expands only through `transaction_id`, `request_id`, and `trace_id`; `user_id`, `tenant_id`, and `session_id` are not safe bridges. The default correlation limits are a depth of 2 and 500 events. Failure indicators include ERROR/FATAL severity, HTTP 5xx, structured failure statuses, and timeout indicators. Findings report observed evidence and do not claim root cause.

## Project structure
- `backend/app/models`: normalized event and investigation contracts
- `backend/app/sources`: source adapter interface and synthetic adapter
- `backend/app/engine`: deterministic correlation and investigation intelligence
- `backend/app/api`: REST routes
- `backend/tests`: backend tests
- `frontend`: React/TypeScript/Vite application
- `samples`: synthetic, non-proprietary incident fixtures

## Principles
Evidence first. Never invent missing identifiers, events, causal relationships, or root causes. Keep the deterministic core independent of AI and source providers.

## Next milestone
Connect production telemetry sources while preserving the explicit evidence and unknown-root-cause contract.
