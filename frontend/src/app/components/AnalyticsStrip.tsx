import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../lib/api";

function spark(seed: number) {
  return Array.from({ length: 20 }).map((_, i) => ({
    x: i,
    y: 30 + Math.sin(i / 2 + seed) * 12 + Math.random() * 6,
  }));
}

function cpuSpark(seed: number) {
  let v = 40 + (seed % 10);
  return Array.from({ length: 24 }).map((_, i) => {
    const drift = Math.sin(i / 1.4 + seed) * 14;
    const spike = i % 5 === 0 ? Math.random() * 22 : Math.random() * 6 - 3;
    v = Math.max(8, Math.min(92, v * 0.55 + (45 + drift + spike) * 0.45));
    return { x: i, y: v };
  });
}

export function AnalyticsStrip({
  totalUsed,
  totalCap,
  activeAgents,
}: {
  totalUsed: number;
  totalCap: number;
  activeAgents: number;
}) {
  const [tasksShipped, setTasksShipped] = useState<number | null>(null);
  const [routesDemo, setRoutesDemo] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await apiFetch("/analytics/routes?limit=100", { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        const total = Number(data.total ?? data.routes?.length ?? 0);
        setTasksShipped(total);
        setRoutesDemo(!Array.isArray(data.routes) || data.routes.length === 0);
      } catch {
        if (!cancelled) {
          setTasksShipped(null);
          setRoutesDemo(true);
        }
      }
    };
    void load();
    const id = window.setInterval(load, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const a = useMemo(() => spark(1), []);
  const b = useMemo(() => spark(3), []);
  const c = useMemo(() => cpuSpark(activeAgents), [activeAgents]);
  const cpuPct = Math.min(99, Math.round((activeAgents / Math.max(1, totalCap || 1)) * 100));

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat label="Spend today" value={`$${totalUsed.toFixed(2)}`} sub={`of $${totalCap} cap`} data={a} color="#6366f1" />
      <Stat label="Active agents" value={`${activeAgents}`} sub="parallel sessions" data={b} color="#10b981" />
      <Stat
        label="Agent load"
        value={`${cpuPct}%`}
        sub="estimated from active / cap"
        data={c}
        color="#a855f7"
      />
      <Stat
        label="Routes logged"
        value={tasksShipped == null ? "—" : String(tasksShipped)}
        sub={routesDemo ? "demo until routing history exists" : "from /api/analytics/routes"}
        data={a.slice().reverse()}
        color="#a855f7"
        demo={routesDemo}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  data,
  color,
  labelColor,
  demo = false,
}: {
  label: string;
  value: string;
  sub: string;
  data: { x: number; y: number }[];
  color: string;
  labelColor?: string;
  demo?: boolean;
}) {
  const id = `g-${label.replace(/\s/g, "")}`;
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200/70 bg-white/60 px-4 py-3 backdrop-blur dark:border-white/[0.07] dark:bg-zinc-950/40">
      <div className="flex items-start justify-between">
        <div>
          <div className={`font-mono text-[9.5px] uppercase tracking-[0.22em] ${labelColor || "text-zinc-500"}`}>
            {label}
            {demo && (
              <span className="ml-1.5 rounded border border-zinc-200/70 px-1 py-0.5 text-[8px] normal-case tracking-normal text-zinc-500 dark:border-white/10">
                demo
              </span>
            )}
          </div>
          <div className="mt-1.5 text-[20px] tracking-tight text-zinc-900 dark:text-white">
            {value}
          </div>
          <div className="font-mono text-[10px] text-zinc-500">{sub}</div>
        </div>
        <div className="h-10 w-20">
          <ResponsiveContainer>
            <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.5} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="y"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#${id})`}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
