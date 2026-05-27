import { motion, AnimatePresence } from "motion/react";
import { Sparkles } from "lucide-react";

export function Loader({ visible }: { visible: boolean }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-[#070709] dark:bg-[#070709]"
          style={{ background: "var(--ld-bg)" }}
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(99,102,241,0.18),transparent_60%)]" />
          <div className="relative flex flex-col items-center gap-8">
            <motion.div
              initial={{ scale: 0.7, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              className="relative"
            >
              <div className="absolute -inset-6 rounded-full bg-indigo-500/25 blur-2xl" />
              <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-zinc-900 to-zinc-950 shadow-[0_0_60px_-10px_rgba(99,102,241,0.7)]">
                <Sparkles className="h-9 w-9 text-indigo-300" strokeWidth={1.5} />
                <motion.div
                  className="absolute inset-0 rounded-2xl border border-indigo-400/40"
                  animate={{ scale: [1, 1.15, 1], opacity: [0.6, 0, 0.6] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </div>
            </motion.div>
            <div className="flex flex-col items-center gap-3">
              <div className="font-mono text-[14px] uppercase tracking-[0.32em] text-zinc-400">
                Booting Orchestra
              </div>
              <div className="relative h-[2px] w-64 overflow-hidden rounded-full bg-white/[0.06]">
                <motion.div
                  className="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-indigo-400 to-transparent"
                  animate={{ x: ["-100%", "300%"] }}
                  transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
