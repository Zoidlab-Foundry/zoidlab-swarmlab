"""SwarmLab assistant manifest — what the in-app assistant knows and may do.

The security boundary: only these capabilities exist for the assistant, and they run through
this app's own session-authed API (require_pro + RLS apply). No deletes are declared.
"""
from foundry_common.assistant import cap, page

MANIFEST = {
    "app": "SwarmLab",
    "description": (
        "SwarmLab turns one task into a team. A swarm is a set of role-specialized agents "
        "plus a TYPED HANDOFF GRAPH declaring who may pass control to whom; the orchestrator "
        "rejects any undeclared handoff, bounds the run with a max-steps ceiling, and records "
        "a full step-by-step trace so any run can be replayed. Runs are DURABLE BACKGROUND "
        "JOBS: starting one returns a job that survives a page close — the trace and final "
        "output appear on the Runs page when it completes."
    ),
    "base_url": "http://127.0.0.1:8707",
    "pages": [
        page("/", "Dashboard", "Overview: swarms, recent runs, relay status."),
        page("/swarms", "Swarms", "Design swarms: agents with roles, the handoff graph, entry agent, step cap.",
             assists={"new-swarm": "the New swarm button"}),
        page("/run", "Run", "Give a swarm a task and launch a real multi-agent run.",
             assists={"run-swarm": "the Run swarm button"}),
        page("/runs", "Runs", "Every run with outcome, steps used, cost and the full replayable trace."),
    ],
    "capabilities": [
        cap("list_swarms", "GET", "/api/swarms", risk="read",
            desc="The user's swarms with agent and handoff counts."),
        cap("get_swarm", "GET", "/api/swarms/{sid}", risk="read",
            desc="One swarm: its agents, roles, handoff edges and entry agent.",
            params={"sid": "swarm id"}),
        cap("list_runs", "GET", "/api/runs", risk="read",
            desc="Swarm runs, newest first, with outcome and steps used."),
        cap("get_run", "GET", "/api/runs/{rid}", risk="read",
            desc="One run: final output, outcome, per-step trace, tokens and cost.",
            params={"rid": "run id"}),
        cap("get_job", "GET", "/api/jobs/{jid}", risk="read",
            desc="Status of a background swarm job (queued/running/succeeded/failed).",
            params={"jid": "job id"}),
        cap("stats", "GET", "/api/stats", risk="read",
            desc="Counts of swarms and runs plus relay availability."),
        cap("create_swarm", "POST", "/api/swarms", risk="write",
            desc="Create a swarm. agents is a list of role objects; handoffs is the list of "
                 "allowed edges between them (an undeclared edge is rejected at run time); "
                 "entry_agent names which agent starts.",
            params={"name": "swarm name", "description": "short description",
                    "goal": "what the swarm is for", "agents": "list of agent objects (key, name, role, instruction)",
                    "handoffs": "list of allowed handoff edges", "entry_agent": "key of the starting agent",
                    "max_steps": "step ceiling (default 8)", "model": "model id or 'auto'"}),
        cap("run_swarm", "POST", "/api/run", risk="write",
            desc="Run a swarm on a task. Every agent turn is a real relay call billed to the "
                 "user's own Nyquest wallet; returns a durable job to watch on Runs.",
            params={"swarm_id": "swarm id", "task_input": "the task for the swarm",
                    "model": "model id (optional)", "max_steps": "override the step cap (optional)"}),
    ],
}
