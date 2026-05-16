import { motion } from "motion/react";
import { Terminal, Github } from "lucide-react";

export function Navbar() {
  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="fixed top-0 left-0 right-0 z-50 flex justify-center pt-4 px-4"
    >
      <div className="w-full max-w-6xl flex items-center justify-between px-5 py-3 rounded-2xl border border-white/10 bg-black/40 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
        <div className="flex items-center gap-2">
          <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/30">
            <Terminal className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <span className="text-white tracking-tight" style={{ fontWeight: 600 }}>
            Orchestrator
          </span>
          <span className="ml-1 px-1.5 py-0.5 text-[10px] uppercase tracking-wider rounded-md bg-white/5 border border-white/10 text-neutral-400">
            beta
          </span>
        </div>

        <div className="hidden md:flex items-center gap-7 text-sm text-neutral-400">
          <a href="#problem" className="hover:text-white transition-colors">Problem</a>
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#download" className="hover:text-white transition-colors">Download</a>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="#"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-sm text-neutral-300 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
          >
            <Github className="w-4 h-4" />
            <span>Star</span>
          </a>
          <a
            href="#download"
            className="px-4 py-1.5 text-sm rounded-lg bg-white text-black hover:bg-neutral-200 transition-colors shadow-lg shadow-white/10"
          >
            Download
          </a>
        </div>
      </div>
    </motion.nav>
  );
}
