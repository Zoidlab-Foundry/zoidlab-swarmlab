# ZoidLab SwarmLab — Foundry Package 13

Multi-Agent Orchestration. Design **swarms** — sets of role-specialized agents connected by a
**typed handoff graph** (which agent may hand off to which) — and run them for real through the
Nyquest relay. Each agent turn is a genuine relay completion; an agent may end its turn with a
control directive (`[[HANDOFF:<key>]]` or `[[DONE]]`). The orchestrator **enforces the handoff
contract** (an undeclared edge is rejected, not followed), **bounds runtime** by a max-steps
ceiling (hard cap 16), and records a full **replayable** step trace.

Every data endpoint requires Nyquest Pro (fail-closed on the Next middleware AND the FastAPI
backend). Runs emit SpendGuard usage events and preflight through TrustGate.

## Layout
- `backend/` — FastAPI + Postgres with per-tenant FORCE row-level security (every query runs as
  the non-superuser `app_rls` role keyed on `app.current_owner`, so tenant isolation is enforced
  by the database, not by application code). `swarm_engine.py` real relay orchestration with
  enforced typed handoffs + bounded steps; `db_pg.py` owner-scoped swarms/runs; `celery_app.py` +
  `tasks.py` Celery + Redis durable run jobs that survive an API restart; `main.py` the `/api`.
- `frontend/` — Next 15 + React 19 (amber theme). Dashboard, Swarms (agent + handoff builder),
  Run (trace + final output), Runs (replayable traces).

## Run locally
Backend: `cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/uvicorn main:app --port 8707`
Frontend: `cd frontend && npm install && SWARMLAB_API_URL=http://127.0.0.1:8707 npm run dev` (port 3707)

Live: https://swarm.zoidlab.ai
