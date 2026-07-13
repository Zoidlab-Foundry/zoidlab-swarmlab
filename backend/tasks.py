"""Celery tasks for SwarmLab — the real multi-agent orchestration runs here, in the worker."""
import asyncio

from celery.exceptions import SoftTimeLimitExceeded

from celery_app import app
import db_pg as db
import swarm_engine
import foundry
import jobs


@app.task(bind=True, name="swarmlab.run_swarm", max_retries=2,
          autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True, retry_jitter=True)
def run_swarm(self, job_id, run_id, swarm_id, task_input, model, max_steps, owner, corr, relay_key, session_token):
    jobs.mark_running(job_id, owner, attempts=self.request.retries + 1)
    db.set_run_status(run_id, "running", owner)
    try:
        swarm = db.get_swarm(swarm_id, owner)
        if not swarm:
            raise RuntimeError("swarm not found for run")
        foundry.set_session(session_token)
        res = asyncio.run(swarm_engine.run(swarm, task_input, model, max_steps, relay_key=relay_key))
        try:
            asyncio.run(foundry.emit_spend(res.get("usage"), resource_id=run_id, feature=swarm.get("name"),
                                           correlation_id=corr, environment="development"))
        except Exception:
            pass
        db.finish_run(run_id, res, owner)
        jobs.mark_terminal(job_id, owner, res)
        return {"status": res.get("status")}
    except SoftTimeLimitExceeded:
        db.finish_run(run_id, {"status": "failed", "error": "timed out (soft limit)"}, owner)
        jobs.mark(job_id, owner, "timed_out", "soft time limit exceeded")
        return {"status": "timed_out"}
    except Exception as e:
        if self.request.retries >= self.max_retries:
            db.finish_run(run_id, {"status": "failed", "error": str(e)[:400]}, owner)
            jobs.mark(job_id, owner, "failed", str(e)[:400], dead=True)
            return {"status": "failed"}
        raise
