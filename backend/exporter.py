"""SwarmLab package export — a portable multi-agent swarm (agents + typed handoff graph)
wrapped in the canonical Foundry base envelope (blueprint §6.2). No secrets are included."""
import envelope


def to_package(swarm, owner=None):
    payload = {
        "schema_version": "1.0",
        "package_type": "nyquest_swarm_package",
        "foundry_package": "swarm",
        "resource_version": swarm.get("version", "1.0.0"),
        "swarm": {"name": swarm.get("name"), "description": swarm.get("description"),
                  "goal": swarm.get("goal"), "entry_agent": swarm.get("entry_agent"),
                  "max_steps": swarm.get("max_steps"), "model": swarm.get("model")},
        "agents": swarm.get("agents", []),
        "handoff_contract": swarm.get("handoffs", []),
        "runtime": {"bounded_by": "max_steps", "hard_cap": 16, "replayable": True},
        "governance": {"human_review": True},
        "dependencies": [],
        "credential_refs": [],
    }
    return envelope.wrap("swarm", "swarm", swarm.get("id"), swarm.get("version", "1.0.0"),
                         payload, nyquest_user_id=owner)
