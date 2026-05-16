import { motion } from "motion/react";
import {
  Maximize2,
  MoreHorizontal,
  Pause,
  RefreshCw,
  ShieldAlert,
  ChevronDown,
  Send,
} from "lucide-react";
import { useState } from "react";
import { Dropdown } from "./Sidebar";

type AuthMethod = "api_key" | "oauth" | "ssh" | "bearer" | "account";

export type CliRuntime = {
  id: string;
  name: string;
  glyph: string;
  model: string;
  models: string[];
  color: string;
  accent: string;
  authMethod: AuthMethod;
  state: "executing" | "idle" | "limited" | "permission";
  used: number;
  cap: number;
  resetsIn?: string;
  log: { kind: "cmd" | "out" | "ok" | "err" | "warn" | "sys"; text: string }[];
  pendingCmd?: string;
  task?: string;
};

const stateMap = {
  executing: {
    label: "Executing",
    cls: "border-emerald-300/40 bg-emerald-50 text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-300",
  },
  idle: {
    label: "Idle",
    cls: "border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-400/20 dark:bg-zinc-400/10 dark:text-zinc-400",
  },
  limited: {
    label: "Rate Limited",
    cls: "border-rose-300/40 bg-rose-50 text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-300",
  },
  permission: {
    label: "Awaiting Permission",
    cls: "border-amber-300/40 bg-amber-50 text-amber-700 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-300",
  },
};

const lineColor = {
  cmd: "text-zinc-900 dark:text-zinc-100",
  out: "text-zinc-500",
  ok: "text-emerald-600 dark:text-emerald-400",
  err: "text-rose-600 dark:text-rose-300",
  warn: "text-amber-600 dark:text-amber-300",
  sys: "text-indigo-600 dark:text-indigo-300",
};

export function TerminalCard({ cli, defaultMenuOpen = false }: { cli: CliRuntime; defaultMenuOpen?: boolean }) {
  const [menuOpen, setMenuOpen] = useState(defaultMenuOpen);
  const [model, setModel] = useState(cli.model);
  const pct = Math.min(100, (cli.used / cli.cap) * 100);
  const s = stateMap[cli.state];
  const overBudget = pct > 85;

  return (
    <div className="group relative flex h-full min-h-[420px] flex-col overflow-hidden rounded-xl border border-zinc-200/70 bg-white/80 transition hover:border-zinc-300 dark:border-white/[0.07] dark:bg-zinc-950/70 dark:hover:border-white/[0.14]">
      <div className="flex items-center justify-between gap-2 border-b border-zinc-200/70 px-4 py-2.5 dark:border-white/[0.05]">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${cli.color} shrink-0 font-mono text-[18px] leading-none`}>
            {cli.glyph}
          </span>
          <div className="min-w-0 leading-tight">
            <div className="truncate text-[12.5px] text-zinc-900 dark:text-white">{cli.name}</div>
            <div className="truncate font-mono text-[9.5px] text-zinc-500">{model}</div>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-500">
              Model
            </span>
            <Dropdown
              value={model}
              options={cli.models}
              onChange={setModel}
              className="w-[140px]"
              listWidth="w-[180px] right-0"
            />
          </div>
          <span
            className={`inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-[9px] uppercase tracking-wider ${s.cls}`}
          >
            {cli.state === "executing" && (
              <span className="relative flex h-1 w-1">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-1 w-1 rounded-full bg-emerald-500" />
              </span>
            )}
            {s.label}
          </span>
          <div className="relative">
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className={`rounded p-1 ${menuOpen ? "bg-zinc-100 text-zinc-700 dark:bg-white/10 dark:text-zinc-200" : "text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5"}`}
            >
              <MoreHorizontal className="h-3 w-3" />
            </button>
            {menuOpen && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute right-0 top-full z-30 mt-1 w-[260px] overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-xl dark:border-white/10 dark:bg-zinc-950"
              >
                <button className="flex w-full items-center gap-2 px-3 py-2 text-left text-[11.5px] text-zinc-700 hover:bg-zinc-50 dark:text-zinc-200 dark:hover:bg-white/5">
                  <Pause className="h-3 w-3 text-zinc-500" />
                  <span>Pause</span>
                  <span className="ml-auto font-mono text-[9px] text-zinc-400">⌘P</span>
                </button>
                <button className="flex w-full items-center gap-2 border-t border-zinc-200/70 px-3 py-2 text-left text-[11.5px] text-zinc-700 hover:bg-zinc-50 dark:border-white/[0.06] dark:text-zinc-200 dark:hover:bg-white/5">
                  <RefreshCw className="h-3 w-3 text-zinc-500" />
                  <span>Reload</span>
                  <span className="ml-auto font-mono text-[9px] text-zinc-400">⌘R</span>
                </button>
                <button className="flex w-full items-start gap-2 border-t border-zinc-200/70 px-3 py-2 text-left text-[11.5px] text-zinc-700 hover:bg-zinc-50 dark:border-white/[0.06] dark:text-zinc-200 dark:hover:bg-white/5">
                  <Maximize2 className="mt-0.5 h-3 w-3 shrink-0 text-zinc-500" />
                  <div className="min-w-0">
                    <div>Full-screen</div>
                    <div className="mt-0.5 font-mono text-[9.5px] leading-snug text-zinc-500">
                      Pops out this CLI terminal as a separate, native PC window.
                    </div>
                  </div>
                </button>
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {cli.task && (
        <div className="border-b border-zinc-200/70 bg-indigo-50/30 px-4 py-1.5 dark:border-white/[0.05] dark:bg-indigo-400/[0.04]">
          <div className="flex items-center gap-1.5 font-mono text-[10px]">
            <span className="text-zinc-500">assigned:</span>
            <span className="truncate text-indigo-700 dark:text-indigo-300">{cli.task}</span>
          </div>
        </div>
      )}

      <div className="space-y-1.5 px-4 pt-3">
        <div className="flex items-center justify-between font-mono text-[10px]">
          <span className="text-zinc-500">Daily quota</span>
          <span className={overBudget ? "text-rose-600 dark:text-rose-300" : "text-zinc-700 dark:text-zinc-200"}>
            ${cli.used.toFixed(2)}
            <span className="text-zinc-400 dark:text-zinc-600"> / ${cli.cap.toFixed(2)}</span>
          </span>
        </div>
        <div className="relative h-1.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-white/[0.05]">
          <motion.div
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.8 }}
            className="h-full"
            style={{
              background: overBudget ? "linear-gradient(to right,#fb7185,#f43f5e)" : cli.accent,
            }}
          />
          <div className="absolute top-0 h-full w-px bg-rose-400/40" style={{ left: "85%" }} />
        </div>
        <div className="flex items-center justify-between font-mono text-[9px] text-zinc-500">
          <span>tokens 28.4k / 100k</span>
          {cli.resetsIn ? (
            <span className="text-rose-600 dark:text-rose-300">resets in {cli.resetsIn}</span>
          ) : (
            <span>req/min 14 · p95 820ms</span>
          )}
        </div>
      </div>

      <div className="m-3 mt-3 flex flex-1 flex-col overflow-hidden rounded-lg border border-zinc-200/70 bg-zinc-50/60 dark:border-white/[0.05] dark:bg-black/50">
        <div className="flex items-center justify-between border-b border-zinc-200/70 px-3 py-1 dark:border-white/[0.04]">
          <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-500">
            {cli.id}.session
          </span>
        </div>
        <div className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2 font-mono text-[11px] leading-relaxed">
          {cli.log.map((l, i) => (
            <div key={i} className={lineColor[l.kind]}>
              {l.kind === "cmd" && <span className="text-zinc-400">$ </span>}
              {l.kind === "out" && <span className="text-zinc-400">→ </span>}
              {l.kind === "ok" && <span>✓ </span>}
              {l.kind === "err" && <span>✗ </span>}
              {l.kind === "warn" && <span>⚠ </span>}
              {l.text}
            </div>
          ))}
          {cli.state === "executing" && (
            <span className="inline-block h-3 w-1.5 animate-pulse bg-zinc-500 align-middle" />
          )}
        </div>
        <div className="flex items-center gap-1 border-t border-zinc-200/70 bg-white px-2 py-1 dark:border-white/[0.04] dark:bg-black/30">
          <span className="font-mono text-[11px] text-zinc-400">$</span>
          <input
            placeholder={`send command to ${cli.id}…`}
            className="flex-1 bg-transparent font-mono text-[11px] text-zinc-800 outline-none placeholder:text-zinc-400 dark:text-zinc-200"
          />
          <button className="rounded p-0.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200">
            <Send className="h-3 w-3" />
          </button>
        </div>
      </div>

      {cli.state === "permission" && cli.pendingCmd && (
        <div className="border-t border-amber-300/40 bg-amber-50/70 px-4 py-2.5 dark:border-amber-400/15 dark:bg-amber-400/[0.04]">
          <div className="flex items-center gap-1.5 text-[10px] text-amber-700 dark:text-amber-200">
            <ShieldAlert className="h-3 w-3" />
            Approval required for destructive command
          </div>
          <pre className="mt-1.5 rounded border border-amber-300/40 bg-white px-2 py-1 font-mono text-[10px] text-amber-800 dark:border-amber-400/15 dark:bg-black/40 dark:text-amber-100">
            {cli.pendingCmd}
          </pre>
          <div className="mt-2 flex items-center justify-end gap-1.5">
            <button className="rounded-md border border-zinc-200/70 bg-white px-2 py-1 text-[10px] text-zinc-700 hover:bg-zinc-50 dark:border-white/10 dark:bg-white/[0.04] dark:text-zinc-300 dark:hover:bg-white/[0.08]">
              Deny
            </button>
            <button className="rounded-md bg-emerald-500 px-2 py-1 text-[10px] text-white hover:bg-emerald-600">
              Approve once
            </button>
            <button className="rounded-md border border-emerald-400/40 bg-emerald-100 px-2 py-1 text-[10px] text-emerald-700 hover:bg-emerald-200 dark:border-emerald-400/30 dark:bg-emerald-400/10 dark:text-emerald-300 dark:hover:bg-emerald-400/20">
              Always allow
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
