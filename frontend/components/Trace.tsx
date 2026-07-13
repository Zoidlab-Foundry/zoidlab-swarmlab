"use client";

const HANDOFF_STYLE: Record<string, string> = {
  accepted: "text-ok", rejected_no_edge: "text-bad", rejected_unknown_agent: "text-bad",
};

export function Trace({ steps }: { steps: any[] }) {
  if (!steps?.length) return <p className="text-[12.5px] text-faint">No steps.</p>;
  return (
    <div className="space-y-2.5">
      {steps.map((s, i) => (
        <div key={i} className="rounded-2xl border border-line bg-panel2 p-3.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="grid h-5 w-5 place-items-center rounded-full bg-vi/15 text-[10px] text-vi tnum">{s.step}</span>
              <span className="text-[12.5px] font-semibold text-ink">{s.agent_name}</span>
              {s.done && <span className="rounded-full bg-ok/10 px-2 py-0.5 text-[10px] text-ok">done</span>}
            </div>
            {s.handoff_to && (
              <span className={`text-[11px] ${HANDOFF_STYLE[s.handoff_status] || "text-dim"}`}>
                → {s.handoff_to} {s.handoff_status && s.handoff_status !== "accepted" ? `(${s.handoff_status.replace(/_/g, " ")})` : ""}
              </span>
            )}
          </div>
          <p className="mt-2 whitespace-pre-wrap text-[12.5px] leading-relaxed text-dim">{s.output}</p>
        </div>
      ))}
    </div>
  );
}

export function FinalOutput({ text }: { text: string }) {
  if (!text) return null;
  return (
    <div className="rounded-2xl border border-vi/25 bg-vi/5 p-5">
      <div className="text-[12px] uppercase tracking-wider text-vi">Final output</div>
      <p className="mt-2 whitespace-pre-wrap text-[13.5px] leading-relaxed text-ink">{text}</p>
    </div>
  );
}
