"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, usd, ms } from "../../lib/api";

const OUTCOME: Record<string, string> = {
  completed: "bg-ok/10 text-ok", halted_no_handoff: "bg-warn/10 text-warn",
  max_steps_reached: "bg-warn/10 text-warn", blocked: "bg-warn/10 text-warn",
};

export default function RunsPage() {
  const [runs, setRuns] = useState<any[]>([]);
  useEffect(() => { api.runs().then(setRuns).catch(() => {}); }, []);

  return (
    <div className="py-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[22px] font-semibold">Runs</h1>
          <p className="mt-1 text-[13px] text-dim">Every swarm run, with its outcome, step count, and cost. Open one to replay the full trace.</p>
        </div>
        <Link href="/run" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">New run →</Link>
      </div>

      <div className="mt-5 overflow-x-auto rounded-2xl border border-line bg-panel">
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 font-medium">Swarm</th>
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="px-4 py-3 font-medium">Outcome</th>
              <th className="px-4 py-3 font-medium">Steps</th>
              <th className="px-4 py-3 font-medium">Cost</th>
              <th className="px-4 py-3 font-medium">Latency</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="border-t border-line/60 hover:bg-panel2/50">
                <td className="px-4 py-3"><Link href={`/runs/${r.id}`} className="font-medium text-ink hover:text-cy">{r.swarm_name}</Link></td>
                <td className="px-4 py-3 max-w-[240px] truncate text-dim" title={r.task_input}>{r.task_input}</td>
                <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-[10.5px] ${OUTCOME[r.outcome] || "bg-bad/10 text-bad"}`}>{r.outcome || r.status}</span></td>
                <td className="px-4 py-3 tnum text-dim">{r.steps_used ?? "—"}</td>
                <td className="px-4 py-3 tnum text-dim">{usd(r.cost_usd || 0)}</td>
                <td className="px-4 py-3 tnum text-dim">{ms(r.latency_ms)}</td>
              </tr>
            ))}
            {!runs.length && <tr><td colSpan={6} className="px-4 py-10 text-center text-[13px] text-faint">No runs yet. <Link href="/run" className="text-cy hover:underline">Run a swarm</Link>.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
