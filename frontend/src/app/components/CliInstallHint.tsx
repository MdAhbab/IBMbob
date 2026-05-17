import { Terminal } from "lucide-react";
import { cliInstallForProvider } from "../lib/cliInstall";

export function CliInstallHint({ providerId }: { providerId: string }) {
  const info = cliInstallForProvider(providerId);
  if (!info) return null;

  return (
    <div className="mt-2 rounded-lg border border-amber-300/50 bg-amber-50/80 px-3 py-2.5 text-[11px] leading-relaxed text-amber-900 dark:border-amber-400/25 dark:bg-amber-950/30 dark:text-amber-100">
      <div className="mb-1 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-amber-700 dark:text-amber-300">
        <Terminal className="h-3 w-3" />
        Install this CLI (if not on PATH)
      </div>
      <div className="font-mono text-[10.5px] text-zinc-800 dark:text-zinc-200">{info.install}</div>
      <div className="mt-1 font-mono text-[9.5px] text-zinc-600 dark:text-zinc-400">
        Verify: {info.verify}
      </div>
      {info.notes && (
        <p className="mt-1.5 text-[10.5px] text-amber-800/90 dark:text-amber-200/80">{info.notes}</p>
      )}
    </div>
  );
}
