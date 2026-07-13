"""Postgres data layer for SwarmLab with per-tenant Row-Level Security (§3.2).

Tenant isolation is DB-enforced (FORCE RLS keyed on app.current_owner). App connections use
the RLS-enforced role; DDL + cross-tenant admin use the superuser. Public API mirrors the
former sqlite database.py.
"""
import os
import uuid
import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://app_rls@127.0.0.1:5433/swarmlab")
DATABASE_URL_ADMIN = os.environ.get("DATABASE_URL_ADMIN", "postgresql://foundry@127.0.0.1:5433/swarmlab")
_pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, open=True, kwargs={"autocommit": False})


def admin_conn():
    return psycopg.connect(DATABASE_URL_ADMIN, row_factory=dict_row)


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


class _tx:
    def __init__(self, owner):
        self.owner = owner or ""

    def __enter__(self):
        self.conn = _pool.getconn()
        self.cur = self.conn.cursor(row_factory=dict_row)
        self.cur.execute("SELECT set_config('app.current_owner', %s, true)", (self.owner,))
        return self.cur

    def __exit__(self, exc_type, exc, tb):
        try:
            self.conn.rollback() if exc_type else self.conn.commit()
        finally:
            self.cur.close()
            _pool.putconn(self.conn)


_TENANT_TABLES = ["swarms", "swarm_runs", "jobs"]


def init():
    with admin_conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT, name TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS swarms (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
            goal TEXT, agents JSONB, handoffs JSONB, entry_agent TEXT, max_steps INTEGER DEFAULT 8,
            model TEXT DEFAULT 'auto', version TEXT DEFAULT '1.0.0', created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS swarm_runs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, swarm_id TEXT, swarm_name TEXT, model TEXT,
            task_input TEXT, status TEXT DEFAULT 'queued', outcome TEXT, trace JSONB, final_output TEXT,
            steps_used INTEGER, prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER,
            cost_usd DOUBLE PRECISION, latency_ms INTEGER, error TEXT, correlation_id TEXT, created_at TEXT, finished_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, status TEXT, error TEXT,
            attempts INTEGER DEFAULT 0, celery_id TEXT, timeout_s INTEGER, created_at TEXT, started_at TEXT, finished_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS dead_letters (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, error TEXT, created_at TEXT)""")
        for t in _TENANT_TABLES:
            c.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
            c.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
            c.execute(f"DROP POLICY IF EXISTS {t}_isolation ON {t}")
            c.execute(f"""CREATE POLICY {t}_isolation ON {t}
                USING (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))
                WITH CHECK (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_srun_owner ON swarm_runs(owner_user_id, created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_owner ON jobs(owner_user_id, created_at)")
        c.execute("GRANT USAGE ON SCHEMA public TO app_rls")
        c.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO app_rls")


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _pool.connection() as c:
        c.execute("""INSERT INTO users (id,email,name,created_at,updated_at) VALUES (%s,%s,%s,%s,%s)
                     ON CONFLICT (id) DO UPDATE SET email=COALESCE(EXCLUDED.email,users.email),
                       name=COALESCE(EXCLUDED.name,users.name), updated_at=EXCLUDED.updated_at""",
                  (uid, email, name, now, now))


# --- swarms ---
def list_swarms(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM swarms ORDER BY updated_at DESC")
        return cur.fetchall()


def get_swarm(sid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM swarms WHERE id=%s", (sid,))
        return cur.fetchone()


def create_swarm(d, owner):
    sid = new_id("swarm"); now = now_iso()
    agents = d.get("agents") or []
    entry = d.get("entry_agent") or (agents[0].get("key") if agents else "")
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO swarms (id,owner_user_id,name,slug,description,goal,agents,handoffs,entry_agent,max_steps,model,version,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'1.0.0',%s,%s)""",
                    (sid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("goal", ""),
                     Json(agents), Json(d.get("handoffs", [])), entry, int(d.get("max_steps", 8)),
                     d.get("model", "auto"), now, now))
    return get_swarm(sid, owner)


def update_swarm(sid, owner, d):
    cur_s = get_swarm(sid, owner)
    if not cur_s or (cur_s.get("owner_user_id") and cur_s["owner_user_id"] != owner):
        return None
    agents = d.get("agents") if d.get("agents") is not None else cur_s["agents"]
    entry = d.get("entry_agent") or cur_s.get("entry_agent") or (agents[0].get("key") if agents else "")
    with _tx(owner) as cur:
        cur.execute("""UPDATE swarms SET name=%s, description=%s, goal=%s, agents=%s, handoffs=%s, entry_agent=%s, max_steps=%s, model=%s, updated_at=%s WHERE id=%s""",
                    (d.get("name", cur_s["name"]), d.get("description", cur_s["description"]), d.get("goal", cur_s["goal"]),
                     Json(agents), Json(d.get("handoffs") if d.get("handoffs") is not None else cur_s["handoffs"]),
                     entry, int(d.get("max_steps", cur_s["max_steps"])), d.get("model", cur_s["model"]), now_iso(), sid))
    return get_swarm(sid, owner)


def delete_swarm(sid, owner):
    cur_s = get_swarm(sid, owner)
    if not cur_s or (cur_s.get("owner_user_id") and cur_s["owner_user_id"] != owner):
        return False
    with _tx(owner) as cur:
        cur.execute("DELETE FROM swarms WHERE id=%s", (sid,))
    return True


# --- runs ---
def create_run(swarm, task_input, model, owner, correlation_id):
    rid = new_id("srun")
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO swarm_runs (id,owner_user_id,swarm_id,swarm_name,model,task_input,status,correlation_id,created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,'queued',%s,%s)""",
                    (rid, owner, swarm["id"], swarm["name"], model, task_input, correlation_id, now_iso()))
    return rid


def finish_run(rid, res, owner=None):
    with _tx(owner) as cur:
        cur.execute("""UPDATE swarm_runs SET status=%s, outcome=%s, trace=%s, final_output=%s, steps_used=%s,
                       prompt_tokens=%s, completion_tokens=%s, total_tokens=%s, cost_usd=%s, latency_ms=%s, error=%s, finished_at=%s
                       WHERE id=%s""",
                    (res.get("status", "failed"), res.get("outcome"), Json(res.get("trace", [])), res.get("final_output"),
                     res.get("steps_used"), res.get("prompt_tokens"), res.get("completion_tokens"),
                     res.get("total_tokens"), res.get("cost_usd"), res.get("latency_ms"), res.get("error"), now_iso(), rid))


def set_run_status(rid, status, owner=None):
    with _tx(owner) as cur:
        cur.execute("UPDATE swarm_runs SET status=%s WHERE id=%s", (status, rid))


def list_runs(v=None, limit=100):
    with _tx(v) as cur:
        cur.execute("""SELECT id,owner_user_id,swarm_id,swarm_name,model,task_input,status,outcome,steps_used,
                       total_tokens,cost_usd,latency_ms,created_at FROM swarm_runs ORDER BY created_at DESC LIMIT %s""", (limit,))
        return cur.fetchall()


def get_run(rid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM swarm_runs WHERE id=%s", (rid,))
        return cur.fetchone()


def stats(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT COUNT(*) n FROM swarms"); swarms = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM swarm_runs"); runs = cur.fetchone()["n"]
        cur.execute("""SELECT COALESCE(SUM(cost_usd),0) cost, COALESCE(AVG(steps_used),0) steps,
                       COALESCE(SUM(CASE WHEN outcome='completed' THEN 1 ELSE 0 END),0) done FROM swarm_runs""")
        row = cur.fetchone()
    return {"swarms": swarms, "runs": runs, "spend_usd": round(row["cost"] or 0, 4),
            "avg_steps": round(row["steps"] or 0, 1), "completed": row["done"] or 0}
