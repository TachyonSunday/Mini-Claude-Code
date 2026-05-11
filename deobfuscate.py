#!/usr/bin/env python3
"""将 codexglue_py_2k.jsonl 中混淆的占位符替换为有意义的英文命名."""

import json
import os
import sys
import time

from openai import OpenAI

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SRC_FILE = os.path.join(DATA_DIR, "codexglue_py_2k.jsonl")
OUT_FILE = os.path.join(DATA_DIR, "codexglue_py_deobfuscated.jsonl")

PROMPT = """你是代码分析专家。下面这段 Python 代码使用了占位符名称（METHOD_1, VAR_1, TYPE_1, STRING_1 等）。

请根据代码的逻辑和上下文，推断这些占位符真实意图并重命名为有意义的英文名称。只返回重命名后的代码，保留所有原有逻辑、缩进和结构。不要添加任何解释。"""


def deobfuscate_one(client: OpenAI, code: str, retries: int = 2) -> str | None:
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": code[:1200]},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            text = resp.choices[0].message.content.strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:])
            if text.endswith("```"):
                text = text[:-3]
            return text.strip()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
    return None


def main():
    if not DEEPSEEK_KEY:
        print("Set DEEPSEEK_API_KEY first")
        sys.exit(1)

    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

    items = []
    with open(SRC_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    # Resume checkpoint: skip already processed items
    start_idx = 0
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            start_idx = sum(1 for _ in f)
        print(f"Resuming from item {start_idx}/{len(items)} "
              f"({start_idx/len(items)*100:.0f}% done)")

    print(f"Deobfuscating {len(items) - start_idx} remaining samples...")

    ok = err = 0
    mode = "a" if start_idx > 0 else "w"
    with open(OUT_FILE, mode, encoding="utf-8") as f:
        for i, item in enumerate(items):
            if i < start_idx:
                continue
        for i, item in enumerate(items):
            # Process both buggy and fixed code
            de_buggy = deobfuscate_one(client, item["python_buggy"])
            de_fixed = deobfuscate_one(client, item["python_fixed"])
            if de_buggy and de_fixed:
                item["deobfuscated_buggy"] = de_buggy
                item["deobfuscated_fixed"] = de_fixed
                ok += 1
            else:
                # Keep originals if deobfuscation failed
                item["deobfuscated_buggy"] = item["python_buggy"]
                item["deobfuscated_fixed"] = item["python_fixed"]
                err += 1
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()

            if (i + 1) % 10 == 0:
                pct = (i + 1) / len(items) * 100
                print(f"  [{i+1}/{len(items)}] {pct:.0f}%  ok={ok} err={err}")
                time.sleep(0.3)

    print(f"\nDone! ok={ok} err={err}")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
