import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { useMemo } from "react";

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

export function AnalyticsStrip({ totalUsed, totalCap, activeAgents }: {
  totalUsed: number;
  totalCap: number;
  activeAgents: number;
}) {
  const a = useMemo(() => spark(1), []);
  const b = useMemo(() => spark(3), []);
  const c = useMemo(() => cpuSpark(5), []);
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat label="Spend today" value={`$${totalUsed.toFixed(2)}`} sub={`of $${totalCap} cap`} data={a} color="#6366f1" />
      <Stat label="Active agents" value={`${activeAgents}`} sub="parallel sessions" data={b} color="#10b981" />
      <Stat label="CPU Usage" value="45.2% CPU" sub="P95 core load" data={c} color="#a855f7" labelColor="text-violet-500 dark:text-violet-300" />
      <Stat label="Tasks shipped" value="38" sub="last 24h" data={a.slice().reverse()} color="#a855f7" />
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
}: {
  label: string;
  value: string;
  sub: string;
  data: { x: number; y: number }[];
  color: string;
  labelColor?: string;
}) {
  const id = `g-${label.replace(/\s/g, "")}`;
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200/70 bg-white/60 px-4 py-3 backdrop-blur dark:border-white/[0.07] dark:bg-zinc-950/40">
      <div className="flex items-start justify-between">
        <div>
          <div className={`font-mono text-[9.5px] uppercase tracking-[0.22em] ${labelColor || "text-zinc-500"}`}>
            {label}
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
