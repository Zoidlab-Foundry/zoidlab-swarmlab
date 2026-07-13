"""Real multi-agent orchestration through the Nyquest relay.

A swarm is a set of role-specialized agents plus a set of TYPED HANDOFF edges (who may hand
off to whom). Running a swarm is real: each active agent is a genuine relay completion; the
agent may end its turn with a control directive:

    [[HANDOFF:<agent_key>]]  — pass control to another agent (only allowed if an edge exists)
    [[DONE]]                 — finish the run with its message as the final answer

The orchestrator enforces the handoff contract (an unknown or disallowed target is rejected
and recorded, not followed), bounds the run by a max-steps ceiling, and records a full
step-by-step trace so any run can be replayed. Token usage and cost are summed across steps.
"""
import re
import time
import llm
import pricing

DEFAULT_MODEL = "openai/gpt-4o-mini"
MAX_STEPS_CAP = 16   # bounded runtime — hard ceiling regardless of request

_HANDOFF_RE = re.compile(r"\[\[HANDOFF:\s*([a-zA-Z0-9_\-]+)\s*\]\]")
_DONE_RE = re.compile(r"\[\[DONE\]\]")


def _agent_map(swarm):
    return {a.get("key"): a for a in (swarm.get("agents") or []) if a.get("key")}


def _edges_for(swarm, key):
    return [e.get("to") for e in (swarm.get("handoffs") or []) if e.get("from") == key]


def _agent_system(agent, swarm, allowed_targets):
    parts = [f"You are the '{agent.get('name') or agent.get('key')}' agent in a multi-agent team working on one shared task."]
    if agent.get("role"):
        parts.append("Your role: " + agent["role"])
    if agent.get("system"):
        parts.append(agent["system"])
    parts.append("The overall goal: " + (swarm.get("goal") or "complete the task the user gave the team."))
    if allowed_targets:
        listing = ", ".join(f"'{t}'" for t in allowed_targets)
        parts.append(f"When another agent should take over, END your message with [[HANDOFF:<key>]] where <key> is one of: {listing}. "
                     "Hand off only when it genuinely helps.")
    else:
        parts.append("You have no downstream agents.")
    parts.append("When the task is fully complete, END your message with [[DONE]] and give the final answer first. "
                 "Keep each turn focused; do the part that is yours, don't repeat others. "
                 "You MUST end every message with exactly one control directive: [[HANDOFF:<key>]] or [[DONE]].")
    return "\n".join(parts)


def _clean(text):
    return _DONE_RE.sub("", _HANDOFF_RE.sub("", text or "")).strip()


async def run(swarm, task_input, model, max_steps, relay_key=None):
    if not llm.available() and not relay_key:
        return {"status": "failed", "error": "No relay key configured — real orchestration needs NYQUEST_API_KEY."}
    model = model or swarm.get("model") or DEFAULT_MODEL
    if model == "auto":
        model = DEFAULT_MODEL
    agents = _agent_map(swarm)
    if not agents:
        return {"status": "failed", "error": "Swarm has no agents."}
    current = swarm.get("entry_agent") or next(iter(agents))
    if current not in agents:
        return {"status": "failed", "error": f"Entry agent '{current}' is not defined."}
    steps = min(int(max_steps or 8), MAX_STEPS_CAP)

    trace = []
    blackboard = [f"TASK: {task_input}"]
    pt = ct = 0
    t0 = time.perf_counter()
    final_output = None
    outcome = "incomplete"

    try:
        for i in range(steps):
            agent = agents[current]
            allowed = [t for t in _edges_for(swarm, current) if t in agents]
            sys = _agent_system(agent, swarm, allowed)
            convo = "\n\n".join(blackboard[-12:])
            msgs = [{"role": "system", "content": sys},
                    {"role": "user", "content": f"Shared context so far:\n{convo}\n\nContinue as the '{agent.get('name') or current}' agent."}]
            txt, u = await llm.chat(model, msgs, temperature=0.5, max_tokens=500)
            pt += int(u.get("prompt_tokens") or 0); ct += int(u.get("completion_tokens") or 0)
            clean = _clean(txt)
            done = bool(_DONE_RE.search(txt))
            m = _HANDOFF_RE.search(txt)
            target = m.group(1) if m else None
            handoff_status = None
            next_agent = None
            if not done and target:
                if target in allowed:
                    next_agent = target; handoff_status = "accepted"
                elif target in agents:
                    handoff_status = "rejected_no_edge"    # contract violation — not followed
                else:
                    handoff_status = "rejected_unknown_agent"
            trace.append({"step": i + 1, "agent_key": current, "agent_name": agent.get("name") or current,
                          "output": clean, "handoff_to": target, "handoff_status": handoff_status,
                          "done": done})
            blackboard.append(f"[{agent.get('name') or current}]: {clean}")
            if done:
                final_output = clean; outcome = "completed"; break
            if next_agent:
                current = next_agent
            elif not target:
                # No explicit directive. Follow the typed graph: a single outgoing edge is an
                # implicit sequential handoff; a terminal agent (no edges) ends the run; a
                # branch point with no choice is ambiguous and halts.
                if len(allowed) == 1:
                    trace[-1]["handoff_to"] = allowed[0]; trace[-1]["handoff_status"] = "implicit"
                    current = allowed[0]
                elif len(allowed) == 0:
                    final_output = clean; outcome = "completed"; break
                else:
                    final_output = clean; outcome = "halted_ambiguous"; break
            else:
                # attempted an invalid handoff to a real agent with no edge: stay this step,
                # the bound (max_steps) prevents an infinite loop
                continue
        if final_output is None:
            final_output = trace[-1]["output"] if trace else ""
            outcome = outcome if outcome != "incomplete" else "max_steps_reached"
    except Exception as e:
        return {"status": "failed", "error": str(e)[:400], "trace": trace,
                "latency_ms": int((time.perf_counter() - t0) * 1000)}

    cost, _ = pricing.cost_for(model, pt, ct)
    return {"status": "completed", "trace": trace, "final_output": final_output, "outcome": outcome,
            "steps_used": len(trace), "prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct,
            "cost_usd": cost, "latency_ms": int((time.perf_counter() - t0) * 1000),
            "usage": {"model": model, "prompt_tokens": pt, "completion_tokens": ct}}
