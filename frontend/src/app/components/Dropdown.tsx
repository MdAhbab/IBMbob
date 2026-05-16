import { useState, useRef, useLayoutEffect } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "motion/react";
import { Check, ChevronDown } from "lucide-react";

export function Dropdown<T extends string>({
  value,
  options,
  labels,
  onChange,
  mono = true,
  className = "",
}: {
  value: T;
  options: readonly T[];
  labels?: Record<string, string>;
  onChange: (v: T) => void;
  mono?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [rect, setRect] = useState<{ top: number; left: number; width: number } | null>(null);

  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      const r = btnRef.current?.getBoundingClientRect();
      if (r) setRect({ top: r.bottom + 4, left: r.left, width: r.width });
    };
    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    const onDown = (e: MouseEvent) => {
      if (btnRef.current && !btnRef.current.contains(e.target as Node)) {
        const menu = document.getElementById("dropdown-portal-menu");
        if (menu && menu.contains(e.target as Node)) return;
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
      document.removeEventListener("mousedown", onDown);
    };
  }, [open]);

  return (
    <div className={`relative ${className}`}>
      <button
        ref={btnRef}
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex w-full items-center justify-between gap-2 rounded-md border border-zinc-200/70 bg-white/60 px-2.5 py-1.5 text-[11px] text-zinc-700 transition hover:bg-white dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-300 dark:hover:bg-white/[0.05] ${
          mono ? "font-mono" : ""
        }`}
      >
        <span className="truncate">{labels?.[value] ?? value}</span>
        <ChevronDown className={`h-3 w-3 shrink-0 text-zinc-400 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && rect && typeof document !== "undefined" &&
        createPortal(
          <AnimatePresence>
            <motion.div
              id="dropdown-portal-menu"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              style={{ position: "fixed", top: rect.top, left: rect.left, width: rect.width }}
              className="z-[1000] max-h-[60vh] overflow-y-auto rounded-md border border-zinc-200 bg-white p-1 shadow-xl dark:border-white/10 dark:bg-zinc-950"
            >
              {options.map((o) => (
                <button
                  key={o}
                  type="button"
                  onClick={() => {
                    onChange(o);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-[11px] transition hover:bg-zinc-100 dark:hover:bg-white/5 ${
                    mono ? "font-mono" : ""
                  } ${o === value ? "text-indigo-600 dark:text-indigo-300" : "text-zinc-700 dark:text-zinc-300"}`}
                >
                  {labels?.[o] ?? o}
                  {o === value && <Check className="h-3 w-3" />}
                </button>
              ))}
            </motion.div>
          </AnimatePresence>,
          document.body
        )}
    </div>
  );
}
