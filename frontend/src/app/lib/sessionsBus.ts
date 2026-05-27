/** Cross-component session list refresh (MED-047 / MED-046). */
export const SESSIONS_CHANGED = "orch:sessions-changed";

export function notifySessionsChanged() {
  window.dispatchEvent(new CustomEvent(SESSIONS_CHANGED));
}

export function lastSessionStorageKey() {
  return "orch.lastSessionId";
}

export function saveLastSessionId(id: number) {
  try {
    localStorage.setItem(lastSessionStorageKey(), String(id));
  } catch {}
}

export function loadLastSessionId(): number | null {
  try {
    const v = localStorage.getItem(lastSessionStorageKey());
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}
