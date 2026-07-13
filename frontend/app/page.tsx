"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, usd, num } from "../lib/api";

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-faint">{label}</div>
      <div className="mt-1.5 text-[24px] font-semibold tnum text-ink">{value}</div>
      {sub && <div className="mt-0.5 text-[12px] text-dim">{sub}</div>}
    </div>
  );
}

const OUTCOME: Record<string, string> = {
  completed: "bg-ok/10 text-ok", halted_no_handoff: "bg-warn/10 text-warn",
  max_steps_reached: "bg-warn/10 text-warn", blocked: "bg-warn/10 text-warn",
};

export default function Dashboard() {
  const [s, setS] = useState<any>(null);
  const [swarms, setSwarms] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);

  useEffect(() => {
    api.stats().then(setS).catch(() => {});
    api.swarms().then(setSwarms).catch(() => {});
    api.runs().then((r) => setRuns(r.slice(0, 6))).catch(() => {});
    api.meta().then(setMeta).catch(() => {});
  }, []);

  return (
    <div className="relative py-8">
      <div className="hero-glow" />
      <div className="relative flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight">
            Many agents, <span className="prism-text">one task</span>.
          </h1>
          <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-dim">
            Compose swarms of role-specialized agents connected by typed handoff edges, then run them for
            real on the live relay. The handoff contract is enforced, runtime is bounded by a step ceiling,
            and every run is fully replayable, step by step.
          </p>
        </div>
        <Link href="/run" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">
          Run a swarm →
        </Link>
      </div>

      {meta && (
        <div className={`relative mt-4 flex flex-wrap items-center gap-2 rounded-xl border px-4 py-2.5 text-[12.5px] ${meta.relay_available ? "border-ok/30 bg-ok/5 text-ok" : "border-warn/30 bg-warn/5 text-warn"}`}>
          <span className={`h-2 w-2 rounded-full ${meta.relay_available ? "bg-ok" : "bg-warn"}`} />
          {meta.relay_available
            ? <>Live relay connected — runs bill the <b>{meta.billing_mode}</b> wallet. Runtime capped at {meta.max_steps_cap} steps.</>
            : <>Relay key not configured — real runs are unavailable until <code className="text-ink">NYQUEST_API_KEY</code> is set.</>}
        </div>
      )}

      <div className="relative mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Swarms" value={num(s?.swarms ?? 0)} sub="designed" />
        <Stat label="Runs" value={num(s?.runs ?? 0)} sub="real orchestrations" />
        <Stat label="Avg steps" value={String(s?.avg_steps ?? 0)} sub="per run" />
        <Stat label="Spend" value={usd(s?.spend_usd ?? 0)} sub={`${num(s?.completed ?? 0)} completed`} />
      </div>

      <div className="relative mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold">Swarms</h2>
            <Link href="/swarms" className="text-[12px] text-cy hover:underline">All →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {swarms.slice(0, 6).map((sw) => (
              <Link key={sw.id} href={`/run?swarm=${sw.id}`} className="block rounded-lg border border-line bg-panel2 p-2.5 hover:border-vi/40">
                <div className="flex items-center justify-between">
                  <div className="text-[12.5px] font-medium text-ink">{sw.name}</div>
                  <span className="rounded-full bg-vi/10 px-2 py-0.5 text-[10.5px] text-vi">{(sw.agents || []).length} agents</span>
                </div>
                <div className="mt-0.5 line-clamp-1 text-[11px] text-faint">{sw.goal || sw.description}</div>
              </Link>
            ))}
            {!swarms.length && <p className="text-[12px] text-faint">No swarms yet. <Link href="/swarms" className="text-cy hover:underline">Design one</Link>.</p>}
          </div>
        </div>
        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold">Recent runs</h2>
            <Link href="/runs" className="text-[12px] text-cy hover:underline">All →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {runs.map((r) => (
              <Link key={r.id} href={`/runs/${r.id}`} className="block rounded-lg border border-line bg-panel2 p-2.5 hover:border-vi/40">
                <div className="flex items-center justify-between">
                  <div className="text-[12.5px] font-medium text-ink">{r.swarm_name}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${OUTCOME[r.outcome] || "bg-bad/10 text-bad"}`}>{r.outcome || r.status}</span>
                </div>
                <div className="mt-0.5 line-clamp-1 text-[11px] text-faint">{r.task_input} · {r.steps_used ?? "—"} steps</div>
              </Link>
            ))}
            {!runs.length && <p className="text-[12px] text-faint">No runs yet. <Link href="/run" className="text-cy hover:underline">Run a swarm</Link>.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
