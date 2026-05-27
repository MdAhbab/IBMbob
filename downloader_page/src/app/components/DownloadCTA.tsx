import { motion } from "motion/react";
import { Download, Apple, Terminal, Github } from "lucide-react";

export function DownloadCTA() {
  const downloadLink = "https://drive.google.com/drive/folders/1AJTGFYTia7V6eyrli1h_DwC00YGs0w5D?usp=sharing";

  const platforms = [
    { name: "Windows", icon: Download, sub: "Windows 10 · 11" },
    { name: "macOS", icon: Apple, sub: "Apple Silicon · Intel" },
    { name: "Linux", icon: Terminal, sub: ".deb · .rpm · AppImage" },
  ];

  return (
    <section id="download" className="relative py-32 px-4">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[600px] rounded-full bg-violet-600/20 blur-[140px]" />
      </div>

      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.7 }}
          className="relative rounded-[2rem] overflow-hidden border border-white/10 bg-gradient-to-br from-neutral-900 via-black to-neutral-900 p-10 md:p-16"
        >
          {/* Glow border */}
          <div className="absolute -inset-px rounded-[2rem] bg-gradient-to-r from-violet-500/40 via-fuchsia-500/40 to-blue-500/40 opacity-50 blur-md -z-10" />

          {/* Grid pattern */}
          <div
            className="absolute inset-0 opacity-[0.08]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.4) 1px, transparent 1px)",
              backgroundSize: "40px 40px",
              maskImage:
                "radial-gradient(ellipse at center, black 0%, transparent 60%)",
            }}
          />

          <div className="relative text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm text-neutral-300 mb-6">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75 animate-ping" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-violet-400" />
              </span>
              <span>Free during beta</span>
            </div>

            <h2
              className="text-white tracking-[-0.03em] leading-tight"
              style={{ fontSize: "clamp(2rem, 5vw, 3.75rem)", fontWeight: 600 }}
            >
              Stop juggling.{" "}
              <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-rose-400 bg-clip-text text-transparent">
                Start orchestrating.
              </span>
            </h2>
            <p className="mt-5 text-neutral-400 text-xl mb-8">
              Install in 30 seconds. Auto‑detects every AI CLI on your machine.
            </p>

            {/* Platform downloads */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-3">
              {platforms.map((p, i) => (
                <motion.a
                  key={p.name}
                  href={downloadLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: 0.1 + i * 0.08 }}
                  className="group relative flex items-center gap-3 px-4 py-3.5 rounded-xl border border-white/10 backdrop-blur-md transition-all text-left bg-white/[0.03] hover:bg-white/[0.08] hover:border-white/20 cursor-pointer"
                >
                <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center transition-colors group-hover:bg-white/10">
                  <p.icon className="w-4 h-4 text-neutral-200" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-white text-base" style={{ fontWeight: 500 }}>
                    Download for {p.name}
                  </div>
                  <div className="text-sm text-neutral-500 truncate">
                    {p.sub}
                  </div>
                </div>
                <Download className="w-4 h-4 text-neutral-500 group-hover:text-white transition-colors" />
                </motion.a>
              ))}
            </div>

            {/* Footer note */}
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4 text-base text-neutral-500">
              <a
                href="https://github.com/MdAhbab/IBMbob"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 hover:text-white transition-colors"
              >
                <Github className="w-4 h-4" />
                <span>View source on GitHub</span>
              </a>
              <span className="hidden sm:inline text-neutral-700">·</span>
              <span>MIT licensed · v1.0.0‑beta.3</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-white/5 px-4 py-10 mt-10">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-base text-neutral-500">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center">
            <Terminal className="w-3 h-3 text-white" strokeWidth={2.5} />
          </div>
          <span>© 2026 AI CLI Orchestrator. Built by devs, for devs.</span>
        </div>
        <div className="flex items-center gap-6">
          <a href="#" className="hover:text-white transition-colors">Docs</a>
          <a href="https://github.com/MdAhbab/IBMbob" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">GitHub</a>
          <a href="#" className="hover:text-white transition-colors">Discord</a>
          <a href="#" className="hover:text-white transition-colors">Privacy</a>
        </div>
      </div>
    </footer>
  );
}
