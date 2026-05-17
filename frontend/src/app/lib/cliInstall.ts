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
  bob: {
    install: "pip install ibm-watsonx-ai",
    verify: "python -c \"import ibm_watsonx_ai; print('ok')\"",
    notes: "Orchestrator chat uses Watsonx — set WATSONX_API_KEY and WATSONX_PROJECT_ID in backend/.env.",
  },
};

export function cliInstallForProvider(providerId: string): CliInstallInfo | undefined {
  return CLI_INSTALL_BY_ID[providerId];
}
