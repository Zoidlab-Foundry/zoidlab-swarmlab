"""SQLite persistence for ZoidLab SwarmLab (Foundry Package 13 — Multi-Agent Orchestration).

Design swarms (role-specialized agents + a typed handoff graph) and run them for real through
the Nyquest relay. Each run records a full step-by-step trace so it can be replayed. Owner =
Nyquest user id; seed (owner NULL) is shared.
"""
import os
import json
import uuid
import sqlite3
import datetime

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "swarmlab.db")


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _j(v):
    return json.dumps(v)


def _pj(v, d=None):
    try:
        return json.loads(v) if v is not None else d
    except Exception:
        return d


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


def init():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT, name TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS swarms (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
                goal TEXT, agents TEXT, handoffs TEXT, entry_agent TEXT, max_steps INTEGER DEFAULT 8,
                model TEXT DEFAULT 'auto', version TEXT DEFAULT '1.0.0', created_at TEXT, updated_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_swarm_owner ON swarms(owner_user_id);
            CREATE TABLE IF NOT EXISTS swarm_runs (
                id TEXT PRIMARY KEY, owner_user_id TEXT, swarm_id TEXT, swarm_name TEXT, model TEXT,
                task_input TEXT, status TEXT DEFAULT 'queued', outcome TEXT, trace TEXT, final_output TEXT,
                steps_used INTEGER, prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER,
                cost_usd REAL, latency_ms INTEGER, error TEXT, correlation_id TEXT, created_at TEXT, finished_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_srun_owner ON swarm_runs(owner_user_id, created_at);
            """
        )


def _vis(col="owner_user_id"):
    return f"({col} IS NULL OR {col}=?)"


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO users (id,email,name,created_at,updated_at) VALUES (?,?,?,?,?)
                     ON CONFLICT(id) DO UPDATE SET email=COALESCE(excluded.email,users.email),
                       name=COALESCE(excluded.name,users.name), updated_at=excluded.updated_at""",
                  (uid, email, name, now, now))


# --- swarms ---
def _swarm_out(r):
    if not r:
        return None
    d = dict(r)
    d["agents"] = _pj(d.get("agents"), []); d["handoffs"] = _pj(d.get("handoffs"), [])
    return d


def list_swarms(v=None):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM swarms WHERE {_vis()} ORDER BY updated_at DESC", (v,)).fetchall()
    return [_swarm_out(r) for r in rows]


def get_swarm(sid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM swarms WHERE id=? AND {_vis()}", (sid, v)).fetchone()
    return _swarm_out(r)


def create_swarm(d, owner):
    sid = new_id("swarm"); now = now_iso()
    agents = d.get("agents") or []
    entry = d.get("entry_agent") or (agents[0].get("key") if agents else "")
    with _conn() as c:
        c.execute("""INSERT INTO swarms (id,owner_user_id,name,slug,description,goal,agents,handoffs,entry_agent,max_steps,model,version,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,'1.0.0',?,?)""",
                  (sid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("goal", ""),
                   _j(agents), _j(d.get("handoffs", [])), entry, int(d.get("max_steps", 8)),
                   d.get("model", "auto"), now, now))
    return get_swarm(sid, owner)


def update_swarm(sid, owner, d):
    cur = get_swarm(sid, owner)
    if not cur or (cur.get("owner_user_id") and cur["owner_user_id"] != owner):
        return None
    agents = d.get("agents") if d.get("agents") is not None else cur["agents"]
    entry = d.get("entry_agent") or cur.get("entry_agent") or (agents[0].get("key") if agents else "")
    with _conn() as c:
        c.execute("""UPDATE swarms SET name=?, description=?, goal=?, agents=?, handoffs=?, entry_agent=?, max_steps=?, model=?, updated_at=? WHERE id=?""",
                  (d.get("name", cur["name"]), d.get("description", cur["description"]), d.get("goal", cur["goal"]),
                   _j(agents), _j(d.get("handoffs") if d.get("handoffs") is not None else cur["handoffs"]),
                   entry, int(d.get("max_steps", cur["max_steps"])), d.get("model", cur["model"]), now_iso(), sid))
    return get_swarm(sid, owner)


def delete_swarm(sid, owner):
    cur = get_swarm(sid, owner)
    if not cur or (cur.get("owner_user_id") and cur["owner_user_id"] != owner):
        return False
    with _conn() as c:
        c.execute("DELETE FROM swarms WHERE id=?", (sid,))
    return True


# --- runs ---
def create_run(swarm, task_input, model, owner, correlation_id):
    rid = new_id("srun")
    with _conn() as c:
        c.execute("""INSERT INTO swarm_runs (id,owner_user_id,swarm_id,swarm_name,model,task_input,status,correlation_id,created_at)
                     VALUES (?,?,?,?,?,?,'running',?,?)""",
                  (rid, owner, swarm["id"], swarm["name"], model, task_input, correlation_id, now_iso()))
    return rid


def finish_run(rid, res):
    with _conn() as c:
        c.execute("""UPDATE swarm_runs SET status=?, outcome=?, trace=?, final_output=?, steps_used=?,
                     prompt_tokens=?, completion_tokens=?, total_tokens=?, cost_usd=?, latency_ms=?, error=?, finished_at=?
                     WHERE id=?""",
                  (res.get("status", "failed"), res.get("outcome"), _j(res.get("trace", [])), res.get("final_output"),
                   res.get("steps_used"), res.get("prompt_tokens"), res.get("completion_tokens"),
                   res.get("total_tokens"), res.get("cost_usd"), res.get("latency_ms"), res.get("error"), now_iso(), rid))


def _run_out(r):
    if not r:
        return None
    d = dict(r); d["trace"] = _pj(d.get("trace"), []); return d


def list_runs(v=None, limit=100):
    with _conn() as c:
        rows = c.execute(f"""SELECT id,owner_user_id,swarm_id,swarm_name,model,task_input,status,outcome,steps_used,
                             total_tokens,cost_usd,latency_ms,created_at FROM swarm_runs WHERE {_vis()}
                             ORDER BY created_at DESC LIMIT ?""", (v, limit)).fetchall()
    return [dict(r) for r in rows]


def get_run(rid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM swarm_runs WHERE id=? AND {_vis()}", (rid, v)).fetchone()
    return _run_out(r)


def stats(v=None):
    with _conn() as c:
        swarms = c.execute(f"SELECT COUNT(*) n FROM swarms WHERE {_vis()}", (v,)).fetchone()["n"]
        runs = c.execute(f"SELECT COUNT(*) n FROM swarm_runs WHERE {_vis()}", (v,)).fetchone()["n"]
        row = c.execute(f"""SELECT COALESCE(SUM(cost_usd),0) cost, COALESCE(AVG(steps_used),0) steps,
                            SUM(CASE WHEN outcome='completed' THEN 1 ELSE 0 END) done FROM swarm_runs WHERE {_vis()}""", (v,)).fetchone()
    return {"swarms": swarms, "runs": runs, "spend_usd": round(row["cost"] or 0, 4),
            "avg_steps": round(row["steps"] or 0, 1), "completed": row["done"] or 0}
