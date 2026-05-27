import { apiFetch } from "./api";
import type { SessionEntry } from "../components/store";

export function mapSessionStatus(raw: string): SessionEntry["status"] {
  if (raw === "completed") return "completed";
  if (raw === "failed") return "failed";
  if (raw === "paused") return "paused";
  if (raw === "archived") return "archived";
  return "active";
}

export async function fetchSessionEntries(limit = 20): Promise<SessionEntry[]> {
  const [sessionsRes, usageRes] = await Promise.all([
    apiFetch(`/sessions?limit=${limit}`),
    apiFetch("/analytics/usage?days=30"),
  ]);
  if (!sessionsRes.ok) return [];

  const j = await sessionsRes.json();
  let totalTokens = 0;
  let totalCost = 0;
  if (usageRes.ok) {
    const usage = await usageRes.json();
    totalTokens = Number(usage.total_tokens ?? 0);
    totalCost = Number(usage.total_cost ?? 0);
  }

  const sessionCount = Math.max(1, (j.sessions ?? []).length);
  return (j.sessions ?? []).map((s: any) => {
    let meta = s.metadata;
    if (meta && typeof meta === "string") {
      try {
        meta = JSON.parse(meta);
      } catch {
        meta = {};
      }
    }
    return {
      id: String(s.id),
      prompt: s.title ?? "(untitled session)",
      status: mapSessionStatus(String(s.status ?? "active")),
      startedAt: new Date(s.created_at).getTime(),
      endedAt: s.updated_at ? new Date(s.updated_at).getTime() : undefined,
      summary: s.description ?? "",
      agents: Array.isArray(meta?.delegated_agents) ? meta.delegated_agents : [],
      spend: totalCost / sessionCount,
      tokens: Math.round(totalTokens / sessionCount),
      artifacts: Array.isArray(meta?.artifacts)
        ? meta.artifacts.map((a: any) => a.name ?? String(a))
        : [],
    };
  });
}
