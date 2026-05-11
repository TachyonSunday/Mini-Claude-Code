#!/usr/bin/env python3
"""用 DeepSeek 将 CodeXGLUE Java 数据翻译为 Python + 分类 fix type."""

import json
import os
import sys
import time

from openai import OpenAI

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

PROMPT = """你是代码分析专家。我会给你一段 Java buggy 代码和 fixed 代码。

请完成两件事：
1. 将这段代码的"bug-fix 关系"翻译成等价的 Python 代码对（保留 bug 本质和修复逻辑）
2. 判断这个修复属于以下哪个类型：空值检查/边界修正/异常处理/条件逻辑/循环修正/类型转换/赋值修正/其他

返回 JSON 格式：
{
  "python_buggy": "有bug的Python代码",
  "python_fixed": "修好的Python代码",
  "fix_type": "类型名"
}

只返回 JSON，不要其他文字。"""

FIX_TYPES = ["空值检查", "边界修正", "异常处理", "条件逻辑", "循环修正", "类型转换", "赋值修正", "其他"]


def translate_one(client: OpenAI, buggy: str, fixed: str, retries: int = 2) -> dict | None:
    """Call DeepSeek to translate+classify one sample."""
    user_msg = f"Buggy Java:\n{buggy[:800]}\n\nFixed Java:\n{fixed[:800]}"

    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            text = resp.choices[0].message.content
            # Extract JSON from response
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
            return json.loads(text)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  ERROR: {e}")
                return None


def main():
    if not DEEPSEEK_KEY:
        print("Set DEEPSEEK_API_KEY first")
        sys.exit(1)

    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

    # Load source data
    src_file = os.path.join(DATA_DIR, "codexglue_2k.jsonl")
    items = []
    with open(src_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    print(f"Processing {len(items)} samples...")

    out_file = os.path.join(DATA_DIR, "codexglue_py_2k.jsonl")
    type_counts: dict[str, int] = {t: 0 for t in FIX_TYPES}
    processed = 0
    errors = 0

    with open(out_file, "w", encoding="utf-8") as f:
        for i, item in enumerate(items):
            buggy = item.get("buggy", "")
            fixed = item.get("fixed", "")

            result = translate_one(client, buggy, fixed)
            if result and "python_buggy" in result and "python_fixed" in result:
                ft = result.get("fix_type", "其他")
                if ft not in type_counts:
                    ft = "其他"
                type_counts[ft] += 1
                processed += 1

                out_item = {
                    "id": i,
                    "python_buggy": result["python_buggy"],
                    "python_fixed": result["python_fixed"],
                    "fix_type": ft,
                    "java_buggy": buggy[:200],
                    "java_fixed": fixed[:200],
                }
                f.write(json.dumps(out_item, ensure_ascii=False) + "\n")
                f.flush()
            else:
                errors += 1

            # Progress
            if (i + 1) % 10 == 0:
                pct = (i + 1) / len(items) * 100
                print(f"  [{i+1}/{len(items)}] {pct:.0f}%  ok={processed} err={errors}")
                time.sleep(0.5)  # rate limit

    # Save statistics
    total = processed + errors
    stats = {}
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = round(count / processed * 100, 1) if processed else 0
        stats[t] = {"count": count, "pct": pct}

    with open(os.path.join(DATA_DIR, "fix_patterns.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Processed={processed} Errors={errors}")
    print(f"\n=== Fix Type Distribution ===")
    for t, s in sorted(stats.items(), key=lambda x: -x[1]["count"]):
        bar = "█" * int(s["pct"] / 2)
        print(f"  {t:<10} {s['count']:>5}  {s['pct']:>5.1f}%  {bar}")


if __name__ == "__main__":
    main()
