"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api, usd, ms } from "../../../lib/api";
import { Trace, FinalOutput } from "../../../components/Trace";

const OUTCOME: Record<string, string> = {
  completed: "bg-ok/10 text-ok", halted_no_handoff: "bg-warn/10 text-warn",
  max_steps_reached: "bg-warn/10 text-warn", blocked: "bg-warn/10 text-warn",
};

export default function RunDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [run, setRun] = useState<any>(null);
  const [err, setErr] = useState(false);

  useEffect(() => { api.getRun(id).then(setRun).catch(() => setErr(true)); }, [id]);

  if (err) return <div className="py-10 text-[13px] text-faint">Run not found. <Link href="/runs" className="text-cy hover:underline">Back to runs</Link>.</div>;
  if (!run) return <div className="py-10 text-[13px] text-dim">Loading…</div>;

  return (
    <div className="py-8">
      <Link href="/runs" className="text-[12px] text-dim hover:text-ink">← Runs</Link>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">{run.swarm_name}</h1>
          <div className="mt-1 text-[12px] text-faint">{run.model} · {run.created_at?.slice(0, 19).replace("T", " ")}</div>
          <p className="mt-1 max-w-2xl text-[13px] text-dim"><span className="text-faint">Task:</span> {run.task_input}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[12px]">
          <span className={`rounded-full px-2.5 py-1 font-medium ${OUTCOME[run.outcome] || "bg-bad/10 text-bad"}`}>{run.outcome || run.status}</span>
          {run.steps_used != null && <span className="text-dim">{run.steps_used} steps</span>}
          {run.cost_usd != null && <span className="text-dim">· {usd(run.cost_usd)}</span>}
          {run.latency_ms != null && <span className="text-dim">· {ms(run.latency_ms)}</span>}
        </div>
      </div>

      {run.status === "failed" && run.error && (
        <div className="mt-3 rounded-lg border border-bad/30 bg-bad/5 px-3 py-2 text-[12.5px] text-bad">{run.error}</div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_1fr]">
        <div>
          <div className="mb-2 text-[12px] uppercase tracking-wider text-faint">Replay · trace</div>
          <Trace steps={run.trace || []} />
        </div>
        <div className="space-y-4">
          <FinalOutput text={run.final_output} />
          <details className="rounded-2xl border border-line bg-panel p-4">
            <summary className="cursor-pointer text-[12.5px] text-dim">Token & correlation detail</summary>
            <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] text-dim">
              <div><div className="text-faint">Prompt tokens</div><div className="tnum text-ink">{run.prompt_tokens ?? "—"}</div></div>
              <div><div className="text-faint">Completion tokens</div><div className="tnum text-ink">{run.completion_tokens ?? "—"}</div></div>
              <div><div className="text-faint">Total tokens</div><div className="tnum text-ink">{run.total_tokens ?? "—"}</div></div>
              <div><div className="text-faint">Correlation</div><div className="truncate font-mono text-[11px] text-ink" title={run.correlation_id}>{run.correlation_id || "—"}</div></div>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
