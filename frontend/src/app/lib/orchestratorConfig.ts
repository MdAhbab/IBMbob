import type { OrchestratorCfg } from "../components/store";

export function routingStrategyToBackend(
  strategy: OrchestratorCfg["routingStrategy"],
): string {
  const map: Record<OrchestratorCfg["routingStrategy"], string> = {
    specialty: "auto",
    cheapest: "least_cost",
    round_robin: "round_robin",
    fastest: "fastest",
  };
  return map[strategy];
}

export function routingStrategyFromBackend(
  backend: string,
): OrchestratorCfg["routingStrategy"] {
  const map: Record<string, OrchestratorCfg["routingStrategy"]> = {
    auto: "specialty",
    manual: "specialty",
    least_cost: "cheapest",
    round_robin: "round_robin",
    fastest: "fastest",
  };
  return map[backend] ?? "specialty";
}

export type OrchestratorConfigApi = {
  routing_strategy?: string;
  config_data?: Record<string, unknown> | null;
};

export function orchestratorFromApi(
  base: OrchestratorCfg,
  api: OrchestratorConfigApi,
): OrchestratorCfg {
  const data = api.config_data ?? {};
  const model =
    typeof data.model_name === "string"
      ? data.model_name
      : typeof data.model === "string"
      ? data.model
      : base.model;

  return {
    ...base,
    model,
    routingStrategy: api.routing_strategy
      ? routingStrategyFromBackend(api.routing_strategy)
      : base.routingStrategy,
    parallelism:
      typeof data.parallelism === "number" ? data.parallelism : base.parallelism,
    autoFailover:
      typeof data.auto_failover === "boolean" ? data.auto_failover : base.autoFailover,
    globalDailyCap:
      typeof data.global_daily_cap === "number"
        ? data.global_daily_cap
        : base.globalDailyCap,
  };
}

export function orchestratorToApiPayload(orchestrator: OrchestratorCfg) {
  return {
    routing_strategy: routingStrategyToBackend(orchestrator.routingStrategy),
    config_data: {
      model_name: orchestrator.model,
      parallelism: orchestrator.parallelism,
      auto_failover: orchestrator.autoFailover,
      global_daily_cap: orchestrator.globalDailyCap,
    },
  };
}
