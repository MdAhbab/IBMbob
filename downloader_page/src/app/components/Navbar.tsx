import { motion, AnimatePresence } from "motion/react";
import { Terminal, Menu, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="fixed top-0 left-0 right-0 z-50 flex justify-center pt-4 px-4"
      >
        <div className="w-full max-w-6xl flex items-center justify-between px-4 sm:px-5 py-3 rounded-2xl border border-white/10 bg-black/40 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
          <div className="flex items-center gap-2">
            <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/30">
              <Terminal className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <span className="text-white tracking-tight text-base sm:text-lg" style={{ fontWeight: 600 }}>
              Orchestrator
            </span>
            <span className="ml-1 px-1.5 py-0.5 text-[13px] uppercase tracking-wider rounded-md bg-white/5 border border-white/10 text-neutral-400">
              beta
            </span>
          </div>

          <div className="hidden md:flex items-center gap-7 text-base text-neutral-400">
            <a href="#problem" className="hover:text-white transition-colors">Problem</a>
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#download" className="hover:text-white transition-colors">Download</a>
            <Link to="/demo" className="hover:text-white transition-colors text-violet-400 hover:text-violet-300">Live Demo</Link>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to="/demo"
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-base text-violet-400 hover:text-violet-300 rounded-lg hover:bg-violet-500/10 transition-colors border border-violet-500/20"
            >
              <Terminal className="w-4 h-4" />
              <span>View Demo</span>
            </Link>
            <a
              href="#download"
              className="hidden sm:inline-flex px-4 py-1.5 text-base rounded-lg bg-white text-black hover:bg-neutral-200 transition-colors shadow-lg shadow-white/10"
            >
              Download
            </a>
            
            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-white/5 transition-colors text-neutral-300"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="fixed top-20 left-4 right-4 z-40 md:hidden"
          >
            <div className="rounded-2xl border border-white/10 bg-black/95 backdrop-blur-xl shadow-2xl overflow-hidden">
              <div className="flex flex-col p-4 space-y-1">
                <a
                  href="#problem"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-4 py-3 text-base text-neutral-300 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                >
                  Problem
                </a>
                <a
                  href="#features"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-4 py-3 text-base text-neutral-300 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                >
                  Features
                </a>
                <a
                  href="#download"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-4 py-3 text-base text-neutral-300 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                >
                  Download
                </a>
                <Link
                  to="/demo"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-4 py-3 text-base text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 rounded-lg transition-colors"
                >
                  Live Demo
                </Link>
                <div className="h-px bg-white/10 my-2" />
                <a
                  href="https://drive.google.com/drive/folders/1AJTGFYTia7V6eyrli1h_DwC00YGs0w5D?usp=sharing"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center justify-center px-4 py-3 text-base rounded-lg bg-white text-black hover:bg-neutral-200 transition-colors shadow-lg"
                >
                  Download Installer
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
