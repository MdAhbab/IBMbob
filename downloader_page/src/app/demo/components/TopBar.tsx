import {
  Bell,
  Command,
  Cpu,
  FolderGit2,
  Menu,
  Moon,
  Search,
  Settings as SettingsIcon,
  Sun,
} from "lucide-react";
import { useTheme } from "./theme";
import { useStore } from "./store";

type View = "chat" | "processes" | "settings";

export function TopBar({
  view,
  onView,
  activeAgents,
  onOpenPalette,
  onToggleSidebar,
}: {
  view: View;
  onView: (v: View) => void;
  activeAgents: number;
  onOpenPalette: () => void;
  onToggleSidebar?: () => void;
}) {
  const { theme, toggle } = useTheme();
  const { workspace } = useStore();
  return (
    <div className="flex h-14 items-center justify-between gap-2 border-b border-zinc-200/70 bg-white/60 px-3 backdrop-blur dark:border-white/[0.06] dark:bg-zinc-950/40 sm:px-5">
      <div className="flex min-w-0 items-center gap-2">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="rounded-md border border-zinc-200/70 bg-white p-1.5 text-zinc-600 hover:bg-zinc-50 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-300 dark:hover:bg-white/[0.06] md:hidden"
            title="Toggle sidebar"
          >
            <Menu className="h-3.5 w-3.5" />
          </button>
        )}
        <div className="hidden min-w-0 items-center gap-1.5 text-[15.5px] text-zinc-600 dark:text-zinc-400 sm:flex">
          <FolderGit2 className="h-3.5 w-3.5 text-zinc-400" />
          <span className="truncate text-zinc-800 dark:text-zinc-200">
            {workspace?.name || "no workspace"}
          </span>
          <span className="text-zinc-300 dark:text-zinc-700">/</span>
          <span>main</span>
          <span className="ml-1 rounded-md border border-emerald-300/40 bg-emerald-50 px-1.5 py-0.5 font-mono text-[12px] text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/[0.06] dark:text-emerald-300">
            clean
          </span>
        </div>
      </div>

      <div className="flex flex-1 justify-center">
        <button
          onClick={onOpenPalette}
          className="flex w-full max-w-[560px] items-center gap-2 rounded-lg border border-zinc-200/70 bg-white px-3 py-2 text-[15.5px] text-zinc-500 shadow-sm transition hover:bg-zinc-50 dark:border-white/[0.07] dark:bg-white/[0.02] dark:shadow-none dark:hover:bg-white/[0.05]"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="truncate">Search prompts, sessions, files…</span>
          <span className="ml-auto hidden items-center gap-0.5 font-mono text-[13px] text-zinc-400 sm:flex">
            <Command className="h-3 w-3" />K
          </span>
        </button>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-2">
        <div className="hidden items-center gap-1.5 rounded-md border border-zinc-200/70 bg-white px-2 py-1.5 font-mono text-[13px] text-zinc-600 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-400 lg:flex">
          <Cpu className="h-3 w-3 text-emerald-500" />
          {activeAgents} active
        </div>
        <button
          onClick={() => onView("settings")}
          className={`rounded-md border p-1.5 transition ${
            view === "settings"
              ? "border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-400/30 dark:bg-indigo-400/10 dark:text-indigo-300"
              : "border-zinc-200/70 bg-white text-zinc-600 hover:bg-zinc-50 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-300 dark:hover:bg-white/[0.06]"
          }`}
          title="Settings (⌘,)"
        >
          <SettingsIcon className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={toggle}
          className="rounded-md border border-zinc-200/70 bg-white p-1.5 text-zinc-600 hover:bg-zinc-50 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-300 dark:hover:bg-white/[0.06]"
        >
          {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </button>
        <button className="relative hidden rounded-md border border-zinc-200/70 bg-white p-1.5 text-zinc-600 hover:bg-zinc-50 dark:border-white/[0.07] dark:bg-white/[0.02] dark:text-zinc-300 dark:hover:bg-white/[0.06] sm:block">
          <Bell className="h-3.5 w-3.5" />
          <span className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-rose-500" />
        </button>
      </div>
    </div>
  );
}
