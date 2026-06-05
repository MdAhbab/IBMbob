"""
Benchmark-informed routing helpers.

Loads cli_benchmarks.json (synthesized from the AI CLI Research & Benchmarking
report) and exposes:
  - get_benchmarks()        — raw {slug: data} map.
  - bench_score(slug)       — 0-100 capability index for tie-breaking.
  - routing_guidance_block()— a compact markdown block injected into the
                              orchestrator system prompt so the central AI
                              routes by real benchmark strengths.
  - rank_eligible(slugs, task_hint) — order candidate slugs best-first, with a
                              task-type boost when the task matches best_for.

All functions are defensive: a missing/corrupt JSON degrades to neutral
behavior and never breaks planning or handoff.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BENCH_PATH = Path(__file__).resolve().parent / "cli_benchmarks.json"
_DEFAULT_SCORE = 50.0


@lru_cache(maxsize=1)
def _load() -> Dict[str, Any]:
    try:
        with open(_BENCH_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        clis = data.get("clis")
        if isinstance(clis, dict):
            return clis
    except Exception:
        logger.warning("Could not load cli_benchmarks.json; routing will use neutral scores.", exc_info=True)
    return {}


def get_benchmarks() -> Dict[str, Any]:
    """Return the {slug: benchmark_data} map (possibly empty)."""
    return _load()


def _norm(slug: str) -> str:
    return (slug or "").strip().lower()


def bench_score(slug: str) -> float:
    """Return a 0-100 capability index for a slug (default 50 if unknown)."""
    entry = _load().get(_norm(slug))
    if not entry:
        return _DEFAULT_SCORE
    try:
        return float(entry.get("rank_score", _DEFAULT_SCORE))
    except (TypeError, ValueError):
        return _DEFAULT_SCORE


def best_for(slug: str) -> List[str]:
    entry = _load().get(_norm(slug)) or {}
    return [str(x).lower() for x in (entry.get("best_for") or [])]


def rank_eligible(slugs: List[str], task_hint: Optional[str] = None) -> List[str]:
    """
    Order candidate slugs best-first by benchmark rank_score, applying a boost
    when the task text matches a CLI's best_for tags.
    """
    hint = (task_hint or "").lower()

    def score(slug: str) -> float:
        s = bench_score(slug)
        if hint:
            for tag in best_for(slug):
                if tag and tag in hint:
                    s += 15.0  # task-type match boost
                    break
        return s

    return sorted(slugs, key=score, reverse=True)


def routing_guidance_block(installable_only: bool = True) -> str:
    """
    Build a compact markdown block describing each CLI's benchmark strengths,
    for injection into the orchestrator system prompt. Returns "" if no data.
    """
    clis = _load()
    if not clis:
        return ""

    rows: List[str] = []
    for slug, data in sorted(clis.items(), key=lambda kv: float(kv[1].get("rank_score", 0)), reverse=True):
        if installable_only and not data.get("installable"):
            continue
        rank = data.get("rank_score", "?")
        bestfor = ", ".join(data.get("best_for") or []) or "general"
        rows.append(f"| {slug} | {rank} | {bestfor} |")

    if not rows:
        return ""

    header = (
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "BENCHMARK-INFORMED ROUTING (use real strengths, not guesses)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "When choosing which CLI gets a task, prefer the agent whose `best_for`\n"
        "matches the task type; break ties using the higher capability `rank`\n"
        "(0-100, from SWE-bench/Terminal-Bench). Only assign to ENABLED agents.\n\n"
        "| agent | rank | best for |\n"
        "| :---- | :--- | :------- |\n"
    )
    return header + "\n".join(rows) + "\n"
