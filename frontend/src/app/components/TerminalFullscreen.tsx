import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { wsPath } from "../lib/api";

export function TerminalFullscreen() {
  const { id } = useParams<{ id: string }>();
  const [search] = useSearchParams();
  const name = search.get("name") ?? "terminal";
  const runtimeId = Number(id);
  const [status, setStatus] = useState<"connecting" | "open" | "error" | "closed">(
    "connecting",
  );

  const termContainer = useRef<HTMLDivElement | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!termContainer.current || Number.isNaN(runtimeId)) return;

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: 'Menlo, Consolas, "Cascadia Mono", monospace',
      fontSize: 13,
      lineHeight: 1.3,
      scrollback: 8000,
      theme: {
        background: "#0a0a0d",
        foreground: "#e4e4e7",
        cursor: "#a78bfa",
      },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(termContainer.current);
    termRef.current = term;
    fitRef.current = fit;
    queueMicrotask(() => {
      try {
        fit.fit();
      } catch {}
    });

    const ro = new ResizeObserver(() => {
      try {
        fit.fit();
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }),
          );
        }
      } catch {}
    });
    ro.observe(termContainer.current);

    return () => {
      ro.disconnect();
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, [runtimeId]);

  useEffect(() => {
    if (Number.isNaN(runtimeId)) {
      setStatus("error");
      return;
    }

    const url = wsPath(`/ws/terminals/${runtimeId}`);
    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    const onDataHandler = (data: string) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "input", data }));
      }
    };

    ws.onopen = () => {
      setStatus("open");
      termRef.current?.onData(onDataHandler);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "output" || msg.type === "ask.token") {
          termRef.current?.write(msg.data ?? msg.text ?? "");
        } else if (msg.type === "status") {
          termRef.current?.writeln(`\r\n[orch] status: ${msg.state}`);
        } else if (msg.type === "error") {
          termRef.current?.writeln(`\r\n[orch] error: ${msg.error}`);
        }
      } catch {}
    };

    ws.onerror = () => setStatus("error");
    ws.onclose = () => setStatus("closed");

    return () => {
      try {
        ws.close();
      } catch {}
      wsRef.current = null;
    };
  }, [runtimeId]);

  return (
    <div className="flex h-screen w-screen flex-col bg-[#0a0a0d] text-zinc-100">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-2">
        <div>
          <div className="text-[13px] text-white">{name}</div>
          <div className="font-mono text-[10px] text-zinc-500">
            runtime {id} · {status}
          </div>
        </div>
      </header>
      <div ref={termContainer} className="min-h-0 flex-1 p-2" />
    </div>
  );
}
