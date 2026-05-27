import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronDown,
  CircleCheck,
  CircleX,
  Clock,
  Coins,
  FileText,
  Loader2,
  Search,
  Trash2,
} from "lucide-react";
import { useStore, type SessionEntry } from "./store";

const fmtDate = (t: number) => {
  const d = new Date(t);
  const today = new Date();
  const sameDay = d.toDateString() === today.toDateString();
  return sameDay
    ? d.toTimeString().slice(0, 5)
    : d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
        " · " +
        d.toTimeString().slice(0, 5);
};

const fmtDuration = (s: SessionEntry) => {
  if (!s.endedAt) return "active";
  const ms = s.endedAt - s.startedAt;
  const m = Math.round(ms / 60000);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
};

const StatusBadge = ({ s }: { s: SessionEntry["status"] }) => {
  const map = {
    completed: {
      cls: "border-emerald-300/40 bg-emerald-50 text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-300",
      Icon: CircleCheck,
    },
    failed: {
      cls: "border-rose-300/40 bg-rose-50 text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-300",
      Icon: CircleX,
    },
    active: {
      cls: "border-indigo-300/40 bg-indigo-50 text-indigo-700 dark:border-indigo-400/20 dark:bg-indigo-400/10 dark:text-indigo-300",
      Icon: Loader2,
    },
  }[s];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 font-mono text-[12px] uppercase tracking-wider ${map.cls}`}
    >
      <map.Icon className={`h-2.5 w-2.5 ${s === "active" ? "animate-spin" : ""}`} />
      {s}
    </span>
  );
};

export function SessionHistory() {
  const { sessions, clearSessions } = useStore();
  const [q, setQ] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);

  const filtered = sessions.filter(
    (s) =>
      s.prompt.toLowerCase().includes(q.toLowerCase()) ||
      s.agents.some((a) => a.toLowerCase().includes(q.toLowerCase()))
  );

  if (sessions.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-zinc-300/70 bg-zinc-50/40 px-6 py-12 text-center dark:border-white/10 dark:bg-white/[0.02]">
        <Clock className="mx-auto h-5 w-5 text-zinc-400" />
        <div className="mt-3 text-[16px] text-zinc-700 dark:text-zinc-200">No sessions yet</div>
        <p className="mt-1 text-[14.5px] text-zinc-500">
          When you dispatch tasks to the orchestrator, completed runs land here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-1 items-center gap-1.5 rounded-md border border-zinc-200/70 bg-white/60 px-2 dark:border-white/[0.07] dark:bg-white/[0.02]">
          <Search className="h-3 w-3 text-zinc-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search prompts, agents…"
            className="w-full bg-transparent py-1.5 text-[15px] text-zinc-800 outline-none placeholder:text-zinc-400 dark:text-zinc-200"
          />
        </div>
        <button
          onClick={() => {
            if (confirm("Clear all session history?")) clearSessions();
          }}
          className="flex items-center gap-1 rounded-md border border-zinc-200/70 bg-white px-2 py-1.5 text-[14px] text-zinc-600 hover:bg-zinc-50 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-300 dark:hover:bg-white/[0.06]"
        >
          <Trash2 className="h-3 w-3" /> Clear
        </button>
      </div>

      <div className="space-y-1.5">
        {filtered.map((s) => {
          const open = openId === s.id;
          return (
            <div
              key={s.id}
              className="overflow-hidden rounded-xl border border-zinc-200/70 bg-white/60 dark:border-white/[0.06] dark:bg-zinc-950/40"
            >
              <button
                onClick={() => setOpenId(open ? null : s.id)}
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
              >
                <StatusBadge s={s.status} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[15.5px] text-zinc-900 dark:text-zinc-100">
                    {s.prompt}
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-2 font-mono text-[13px] text-zinc-500">
                    <span>{fmtDate(s.startedAt)}</span>
                    <span>·</span>
                    <span>{fmtDuration(s)}</span>
                    <span>·</span>
                    <span className="inline-flex items-center gap-0.5">
                      <Coins className="h-2.5 w-2.5" />${s.spend.toFixed(2)}
                    </span>
                    <span>·</span>
                    <span>{(s.tokens / 1000).toFixed(1)}k tok</span>
                  </div>
                </div>
                <div className="hidden items-center gap-1 sm:flex">
                  {s.agents.slice(0, 4).map((a) => (
                    <span
                      key={a}
                      className="rounded-md border border-zinc-200/70 bg-zinc-50 px-1.5 py-0.5 font-mono text-[12px] text-zinc-600 dark:border-white/[0.07] dark:bg-white/[0.04] dark:text-zinc-300"
                    >
                      {a}
                    </span>
                  ))}
                </div>
                <ChevronDown
                  className={`h-3.5 w-3.5 shrink-0 text-zinc-400 transition ${open ? "rotate-180" : ""}`}
                />
              </button>
              <AnimatePresence initial={false}>
                {open && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="space-y-3 border-t border-zinc-200/70 px-4 py-3 text-[15px] text-zinc-700 dark:border-white/[0.05] dark:text-zinc-300">
                      <div>
                        <div className="mb-1 font-mono text-[12px] uppercase tracking-[0.2em] text-zinc-500">
                          Summary
                        </div>
                        <p className="leading-relaxed">{s.summary}</p>
                      </div>
                      {s.artifacts.length > 0 && (
                        <div>
                          <div className="mb-1 font-mono text-[12px] uppercase tracking-[0.2em] text-zinc-500">
                            Artifacts
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {s.artifacts.map((a) => (
                              <span
                                key={a}
                                className="inline-flex items-center gap-1 rounded-md border border-indigo-200/70 bg-indigo-50 px-1.5 py-0.5 font-mono text-[13px] text-indigo-700 dark:border-indigo-400/20 dark:bg-indigo-400/10 dark:text-indigo-300"
                              >
                                <FileText className="h-2.5 w-2.5" />
                                {a}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div className="rounded-xl border border-dashed border-zinc-300/70 bg-zinc-50/40 px-6 py-8 text-center text-[15px] text-zinc-500 dark:border-white/10 dark:bg-white/[0.02]">
            No sessions match "{q}".
          </div>
        )}
      </div>
    </div>
  );
}
