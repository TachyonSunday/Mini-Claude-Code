#!/usr/bin/env python3
"""Extract fix pattern statistics from CodeXGLUE dataset."""

import json
import re
import os
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Pattern rules: (category, [regex patterns matching the change])
PATTERNS = [
    ("空值/除零检查", [
        r'\bif\s*\(.*(?:\bnull\b|==\s*0|!=\s*0|<=>\s*0)\s*\)',
        r'\bif\s*\([^)]*\b(is\s+empty|isEmpty|size\s*\(\)\s*==\s*0)',
        r'\bnull\b',
    ]),
    ("边界修正", [
        r'\b(length|size\(\))\s*[-+]\s*\d',
        r'\b(index|start|end|mid)\s*[-+]\s*\d',
        r'\bi\s*[<>=]+\s*[a-zA-Z_]*length',
        r'\bVAR_\d+\s*\.\s*size\s*\(\s*\)',
    ]),
    ("异常处理", [
        r'\btry\s*\{',
        r'\bcatch\s*\(',
        r'\bthrows?\s+',
        r'\bthrow\s+new\s+',
        r'\bError\b',
        r'\bException\b',
    ]),
    ("类型转换", [
        r'\(\s*(int|float|double|long|String)\s*\)',
        r'\bInteger\.parseInt\b',
        r'\btoString\b',
        r'\bvalueOf\b',
    ]),
    ("条件逻辑", [
        r'\bif\s*\(',
        r'\belse\s+if\b',
        r'\bswitch\b',
        r'[=!<>]=\s*[^=]',
        r'\?[\s\n]*:',
    ]),
    ("循环修正", [
        r'\bfor\s*\(',
        r'\bwhile\s*\(',
        r'\bbreak\b',
        r'\bcontinue\b',
    ]),
    ("变量赋值", [
        r'\bVAR_\d+\s*=\s*[^=]',
        r'\breturn\s+',
        r'\bTYPE_\d+\s+VAR_\d+',
    ]),
]


def classify_fix(buggy: str, fixed: str) -> list[str]:
    """Classify the fix type based on what changed between buggy and fixed."""
    # Extract the part that changed
    added = fixed[len(buggy):] if fixed.startswith(buggy) else ""
    removed = buggy[len(fixed):] if buggy.startswith(fixed) else ""

    # If simple prefix/suffix change, analyze the changed part
    changed = added or removed
    if not changed:
        # Find common prefix and suffix
        i = 0
        while i < min(len(buggy), len(fixed)) and buggy[i] == fixed[i]:
            i += 1
        j = 1
        while j <= min(len(buggy), len(fixed)) and buggy[-j] == fixed[-j]:
            j += 1
        changed = buggy[i:len(buggy)-j+1] + "→" + fixed[i:len(fixed)-j+1]

    # Check each pattern category
    matched = []
    for category, rules in PATTERNS:
        for rule in rules:
            if re.search(rule, changed, re.IGNORECASE):
                matched.append(category)
                break  # one match per category

    return matched if matched else ["其他"]


def main():
    data_file = os.path.join(DATA_DIR, "codexglue_2k.jsonl")
    if not os.path.exists(data_file):
        print(f"Data file not found: {data_file}")
        return

    # Load and classify
    counter = Counter()
    per_category_examples: dict[str, list[dict]] = {}
    total = 0

    with open(data_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            buggy = item.get("buggy", "")
            fixed = item.get("fixed", "")

            categories = classify_fix(buggy, fixed)
            for cat in categories:
                counter[cat] += 1
                if cat not in per_category_examples:
                    per_category_examples[cat] = []
                if len(per_category_examples[cat]) < 3:
                    per_category_examples[cat].append(item)
            total += 1

    # Print statistics
    print(f"=== 从 {total} 个样本中提取的 Fix Pattern 分布 ===\n")
    print(f"{'Bug 类型':<16} {'数量':>6} {'占比':>8}")
    print("-" * 32)

    stats = {}
    for cat, count in counter.most_common():
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        stats[cat] = {"count": count, "pct": round(pct, 1)}
        print(f"{cat:<16} {count:>6}   {pct:>5.1f}%  {bar}")

    print(f"\n总样本: {total}")
    print(f"总分类命中: {sum(counter.values())} (一条样本可能匹配多个类别)")

    # Show examples per category
    print(f"\n=== 各类别典型示例 ===\n")
    for cat in counter.most_common():
        cat = cat[0]
        print(f"--- {cat} ---")
        for ex in per_category_examples.get(cat, [])[:2]:
            buggy = ex["buggy"][:100].replace("\n", " ")
            fixed = ex["fixed"][:100].replace("\n", " ")
            print(f"  修复前: {buggy}...")
            print(f"  修复后: {fixed}...")
            print()

    # Save stats as JSON for injection into planner
    out_file = os.path.join(DATA_DIR, "fix_patterns.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"统计数据已保存到: {out_file}")

    # Print the injection prompt snippet
    print(f"\n=== 可注入规划Agent的统计知识 ===")
    print(generate_injection_prompt(stats))


def generate_injection_prompt(stats: dict) -> str:
    """Generate a prompt snippet summarizing the statistical findings."""
    sorted_cats = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)
    lines = ["根据对 2000 个历史代码修复案例的统计分析，常见 bug 类型及分布如下：", ""]
    for cat, s in sorted_cats:
        lines.append(f"  - {cat}: 占比 {s['pct']}% ({s['count']} 例)")
    lines.append("")
    lines.append("制定修复方案时，优先对照以上常见类型，选择合适的修复模式。")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
