async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, credentials: "include", headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try { detail = (await r.json()).detail || detail; } catch {}
    const e = new Error(detail) as Error & { status?: number }; e.status = r.status; throw e;
  }
  return r.json();
}

export const api = {
  entitlements: () => req<any>("/api/auth/entitlements"),
  stats: () => req<any>("/api/stats"),
  meta: () => req<{ relay_available: boolean; billing_mode: string; models: string[]; default_model: string; max_steps_cap: number }>("/api/meta"),

  swarms: () => req<{ swarms: any[] }>("/api/swarms").then((d) => d.swarms),
  swarm: (id: string) => req<any>(`/api/swarms/${id}`),
  createSwarm: (b: any) => req<any>("/api/swarms", { method: "POST", body: JSON.stringify(b) }).then((d) => d.swarm),
  updateSwarm: (id: string, b: any) => req<any>(`/api/swarms/${id}`, { method: "PUT", body: JSON.stringify(b) }).then((d) => d.swarm),
  deleteSwarm: (id: string) => req<any>(`/api/swarms/${id}`, { method: "DELETE" }),

  run: (b: { swarm_id: string; task_input: string; model?: string; max_steps?: number }) =>
    req<any>("/api/run", { method: "POST", body: JSON.stringify(b) }),
  runs: () => req<{ runs: any[] }>("/api/runs").then((d) => d.runs),
  getRun: (id: string) => req<any>(`/api/runs/${id}`),
  job: (id: string) => req<any>(`/api/jobs/${id}`),

  exportUrl: (id: string) => `/api/swarms/${id}/export`,
};

const TERMINAL = ["succeeded", "partial", "failed", "blocked", "timed_out", "cancelled", "interrupted"];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Submit a durable job and poll it to completion, then return the finished run.
export async function runToCompletion(
  submit: () => Promise<any>,
  getRun: (id: string) => Promise<any>,
  onStatus?: (s: string) => void,
): Promise<any> {
  const sub = await submit();
  if (!sub?.job_id) return sub;
  let job = await api.job(sub.job_id);
  onStatus?.(job.status);
  let tries = 0;
  while (!TERMINAL.includes(job.status) && tries < 300) {
    await sleep(900);
    job = await api.job(sub.job_id);
    onStatus?.(job.status);
    tries++;
  }
  const run = await getRun(sub.run_id);
  return { ...run, _job: job };
}

export const usd = (n: number) => "$" + (n ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 });
export const ms = (n: number | null | undefined) => (n == null ? "—" : n >= 1000 ? (n / 1000).toFixed(2) + "s" : Math.round(n) + "ms");
export const num = (n: number) => (n ?? 0).toLocaleString();
