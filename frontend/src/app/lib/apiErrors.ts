export async function parseApiError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as {
      detail?: string | { msg?: string; loc?: unknown[] }[];
      error?: string;
    };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
    }
    if (data.error) return data.error;
  } catch {
    const text = await res.text().catch(() => "");
    if (text) return text.slice(0, 400);
  }
  return res.statusText || `HTTP ${res.status}`;
}
