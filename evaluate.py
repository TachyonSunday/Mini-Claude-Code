#!/usr/bin/env python3
"""Ablation experiment with incremental CSV saving."""

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


def load_samples(limit: int = 15) -> list[dict]:
    path = os.path.join(DATA_DIR, "codexglue_py_deobfuscated.jsonl")
    all_items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_items.append(json.loads(line))
    return all_items[-limit:]


def setup_workspace(code: str) -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    for f in os.listdir(WORKSPACE):
        p = os.path.join(WORKSPACE, f)
        if os.path.isfile(p): os.remove(p)
        elif os.path.isdir(p) and f != ".git": shutil.rmtree(p)
    set_workspace(WORKSPACE)
    with open(os.path.join(WORKSPACE, "code.py"), "w") as f:
        f.write(code)


def run_one(sample: dict, config: str) -> dict:
    buggy = sample.get("deobfuscated_buggy") or sample.get("python_buggy") or ""
    sid = sample.get("id", "?")

    setup_workspace(buggy)

    use_rag = config == "rag"
    use_stats = config == "stats"
    use_clf = config == "classifier"
    orch = Orchestrator(use_rag=use_rag, use_stats=use_stats, use_classifier=use_clf)

    if config == "no_reviewer": orch.reviewer = None
    elif config == "no_planner": orch.planner = None
    elif config == "single": orch.planner = None; orch.reviewer = None

    task = f"修复 code.py 中的 bug"

    start = time.time()
    result = orch.run(task)
    elapsed = time.time() - start

    # Compute edit distance between buggy and fixed as complexity proxy
    from difflib import SequenceMatcher
    fixed_code = sample.get("deobfuscated_fixed") or sample.get("python_fixed") or ""
    similarity = SequenceMatcher(None, buggy, fixed_code).ratio()
    complexity = round(1 - similarity, 3)  # 0=identical, 1=completely different

    return {
        "id": sid, "config": config,
        "success": result.get("success", False),
        "elapsed": round(elapsed, 1),
        "fix_type": sample.get("fix_type", "unknown"),
        "complexity": complexity,
        "buggy_lines": buggy.count('\n') + 1,
        "plan_summary": (result.get("plan", "") or "")[:100].replace("\n", " "),
        "review_summary": (result.get("review", "") or "")[:100].replace("\n", " "),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("Set DEEPSEEK_API_KEY"); sys.exit(1)

    samples = load_samples(args.limit)
    configs = ["full", "no_reviewer", "no_planner", "single", "stats", "classifier"]
    out_path = os.path.join(DATA_DIR, "ablation_results.csv")

    # Write CSV header
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id","config","success","elapsed","fix_type","complexity","buggy_lines","plan_summary","review_summary"])
        w.writeheader()

    for config in configs:
        print(f"\n=== {config} ({args.limit} samples) ===")
        for sample in samples:
            r = run_one(sample, config)
            with open(out_path, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["id","config","success","elapsed","fix_type","complexity","buggy_lines","plan_summary","review_summary"])
                w.writerow(r)
            s = "✓" if r["success"] else "✗"
            print(f"  {s} id={r['id']}  {r['elapsed']}s")
            sys.stdout.flush()

    # Aggregate
    all_r = []
    with open(out_path, "r") as f:
        for row in csv.DictReader(f):
            row["success"] = row["success"] == "True"
            row["elapsed"] = float(row["elapsed"])
            all_r.append(row)

    by_cfg = {}
    for r in all_r:
        c = r["config"]
        if c not in by_cfg: by_cfg[c] = {"total":0,"passed":0,"times":[]}
        by_cfg[c]["total"] += 1
        if r["success"]: by_cfg[c]["passed"] += 1
        by_cfg[c]["times"].append(r["elapsed"])

    agg_path = out_path.replace(".csv", "_aggregate.csv")
    with open(agg_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["config","total","passed","accuracy","avg_time_s"])
        for c in configs:
            s = by_cfg.get(c)
            if s:
                acc = s["passed"]/s["total"] if s["total"] else 0
                avg = round(sum(s["times"])/len(s["times"]),1) if s["times"] else 0
                w.writerow([c, s["total"], s["passed"], round(acc,3), avg])

    print(f"\nCSV: {out_path}")
    for c in configs:
        s = by_cfg.get(c)
        if s:
            acc = s["passed"]/s["total"]
            bar = "█" * int(acc*30)
            print(f"  {c:<13} {bar:<30} {acc:.1%} ({s['passed']}/{s['total']})")


if __name__ == "__main__":
    main()
