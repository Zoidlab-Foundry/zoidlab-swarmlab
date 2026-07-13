"""Seed SwarmLab with demo swarms (real agent + typed-handoff definitions).
No runs are seeded — runs come only from real relay orchestration the user triggers."""
import database as db

_SWARMS = [
    {"name": "Research → Write → Critique",
     "description": "A researcher gathers points, a writer drafts, a critic reviews and finalizes.",
     "goal": "Produce a tight, accurate short piece on the user's topic.",
     "entry_agent": "researcher",
     "agents": [
        {"key": "researcher", "name": "Researcher", "role": "Gather the key facts and angles.",
         "system": "List the most important, verifiable points on the topic. Be concise."},
        {"key": "writer", "name": "Writer", "role": "Draft the piece from the research.",
         "system": "Write a clear, well-structured draft using the researcher's points."},
        {"key": "critic", "name": "Critic", "role": "Review, tighten, and finalize.",
         "system": "Critique the draft for accuracy and clarity, then output the final improved version."},
     ],
     "handoffs": [{"from": "researcher", "to": "writer"}, {"from": "writer", "to": "critic"},
                  {"from": "critic", "to": "writer"}],
     "max_steps": 6},
    {"name": "Support Triage → Specialist",
     "description": "A triage agent classifies an incoming issue and hands off to the right specialist.",
     "goal": "Resolve the customer's issue or route it to the correct specialist with a clear summary.",
     "entry_agent": "triage",
     "agents": [
        {"key": "triage", "name": "Triage", "role": "Classify the issue and route it.",
         "system": "Decide whether this is a billing or a technical issue, summarize it, and hand off."},
        {"key": "billing", "name": "Billing Specialist", "role": "Handle billing issues.",
         "system": "Resolve billing questions clearly and finish."},
        {"key": "tech", "name": "Tech Specialist", "role": "Handle technical issues.",
         "system": "Troubleshoot the technical issue step by step and finish."},
     ],
     "handoffs": [{"from": "triage", "to": "billing"}, {"from": "triage", "to": "tech"}],
     "max_steps": 5},
    {"name": "Plan → Execute → Verify",
     "description": "A planner breaks down a task, an executor does each part, a verifier checks the result.",
     "goal": "Complete the user's task and verify the output meets the request.",
     "entry_agent": "planner",
     "agents": [
        {"key": "planner", "name": "Planner", "role": "Break the task into concrete steps.",
         "system": "Produce a short ordered plan for the task, then hand off."},
        {"key": "executor", "name": "Executor", "role": "Carry out the plan.",
         "system": "Execute the plan and produce the concrete result."},
        {"key": "verifier", "name": "Verifier", "role": "Check the result against the task.",
         "system": "Verify the executor's result satisfies the task; if good, finalize; if not, hand back."},
     ],
     "handoffs": [{"from": "planner", "to": "executor"}, {"from": "executor", "to": "verifier"},
                  {"from": "verifier", "to": "executor"}],
     "max_steps": 7},
]


def run():
    if db.list_swarms(None):
        return 0
    for s in _SWARMS:
        db.create_swarm(s, owner=None)
    return len(_SWARMS)
