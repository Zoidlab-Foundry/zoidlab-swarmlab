"""ZoidLab SwarmLab API — Foundry Package 13, Multi-Agent Orchestration.

Design swarms (role-specialized agents + a typed handoff graph) and run them for real through
the Nyquest relay: agents take turns, hand off along declared edges (the handoff contract is
enforced), the run is bounded by a max-steps ceiling, and a full step trace is stored for
replay. Every data endpoint requires Nyquest Pro (backend fail-closed). Runs emit SpendGuard
usage and preflight through TrustGate. NOTE: uses /api (platform-consistent).
"""
import uuid as _uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

import database as db
import llm
import swarm_engine
import exporter
import foundry
import seed_swarm
from auth import session, require_pro, relay_key, entitlement


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    n = seed_swarm.run()
    if n:
        print(f"[swarmlab] seeded {n} demo swarms")
    yield


app = FastAPI(title="ZoidLab SwarmLab API", lifespan=lifespan)


def require_owner(request: Request):
    o = require_pro(request)
    s = session(request)
    db.upsert_user(o, s.get("email") if s else None, s.get("name") if s else None)
    return o


@app.get("/api/health")
def health():
    return {"ok": True, "service": "swarmlab"}


@app.get("/api/auth/me")
def auth_me(request: Request):
    s = session(request)
    if not s:
        return {"authenticated": False}
    return {"authenticated": True, "user_id": s.get("sub"), "email": s.get("email"),
            "name": s.get("name"), "tier": s.get("tier")}


@app.get("/api/auth/entitlements")
def auth_entitlements(request: Request):
    return entitlement(request)


@app.get("/api/meta")
async def meta():
    try:
        models = await llm.featured_models()
    except Exception:
        models = ["auto"]
    return {"relay_available": llm.available(), "billing_mode": llm.billing_mode(),
            "models": models, "default_model": swarm_engine.DEFAULT_MODEL,
            "max_steps_cap": swarm_engine.MAX_STEPS_CAP}


@app.get("/api/stats")
def stats(request: Request, owner: str = Depends(require_owner)):
    return db.stats(owner)


# --- swarms ---
class Agent(BaseModel):
    key: str
    name: Optional[str] = ""
    role: Optional[str] = ""
    system: Optional[str] = ""
    model: Optional[str] = "auto"


class SwarmBody(BaseModel):
    name: str
    description: Optional[str] = ""
    goal: Optional[str] = ""
    agents: List[dict] = []
    handoffs: List[dict] = []
    entry_agent: Optional[str] = ""
    max_steps: Optional[int] = 8
    model: Optional[str] = "auto"


@app.get("/api/swarms")
def swarms(request: Request, owner: str = Depends(require_owner)):
    return {"swarms": db.list_swarms(owner)}


@app.get("/api/swarms/{sid}")
def get_swarm(sid: str, request: Request, owner: str = Depends(require_owner)):
    s = db.get_swarm(sid, owner)
    if not s:
        raise HTTPException(404, "not_found")
    return s


@app.post("/api/swarms")
def create_swarm(body: SwarmBody, owner: str = Depends(require_owner)):
    return {"ok": True, "swarm": db.create_swarm(body.model_dump(), owner)}


@app.put("/api/swarms/{sid}")
def update_swarm(sid: str, body: SwarmBody, owner: str = Depends(require_owner)):
    s = db.update_swarm(sid, owner, body.model_dump())
    if not s:
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True, "swarm": s}


@app.delete("/api/swarms/{sid}")
def delete_swarm(sid: str, owner: str = Depends(require_owner)):
    if not db.delete_swarm(sid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# --- run ---
class RunBody(BaseModel):
    swarm_id: str
    task_input: str
    model: Optional[str] = None
    max_steps: Optional[int] = None


@app.post("/api/run")
async def run_swarm(body: RunBody, request: Request, owner: str = Depends(require_owner)):
    swarm = db.get_swarm(body.swarm_id, owner)
    if not swarm:
        raise HTTPException(404, "swarm_not_found")
    if not llm.available():
        raise HTTPException(503, "relay_unavailable: real orchestration needs a relay key")
    model = body.model or swarm.get("model") or swarm_engine.DEFAULT_MODEL
    corr = "corr_" + _uuid.uuid4().hex[:12]
    foundry.set_session(request.cookies.get("zb_session"))
    pf = await foundry.trustgate_preflight(
        {"prompt": (swarm.get("goal") or "") + " :: " + (body.task_input or ""), "model": model,
         "data_classification": "internal", "context_type": "multi_agent"}, correlation_id=corr)
    if pf.get("decision") == "blocked":
        rid = db.create_run(swarm, body.task_input, model, owner, corr)
        db.finish_run(rid, {"status": "blocked", "outcome": "blocked",
                            "error": "TrustGate blocked: " + "; ".join(pf.get("reasons") or [])})
        return db.get_run(rid, owner)
    rid = db.create_run(swarm, body.task_input, model, owner, corr)
    llm.set_relay_auth(relay_key(request))
    res = await swarm_engine.run(swarm, body.task_input, model, body.max_steps or swarm.get("max_steps"),
                                 relay_key=relay_key(request))
    db.finish_run(rid, res)
    try:
        await foundry.emit_spend(res.get("usage"), resource_id=rid, feature=swarm.get("name"),
                                 correlation_id=corr, environment="development")
    except Exception:
        pass
    return db.get_run(rid, owner)


@app.get("/api/runs")
def runs(request: Request, owner: str = Depends(require_owner)):
    return {"runs": db.list_runs(owner)}


@app.get("/api/runs/{rid}")
def get_run(rid: str, request: Request, owner: str = Depends(require_owner)):
    r = db.get_run(rid, owner)
    if not r:
        raise HTTPException(404, "not_found")
    return r


# --- export ---
@app.get("/api/swarms/{sid}/export")
def export_swarm(sid: str, request: Request, owner: str = Depends(require_owner)):
    s = db.get_swarm(sid, owner)
    if not s:
        raise HTTPException(404, "not_found")
    return exporter.to_package(s, owner=owner)
