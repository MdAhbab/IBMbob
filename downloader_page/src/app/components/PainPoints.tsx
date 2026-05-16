import { motion } from "motion/react";
import { AlertTriangle, Clock, Repeat, Zap, RefreshCw, Brain } from "lucide-react";

export function PainPoints() {
  return (
    <section id="problem" className="relative py-32 px-4">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/3 left-0 w-[500px] h-[500px] rounded-full bg-red-500/10 blur-[120px]" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-orange-500/10 blur-[120px]" />
      </div>

      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-3xl mx-auto mb-20"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20 text-xs text-red-300 mb-6">
            <AlertTriangle className="w-3 h-3" />
            <span className="uppercase tracking-wider">The Problem</span>
          </div>
          <h2
            className="text-white tracking-[-0.03em] leading-tight"
            style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)", fontWeight: 600 }}
          >
            Your multi‑CLI workflow is{" "}
            <span className="bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent italic">
              bleeding hours.
            </span>
          </h2>
          <p className="mt-5 text-neutral-400 text-lg">
            Every developer using more than one AI CLI hits the same two walls — every single day.
          </p>
        </motion.div>

        {/* Two-up cards */}
        <div className="grid md:grid-cols-2 gap-5">
          {/* Card 1: Context Re-feeding Hell */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.7 }}
            className="group relative rounded-3xl border border-white/10 bg-gradient-to-br from-neutral-900/80 to-black p-8 overflow-hidden"
          >
            <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-orange-500/20 blur-3xl group-hover:bg-orange-500/30 transition-colors" />

            <div className="relative">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500/20 to-red-500/20 border border-orange-500/30 flex items-center justify-center mb-6">
                <Repeat className="w-5 h-5 text-orange-300" />
              </div>

              <h3 className="text-white tracking-tight" style={{ fontSize: "1.75rem", fontWeight: 600 }}>
                Context Re‑feeding Hell
              </h3>
              <p className="mt-3 text-neutral-400 leading-relaxed">
                Every switch between CLIs means re‑explaining your entire project, conventions, and constraints.
                Again. And again. And again.
              </p>

              {/* Mock terminal */}
              <div className="mt-6 rounded-xl border border-white/5 bg-black/60 p-4 font-mono text-xs space-y-1.5">
                <div className="text-neutral-500">$ claude-code "implement auth flow"</div>
                <div className="text-orange-300">⚠ rate limit reached. Switching...</div>
                <div className="text-neutral-500">$ gemini "implement auth flow"</div>
                <div className="text-red-300">✗ no context — explain the project first</div>
                <div className="text-neutral-600 italic">// 10+ min copy/paste begins</div>
                <div className="text-neutral-500">$ codex "wait, what conventions?"</div>
                <div className="text-red-300">✗ no context found</div>
              </div>

              <div className="mt-6 flex flex-wrap items-center gap-4 text-sm">
                <div className="flex items-center gap-2 text-neutral-400">
                  <Clock className="w-4 h-4 text-orange-400" />
                  <span><span className="text-white">10+ min</span> wasted per switch</span>
                </div>
                <div className="flex items-center gap-2 text-neutral-400">
                  <Brain className="w-4 h-4 text-orange-400" />
                  <span><span className="text-white">15‑20 min</span> to regain flow</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Card 2: Rate Limit Nightmares */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="group relative rounded-3xl border border-white/10 bg-gradient-to-br from-neutral-900/80 to-black p-8 overflow-hidden"
          >
            <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-red-500/20 blur-3xl group-hover:bg-red-500/30 transition-colors" />

            <div className="relative">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500/20 to-pink-500/20 border border-red-500/30 flex items-center justify-center mb-6">
                <Zap className="w-5 h-5 text-red-300" />
              </div>

              <h3 className="text-white tracking-tight" style={{ fontSize: "1.75rem", fontWeight: 600 }}>
                Rate Limit Nightmares
              </h3>
              <p className="mt-3 text-neutral-400 leading-relaxed">
                Limits hit mid‑task with zero warning. Some CLIs sit idle while others throw 429s.
                Quota is silently wasted at scale.
              </p>

              {/* Mock quota bars */}
              <div className="mt-6 rounded-xl border border-white/5 bg-black/60 p-4 space-y-3">
                {[
                  { name: "claude-code", pct: 100, color: "bg-red-500", label: "BLOCKED" },
                  { name: "gemini", pct: 12, color: "bg-emerald-500", label: "idle" },
                  { name: "codex", pct: 98, color: "bg-red-500", label: "1 req left" },
                  { name: "deepseek", pct: 8, color: "bg-emerald-500", label: "idle" },
                ].map((row) => (
                  <div key={row.name} className="flex items-center gap-3 text-xs font-mono">
                    <span className="text-neutral-400 w-24 truncate">{row.name}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className={`h-full ${row.color} rounded-full transition-all`}
                        style={{ width: `${row.pct}%` }}
                      />
                    </div>
                    <span
                      className={`w-20 text-right ${
                        row.pct > 90 ? "text-red-400" : "text-emerald-400"
                      }`}
                    >
                      {row.label}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-wrap items-center gap-4 text-sm">
                <div className="flex items-center gap-2 text-neutral-400">
                  <RefreshCw className="w-4 h-4 text-red-400" />
                  <span><span className="text-white">~30%</span> quota wasted</span>
                </div>
                <div className="flex items-center gap-2 text-neutral-400">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span><span className="text-white">Zero</span> visibility into limits</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Stat strip */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-px rounded-2xl overflow-hidden border border-white/10 bg-white/5"
        >
          {[
            { value: "10+ min", label: "lost per CLI switch" },
            { value: "30%", label: "quota wasted on idle CLIs" },
            { value: "8+", label: "CLIs to track manually" },
            { value: "0", label: "visibility into limits" },
          ].map((s) => (
            <div key={s.label} className="bg-black p-6 text-center">
              <div
                className="text-white tracking-tight"
                style={{ fontSize: "1.75rem", fontWeight: 600 }}
              >
                {s.value}
              </div>
              <div className="mt-1 text-sm text-neutral-500">{s.label}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
