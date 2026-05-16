import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronDown,
  CircleCheck,
  CircleX,
  Clock,
  Loader2,
  Menu,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { OrchestratorLogo } from "./OrchestratorLogo";
import { useStore, type Status, type SessionEntry } from "./store";

const STATUS_MAP: Record<Status, { dot: string; label: string; text: string }> = {
  online: { dot: "bg-emerald-500", label: "online", text: "text-emerald-600 dark:text-emerald-400" },
  offline: { dot: "bg-zinc-400", label: "offline", text: "text-zinc-500" },
  limited: { dot: "bg-rose-500", label: "rate-limited", text: "text-rose-600 dark:text-rose-400" },
};

const fmtWhen = (t: number) => {
  const diff = Date.now() - t;
  const m = Math.round(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};

const STATUS_ICON: Record<SessionEntry["status"], { Icon: typeof CircleCheck; cls: string }> = {
  completed: { Icon: CircleCheck, cls: "text-emerald-500" },
  failed: { Icon: CircleX, cls: "text-rose-500" },
  active: { Icon: Loader2, cls: "text-indigo-500 animate-spin" },
};

function HistoryItem({ s }: { s: SessionEntry }) {
  const { Icon, cls } = STATUS_ICON[s.status];
  return (
    <div className="group flex cursor-pointer items-start gap-2 rounded-md border border-transparent px-2 py-1.5 transition hover:border-zinc-200/70 hover:bg-white dark:hover:border-white/[0.06] dark:hover:bg-white/[0.03]">
      <Icon className={`mt-0.5 h-3 w-3 shrink-0 ${cls}`} />
      <div className="min-w-0 flex-1">
        <div className="truncate text-[11.5px] leading-snug text-zinc-800 dark:text-zinc-200">
          {s.prompt}
        </div>
        <div className="mt-0.5 flex items-center gap-1.5 font-mono text-[9px] text-zinc-500">
          <span>{fmtWhen(s.startedAt)}</span>
          <span>·</span>
          <span>{s.agents.length} agents</span>
          <span>·</span>
          <span>${s.spend.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}

export function Sidebar({
  onOpenSettings,
  mobileOpen = false,
  onCloseMobile,
}: {
  onOpenSettings?: () => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}) {
  const { providers, sessions } = useStore();
  const [collapsed, setCollapsed] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [gitOpen, setGitOpen] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1024px)");
    const apply = () => setCollapsed(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const filtered = sessions.filter((s) =>
    s.prompt.toLowerCase().includes(q.toLowerCase())
  );

  const content = (
    <>
      <div className="flex items-center gap-2.5 border-b border-zinc-200/70 px-4 py-4 dark:border-white/[0.06]">
        <OrchestratorLogo size={32} className="drop-shadow-[0_0_14px_rgba(139,92,246,0.5)]" />
        <span className="flex-1 bg-gradient-to-r from-indigo-400 via-violet-400 to-fuchsia-400 bg-clip-text text-[14px] leading-none tracking-tight text-transparent">
          Orchestrator
        </span>
        <button
          onClick={() => (onCloseMobile ? onCloseMobile() : setCollapsed(true))}
          title="Collapse sidebar"
          className="rounded-md border border-zinc-200/70 bg-white p-1.5 text-zinc-500 hover:bg-zinc-50 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-400 dark:hover:bg-white/[0.06]"
        >
          {mobileOpen ? <X className="h-3.5 w-3.5" /> : <Menu className="h-3.5 w-3.5" />}
        </button>
      </div>

      <div className="border-b border-zinc-200/70 px-3 py-3 dark:border-white/[0.06]">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-500 dark:text-zinc-400">
            <Clock className="h-2.5 w-2.5" /> History
          </span>
          <span className="font-mono text-[10px] text-zinc-500 dark:text-zinc-400">
            {sessions.length} sessions
          </span>
        </div>
        <div className="mt-2.5 flex items-center gap-1.5 rounded-md border border-zinc-200/70 bg-white px-2 dark:border-white/[0.06] dark:bg-black/30">
          <Search className="h-3 w-3 text-zinc-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search history"
            className="w-full bg-transparent py-1.5 text-[11.5px] text-zinc-800 outline-none placeholder:text-zinc-400 dark:text-zinc-200"
          />
        </div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto px-3 py-3">
        <div className="overflow-hidden rounded-lg border border-zinc-200/70 bg-white/40 dark:border-white/[0.07] dark:bg-white/[0.015]">
          <button
            onClick={() => setHistoryOpen((o) => !o)}
            className="flex w-full items-center justify-between px-3 py-2.5"
          >
            <div className="flex items-center gap-2">
              <span className="bg-gradient-to-r from-indigo-400 to-fuchsia-400 bg-clip-text font-mono text-[10.5px] uppercase tracking-[0.22em] text-transparent">
                Recent Sessions
              </span>
              <span className="rounded-md border border-zinc-200/70 bg-white px-1.5 py-0.5 font-mono text-[9px] text-zinc-600 dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-zinc-300">
                {filtered.length}
              </span>
            </div>
            <ChevronDown
              className={`h-3.5 w-3.5 text-zinc-400 transition ${historyOpen ? "rotate-0" : "-rotate-90"}`}
            />
          </button>
          <AnimatePresence initial={false}>
            {historyOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="space-y-0.5 border-t border-zinc-200/70 p-1.5 dark:border-white/[0.06]">
                  {filtered.length === 0 ? (
                    <div className="px-2 py-6 text-center">
                      <Clock className="mx-auto h-4 w-4 text-zinc-400" />
                      <p className="mt-2 text-[10.5px] text-zinc-500">
                        {sessions.length === 0
                          ? "No sessions yet — dispatch a task to start."
                          : `No matches for "${q}".`}
                      </p>
                    </div>
                  ) : (
                    filtered.map((s) => <HistoryItem key={s.id} s={s} />)
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="overflow-hidden rounded-lg border border-zinc-200/70 bg-white/40 dark:border-white/[0.07] dark:bg-white/[0.015]">
          <button
            onClick={() => setGitOpen((o) => !o)}
            className="flex w-full items-center justify-between px-3 py-2.5"
          >
            <div className="flex items-center gap-2">
              <span className="bg-gradient-to-r from-indigo-400 to-fuchsia-400 bg-clip-text font-mono text-[10.5px] uppercase tracking-[0.22em] text-transparent">
                Git Handling
              </span>
              <span className="rounded-md border border-emerald-300/40 bg-emerald-50 px-1.5 py-0.5 font-mono text-[9px] text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-300">
                clean
              </span>
            </div>
            <ChevronDown
              className={`h-3.5 w-3.5 text-zinc-400 transition ${gitOpen ? "rotate-0" : "-rotate-90"}`}
            />
          </button>
          <AnimatePresence initial={false}>
            {gitOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="space-y-2 border-t border-zinc-200/70 p-3 dark:border-white/[0.06]">
                  <GitField label="Branch" value="main" mono />
                  <GitField label="Status" value="3 files changed" valueClass="text-amber-600 dark:text-amber-300" />
                  <GitField label="User" value="Git Username" />
                  <GitField label="Repo" value="https://github.com/user/repo" mono truncate />

                  <div className="mt-2 flex items-center gap-1 rounded-md border border-zinc-200/70 bg-white px-2 dark:border-white/[0.07] dark:bg-black/40">
                    <span className="font-mono text-[11px] text-indigo-500">›</span>
                    <input
                      placeholder="git command... (commit, merge, etc.)"
                      className="flex-1 bg-transparent py-1.5 font-mono text-[10.5px] text-zinc-800 outline-none placeholder:text-zinc-400 dark:text-zinc-200"
                    />
                  </div>
                  <div className="flex items-start gap-1.5 rounded-md border border-indigo-300/40 bg-indigo-50/60 px-2 py-1.5 dark:border-indigo-400/20 dark:bg-indigo-400/[0.06]">
                    <Sparkles className="mt-0.5 h-2.5 w-2.5 shrink-0 text-indigo-500 dark:text-indigo-300" />
                    <span className="font-mono text-[9.5px] leading-snug text-indigo-700 dark:text-indigo-200">
                      Commands entered here are intercepted and handled by the Orchestrator.
                    </span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="border-t border-zinc-200/70 px-3 py-3 pb-32 dark:border-white/[0.06]">
        <div className="rounded-lg border border-emerald-300/40 bg-emerald-50 px-3 py-2 dark:border-emerald-400/15 dark:bg-emerald-400/[0.04]">
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </span>
            <span className="text-[11px] text-zinc-900 dark:text-white">Backend healthy</span>
          </div>
          <div className="mt-1 font-mono text-[9px] text-zinc-500 dark:text-zinc-400">
            ws://127.0.0.1:8787 · 12ms
          </div>
        </div>
      </div>
    </>
  );

  return (
    <>
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onCloseMobile}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm md:hidden"
            />
            <motion.aside
              initial={{ x: -320 }}
              animate={{ x: 0 }}
              exit={{ x: -320 }}
              transition={{ type: "spring", stiffness: 360, damping: 36 }}
              className="fixed inset-y-0 left-0 z-50 flex w-[300px] flex-col border-r border-zinc-200/70 bg-zinc-50 backdrop-blur dark:border-white/[0.06] dark:bg-zinc-950 md:hidden"
            >
              {content}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {collapsed ? (
        <aside className="hidden h-full w-[64px] shrink-0 flex-col items-center gap-2 border-r border-zinc-200/70 bg-zinc-50/40 py-3 backdrop-blur dark:border-white/[0.06] dark:bg-zinc-950/40 md:flex">
          <OrchestratorLogo size={36} className="drop-shadow-[0_0_14px_rgba(139,92,246,0.45)]" />
          <button
            onClick={() => setCollapsed(false)}
            title="Expand sidebar"
            className="rounded-md border border-zinc-200/70 bg-white p-1.5 text-zinc-600 hover:bg-zinc-50 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-300 dark:hover:bg-white/[0.06]"
          >
            <Menu className="h-3.5 w-3.5" />
          </button>
          <div className="mt-2 flex flex-1 flex-col items-center gap-2 overflow-y-auto">
            {providers.map((p) => {
              const s = STATUS_MAP[p.status];
              return (
                <div
                  key={p.id}
                  title={`${p.name} · ${s.label}`}
                  className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-200/70 bg-white/60 dark:border-white/[0.07] dark:bg-white/[0.02]"
                >
                  <span className={`${p.color} font-mono text-[15px] leading-none`}>{p.glyph}</span>
                  <span
                    className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full ring-2 ring-zinc-50 dark:ring-zinc-950 ${s.dot}`}
                  />
                </div>
              );
            })}
          </div>
          {onOpenSettings && (
            <button
              onClick={onOpenSettings}
              className="mb-1 rounded-md border border-zinc-200/70 bg-white p-1.5 text-zinc-500 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-400"
              title="Settings"
            >
              <Clock className="h-3.5 w-3.5" />
            </button>
          )}
        </aside>
      ) : (
        <aside className="hidden h-full w-[320px] shrink-0 flex-col border-r border-zinc-200/70 bg-zinc-50/40 backdrop-blur dark:border-white/[0.06] dark:bg-zinc-950/40 md:flex">
          {content}
        </aside>
      )}
    </>
  );
}

function GitField({
  label,
  value,
  mono,
  truncate,
  valueClass,
}: {
  label: string;
  value: string;
  mono?: boolean;
  truncate?: boolean;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-12 shrink-0 font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-500 dark:text-zinc-400">
        {label}
      </span>
      <span
        className={`flex-1 ${truncate ? "truncate" : ""} ${mono ? "font-mono" : ""} text-[11px] ${
          valueClass || "text-zinc-800 dark:text-zinc-200"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

// Re-export Dropdown for other components that import it from Sidebar (Settings, TerminalCard).
export { Dropdown } from "./Dropdown";
