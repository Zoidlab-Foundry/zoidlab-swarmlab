"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, usd, ms } from "../../lib/api";
import { Trace, FinalOutput } from "../../components/Trace";

function RunInner() {
  const params = useSearchParams();
  const [swarms, setSwarms] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [swarmId, setSwarmId] = useState(params.get("swarm") || "");
  const [task, setTask] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.swarms().then(setSwarms).catch(() => {});
    api.meta().then(setMeta).catch(() => {});
  }, []);

  const swarm = swarms.find((s) => s.id === swarmId);

  async function run() {
    if (!swarmId || !task.trim()) return;
    setRunning(true); setErr(null); setResult(null);
    try {
      const r = await api.run({ swarm_id: swarmId, task_input: task.trim() });
      setResult(r);
    } catch (e: any) { setErr(e.message || "run failed"); }
    finally { setRunning(false); }
  }

  return (
    <div className="py-8">
      <h1 className="text-[22px] font-semibold">Run a swarm</h1>
      <p className="mt-1 text-[13px] text-dim">Pick a swarm and give it a task. Agents will take real turns and hand off along the declared edges until the task is done or the step cap is reached.</p>

      {meta && !meta.relay_available && (
        <div className="mt-4 rounded-xl border border-warn/30 bg-warn/5 px-4 py-2.5 text-[12.5px] text-warn">
          Relay key not configured — real runs are unavailable until <code className="text-ink">NYQUEST_API_KEY</code> is set on the server.
        </div>
      )}

      <div className="mt-5 rounded-2xl border border-line bg-panel p-5">
        <label className="block"><span className="text-[12px] text-dim">Swarm</span>
          <select value={swarmId} onChange={(e) => setSwarmId(e.target.value)} className={inp}>
            <option value="">Select a swarm…</option>
            {swarms.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select></label>
        {swarm && (
          <div className="mt-2 flex flex-wrap items-center gap-1.5 rounded-lg border border-line bg-panel2 p-3">
            {(swarm.agents || []).map((a: any) => (
              <span key={a.key} className={`rounded-md border px-1.5 py-0.5 text-[10.5px] ${a.key === swarm.entry_agent ? "border-vi/40 text-vi" : "border-line text-dim"}`}>{a.name || a.key}</span>
            ))}
            <span className="ml-2 text-[11px] text-faint">{(swarm.handoffs || []).length} handoff edges · cap {swarm.max_steps} steps</span>
          </div>
        )}
        {!swarms.length && <p className="mt-2 text-[12px] text-faint">No swarms — <Link href="/swarms" className="text-cy hover:underline">design one</Link>.</p>}

        <label className="mt-4 block"><span className="text-[12px] text-dim">Task</span>
          <textarea value={task} onChange={(e) => setTask(e.target.value)} rows={3} placeholder="What should the swarm work on?" className={inp} /></label>

        <button onClick={run} disabled={running || !swarmId || !task.trim()}
          className="mt-4 w-full rounded-lg bg-vi px-4 py-2.5 text-[13px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
          {running ? "Orchestrating agents…" : "Run swarm →"}
        </button>
        {err && <div className="mt-3 rounded-lg border border-bad/30 bg-bad/5 px-3 py-2 text-[12.5px] text-bad">{err}</div>}
      </div>

      {result && (
        <div className="mt-6">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-[12px] text-dim">
            <span className={`rounded-full px-2.5 py-1 font-medium ${result.outcome === "completed" ? "bg-ok/10 text-ok" : result.status === "failed" ? "bg-bad/10 text-bad" : "bg-warn/10 text-warn"}`}>{result.outcome || result.status}</span>
            {result.steps_used != null && <span>{result.steps_used} steps</span>}
            {result.cost_usd != null && <span>· {usd(result.cost_usd)}</span>}
            {result.latency_ms != null && <span>· {ms(result.latency_ms)}</span>}
            <Link href={`/runs/${result.id}`} className="ml-auto text-cy hover:underline">Open run →</Link>
          </div>
          {result.status === "failed"
            ? <div className="rounded-lg border border-bad/30 bg-bad/5 p-3 text-[12.5px] text-bad">{result.error}</div>
            : (
              <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
                <div><div className="mb-2 text-[12px] uppercase tracking-wider text-faint">Trace</div><Trace steps={result.trace || []} /></div>
                <div><FinalOutput text={result.final_output} /></div>
              </div>
            )}
        </div>
      )}
    </div>
  );
}

const inp = "mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50";

export default function RunPage() {
  return <Suspense fallback={<div className="py-8 text-[13px] text-dim">Loading…</div>}><RunInner /></Suspense>;
}
