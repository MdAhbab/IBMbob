/** Install / verify commands for agent CLIs (shown when a tool is missing locally). */

export type CliInstallInfo = {
  install: string;
  verify: string;
  notes?: string;
};

/** Keys match provider ids in `store.tsx` (`claude`, `gemini`, …). */
export const CLI_INSTALL_BY_ID: Record<string, CliInstallInfo> = {
  claude: {
    install: "npm install -g @anthropic-ai/claude-code",
    verify: "claude --version",
    notes: "Requires Node.js 18+. Then run `claude` and sign in.",
  },
  gemini: {
    install: "npm install -g @google/gemini-cli",
    verify: "gemini --version",
    notes: "Requires Node.js 18+. Use `gemini auth login` after install.",
  },
  codex: {
    install: "npm install -g @openai/codex",
    verify: "codex --version",
    notes: "OpenAI Codex CLI; set OPENAI_API_KEY or sign in when prompted.",
  },
  copilot: {
    install: "npm install -g @github/copilot",
    verify: "copilot --version",
    notes: "Also install GitHub CLI: winget install GitHub.cli then `gh auth login`.",
  },
  deepseek: {
    install: "npm install -g deepseek-cli",
    verify: "deepseek --version",
    notes: "Set DEEPSEEK_API_KEY from platform.deepseek.com.",
  },
  kimi: {
    install: "npm install -g @moonshot-ai/cli",
    verify: "kimi --version",
    notes: "Moonshot / Kimi API key required.",
  },
  cline: {
    install: "npm install -g cline",
    verify: "cline --version",
    notes: "Bring-your-own-key; configure provider keys after install.",
  },
  grok: {
    install: "Configure GROK_API_KEY in Settings or backend/.env",
    verify: "curl https://api.x.ai/v1/models -H \"Authorization: Bearer $GROK_API_KEY\"",
    notes: "Grok powers orchestrator planning via the xAI API (no local CLI required).",
  },
  "gemini-api": {
    install: "Configure GEMINI_API_KEY in Settings or backend/.env",
    verify: "See Google AI Studio for API key validation",
    notes: "Gemini API is used as an orchestrator LLM fallback.",
  },
  "deepseek-api": {
    install: "Configure DEEPSEEK_API_KEY in Settings or backend/.env",
    verify: "curl https://api.deepseek.com/v1/models -H \"Authorization: Bearer $DEEPSEEK_API_KEY\"",
    notes: "DeepSeek API is used as an orchestrator LLM fallback.",
  },
};

export function cliInstallForProvider(providerId: string): CliInstallInfo | undefined {
  return CLI_INSTALL_BY_ID[providerId];
}
