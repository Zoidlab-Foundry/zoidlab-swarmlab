"use client";
import { useEffect, useState } from "react";

/* In-app guide: what SwarmLab is and how to run your first swarm.
   Auto-opens once per browser (localStorage) and lives behind the Guide nav button. */

const STORAGE_KEY = "sw_guide_v1";

const STEPS: { title: string; body: string }[] = [
  {
    title: "Design your swarm",
    body: "On Swarms, click New swarm. Name it, give the team a goal, and add agents — each gets a key, a name, and a role (e.g. researcher, writer, critic).",
  },
  {
    title: "Brief each agent",
    body: "An optional system instruction shapes how each agent behaves on its turn. Turns are real model calls through the Nyquest relay — nothing is simulated.",
  },
  {
    title: "Wire the handoff graph",
    body: "Declare typed handoff edges — who may pass control to whom — then pick the entry agent and a step cap (up to 16). The orchestrator enforces those edges at run time.",
  },
  {
    title: "Launch a real run",
    body: "On Run, pick a swarm and give it a task. The run queues as a durable background job, and agents take live turns, handing off along the declared edges until the task is done or the cap is hit.",
  },
  {
    title: "Replay the collaboration",
    body: "Runs lists every run with its outcome, step count, cost, and latency. Open one to replay the full turn-by-turn trace, read the final output, and inspect token counts and the correlation ID.",
  },
  {
    title: "Export the package",
    body: "Any swarm exports from the Swarms page as a signed Foundry package — the agents plus handoff graph in a canonical envelope with an integrity digest, no secrets included.",
  },
];

export default function HelpGuide() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) setOpen(true);
    } catch {}
  }, []);

  const dismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") dismiss(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim transition hover:text-ink hover:bg-white/5"
        aria-label="Open the SwarmLab guide"
      >
        Guide
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={dismiss} role="dialog" aria-modal="true" aria-label="SwarmLab guide">
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-line bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-1 flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-vi/15 text-[13px] text-vi">✺</span>
              <h2 className="text-[16px] font-semibold">How SwarmLab works</h2>
            </div>
            <p className="mb-5 text-[13px] text-dim">
              Design a multi-agent swarm, then watch real agents collaborate turn by turn along a handoff graph you control. Six steps from zero to a replayable run:
            </p>
            <ol className="space-y-4">
              {STEPS.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-vi/15 text-[12px] font-semibold text-vi">{i + 1}</span>
                  <div>
                    <div className="text-[13.5px] font-medium">{s.title}</div>
                    <div className="text-[12.5px] leading-relaxed text-dim">{s.body}</div>
                  </div>
                </li>
              ))}
            </ol>
            <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
              <a href="https://foundry.zoidlab.ai" className="text-[12px] text-dim hover:text-ink">◈ All Foundry apps</a>
              <button onClick={dismiss} className="rounded-lg bg-vi px-4 py-1.5 text-[12.5px] font-semibold text-black hover:opacity-90">
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
