#!/usr/bin/env python3
"""Ablation experiment: run N CodeXGLUE samples through each agent configuration."""

import csv
import json
import os
import sys
import time
import shutil

sys.path.insert(0, os.path.dirname(__file__))

from tools import set_workspace
from orchestrator import Orchestrator

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
WORKSPACE = os.path.join(os.path.dirname(__file__), "workspace")


def load_samples(limit: int = 50) -> list[dict]:
    path = os.path.join(DATA_DIR, "codexglue_test.jsonl")
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            if line.strip():
                samples.append(json.loads(line))
    return samples


def setup_workspace(buggy_code: str) -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    for f in os.listdir(WORKSPACE):
        p = os.path.join(WORKSPACE, f)
        if os.path.isfile(p):
            os.remove(p)
        elif os.path.isdir(p) and f != ".git":
            shutil.rmtree(p)
    set_workspace(WORKSPACE)
    with open(os.path.join(WORKSPACE, "buggy.java"), "w") as f:
        f.write(buggy_code)


def run_one(sample: dict, config: str) -> dict:
    buggy = sample.get("buggy", "")
    sample_id = sample.get("id", "?")

    setup_workspace(buggy)

    use_rag = config == "stats"
    use_stats = config == "stats"
    orch = Orchestrator(use_rag=use_rag, use_stats=use_stats)

    if config == "no_reviewer":
        orch.reviewer = None
    elif config == "no_planner":
        orch.planner = None
    elif config == "single":
        orch.planner = None
        orch.reviewer = None

    task = f"修复 buggy.java 中的bug。代码：\n```\n{buggy[:1500]}\n```"

    start = time.time()
    result = orch.run(task)
    elapsed = time.time() - start

    return {
        "id": sample_id,
        "config": config,
        "success": result.get("success", False),
        "elapsed": round(elapsed, 1),
        "plan_summary": (result.get("plan", "") or "")[:200].replace("\n", " "),
        "review_summary": (result.get("review", "") or "")[:200].replace("\n", " "),
    }


def run_ablation(limit: int = 50) -> list[dict]:
    samples = load_samples(limit)
    configs = ["full", "no_reviewer", "no_planner", "single", "stats"]
    results = []

    for config in configs:
        print(f"\n=== {config} ({limit} samples) ===")
        for i, sample in enumerate(samples):
            r = run_one(sample, config)
            results.append(r)
            status = "✓" if r["success"] else "✗"
            print(f"  [{i+1}/{limit}] {status}  {r['elapsed']}s  id={r['id']}")
            sys.stdout.flush()

    return results


def save_csv(results: list[dict], path: str) -> None:
    """Save per-sample results and aggregate table as CSV."""
    # Per-sample results
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "config", "success", "elapsed",
                                                "plan_summary", "review_summary"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nPer-sample CSV: {path}")

    # Aggregate table
    by_config = {}
    for r in results:
        c = r["config"]
        if c not in by_config:
            by_config[c] = {"total": 0, "passed": 0, "total_time": 0.0}
        by_config[c]["total"] += 1
        if r["success"]:
            by_config[c]["passed"] += 1
        by_config[c]["total_time"] += r["elapsed"]

    agg_path = path.replace(".csv", "_aggregate.csv")
    with open(agg_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["config", "total", "passed", "accuracy", "avg_time_s"])
        for config in ["full", "no_reviewer", "no_planner", "single", "stats"]:
            s = by_config.get(config)
            if s:
                acc = s["passed"] / s["total"] if s["total"] else 0
                avg_t = round(s["total_time"] / s["total"], 1)
                writer.writerow([config, s["total"], s["passed"], round(acc, 3), avg_t])

    print(f"Aggregate CSV: {agg_path}")
    print()
    for config in ["full", "no_reviewer", "no_planner", "single", "stats"]:
        s = by_config.get(config)
        if s:
            acc = s["passed"] / s["total"] if s["total"] else 0
            bar = "█" * int(acc * 30)
            print(f"  {config:<13} {bar:<30} {acc:.1%}  ({s['passed']}/{s['total']})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("Set DEEPSEEK_API_KEY first")
        sys.exit(1)

    # Rebuild RAG index on every run to use latest embedder
    from rag.retriever import set_paths, build_index
    set_paths(DATA_DIR)
    build_index(
        os.path.join(DATA_DIR, "codexglue_2k.jsonl"),
        os.path.join(DATA_DIR, "index.faiss"),
    )

    results = run_ablation(limit=args.limit)
    save_csv(results, os.path.join(DATA_DIR, "ablation_results.csv"))
