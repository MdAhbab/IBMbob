import { apiFetch } from "./api";

export type ClientEventType =
  | "message_sent"
  | "message_received"
  | "session_created"
  | "session_completed"
  | "file_uploaded"
  | "command_executed"
  | "error_occurred";

export async function trackAnalyticsEvent(
  eventType: ClientEventType,
  opts?: {
    sessionId?: number | null;
    providerId?: number | null;
    tokensUsed?: number;
    costEstimate?: number;
    metadata?: Record<string, unknown>;
  },
): Promise<void> {
  try {
    await apiFetch("/analytics/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_type: eventType,
        session_id: opts?.sessionId ?? null,
        provider_id: opts?.providerId ?? null,
        tokens_used: opts?.tokensUsed ?? 0,
        cost_estimate: opts?.costEstimate ?? 0,
        metadata: opts?.metadata ?? null,
      }),
      timeoutMs: 5000,
    });
  } catch {
    /* telemetry must not block UX */
  }
}
