"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

type Agent = { key: string; name: string; role: string; system: string };
type Edge = { from: string; to: string };

const blankAgent = (): Agent => ({ key: "", name: "", role: "", system: "" });

export default function SwarmsPage() {
  const [swarms, setSwarms] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [maxSteps, setMaxSteps] = useState(6);
  const [agents, setAgents] = useState<Agent[]>([blankAgent(), blankAgent()]);
  const [edges, setEdges] = useState<Edge[]>([{ from: "", to: "" }]);
  const [entry, setEntry] = useState("");

  const load = () => { api.swarms().then(setSwarms).catch(() => {}); };
  useEffect(() => { load(); }, []);

  function reset() {
    setName(""); setGoal(""); setMaxSteps(6); setAgents([blankAgent(), blankAgent()]); setEdges([{ from: "", to: "" }]); setEntry("");
  }

  const validKeys = agents.map((a) => a.key.trim()).filter(Boolean);

  async function save() {
    if (!name.trim() || validKeys.length < 1) return;
    setSaving(true);
    try {
      await api.createSwarm({
        name: name.trim(), goal,
        agents: agents.filter((a) => a.key.trim()).map((a) => ({ ...a, key: a.key.trim() })),
        handoffs: edges.filter((e) => e.from && e.to),
        entry_agent: entry || validKeys[0], max_steps: maxSteps,
      });
      setOpen(false); reset(); load();
    } finally { setSaving(false); }
  }

  async function del(id: string) { await api.deleteSwarm(id).catch(() => {}); load(); }

  return (
    <div className="py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">Swarms</h1>
          <p className="mt-1 text-[13px] text-dim">A swarm is a set of agents plus a typed handoff graph — who may pass control to whom. The orchestrator enforces those edges at run time.</p>
        </div>
        <button onClick={() => setOpen(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">New swarm</button>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {swarms.map((sw) => (
          <div key={sw.id} className="rounded-2xl border border-line bg-panel p-4">
            <div className="flex items-start justify-between gap-2">
              <div className="text-[14px] font-semibold text-ink">{sw.name}</div>
              <span className="rounded-full bg-vi/10 px-2 py-0.5 text-[10.5px] text-vi">{(sw.agents || []).length} agents · {(sw.handoffs || []).length} edges</span>
            </div>
            {sw.goal && <p className="mt-1.5 line-clamp-2 text-[12.5px] text-dim">{sw.goal}</p>}
            <div className="mt-2 flex flex-wrap gap-1.5">
              {(sw.agents || []).map((a: Agent) => (
                <span key={a.key} className={`rounded-md border px-1.5 py-0.5 text-[10.5px] ${a.key === sw.entry_agent ? "border-vi/40 text-vi" : "border-line text-dim"}`}>{a.name || a.key}{a.key === sw.entry_agent ? " ◆" : ""}</span>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-3 text-[12px]">
              <Link href={`/run?swarm=${sw.id}`} className="font-medium text-cy hover:underline">Run →</Link>
              <a href={api.exportUrl(sw.id)} target="_blank" className="text-dim hover:text-ink">Export</a>
              <button onClick={() => del(sw.id)} className="ml-auto text-faint hover:text-bad">delete</button>
            </div>
          </div>
        ))}
        {!swarms.length && <div className="md:col-span-2 rounded-2xl border border-line bg-panel p-8 text-center text-[13px] text-faint">No swarms yet.</div>}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm">
          <div className="mt-8 w-full max-w-3xl rounded-2xl border border-line bg-panel p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-semibold">New swarm</h2>
              <button onClick={() => setOpen(false)} className="text-faint hover:text-ink">✕</button>
            </div>
            <div className="mt-4 grid gap-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block"><span className="text-[12px] text-dim">Name</span>
                  <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Research → Write → Critique" className={inp} /></label>
                <label className="block"><span className="text-[12px] text-dim">Max steps (cap 16)</span>
                  <input type="number" min={2} max={16} value={maxSteps} onChange={(e) => setMaxSteps(Number(e.target.value))} className={inp} /></label>
              </div>
              <label className="block"><span className="text-[12px] text-dim">Goal</span>
                <input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="What the team should accomplish." className={inp} /></label>

              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-dim">Agents</span>
                  <button onClick={() => setAgents([...agents, blankAgent()])} className="text-[12px] text-cy hover:underline">+ agent</button>
                </div>
                <div className="mt-2 space-y-2">
                  {agents.map((a, i) => (
                    <div key={i} className="rounded-lg border border-line bg-panel2 p-2.5">
                      <div className="flex gap-2">
                        <input value={a.key} onChange={(e) => setAgents(agents.map((x, j) => j === i ? { ...x, key: e.target.value } : x))} placeholder="key" className={`${inp} w-28`} />
                        <input value={a.name} onChange={(e) => setAgents(agents.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} placeholder="name" className={`${inp} w-40`} />
                        <input value={a.role} onChange={(e) => setAgents(agents.map((x, j) => j === i ? { ...x, role: e.target.value } : x))} placeholder="role" className={`${inp} flex-1`} />
                        <button onClick={() => setAgents(agents.filter((_, j) => j !== i))} className="px-1 text-faint hover:text-bad">✕</button>
                      </div>
                      <input value={a.system} onChange={(e) => setAgents(agents.map((x, j) => j === i ? { ...x, system: e.target.value } : x))} placeholder="system instruction (optional)" className={`${inp} mt-2`} />
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] text-dim">Handoff edges</span>
                    <button onClick={() => setEdges([...edges, { from: "", to: "" }])} className="text-[12px] text-cy hover:underline">+ edge</button>
                  </div>
                  <div className="mt-2 space-y-2">
                    {edges.map((e, i) => (
                      <div key={i} className="flex items-center gap-1.5">
                        <select value={e.from} onChange={(ev) => setEdges(edges.map((x, j) => j === i ? { ...x, from: ev.target.value } : x))} className={`${inp} flex-1`}>
                          <option value="">from…</option>{validKeys.map((k) => <option key={k} value={k}>{k}</option>)}
                        </select>
                        <span className="text-dim">→</span>
                        <select value={e.to} onChange={(ev) => setEdges(edges.map((x, j) => j === i ? { ...x, to: ev.target.value } : x))} className={`${inp} flex-1`}>
                          <option value="">to…</option>{validKeys.map((k) => <option key={k} value={k}>{k}</option>)}
                        </select>
                        <button onClick={() => setEdges(edges.filter((_, j) => j !== i))} className="px-1 text-faint hover:text-bad">✕</button>
                      </div>
                    ))}
                  </div>
                </div>
                <label className="block"><span className="text-[12px] text-dim">Entry agent</span>
                  <select value={entry} onChange={(e) => setEntry(e.target.value)} className={inp}>
                    <option value="">{validKeys[0] || "first agent"}</option>{validKeys.map((k) => <option key={k} value={k}>{k}</option>)}
                  </select></label>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setOpen(false)} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
              <button onClick={save} disabled={saving || !name.trim() || validKeys.length < 1} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
                {saving ? "Saving…" : "Create swarm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inp = "mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50";
