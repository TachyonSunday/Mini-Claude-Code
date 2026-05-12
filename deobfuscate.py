#!/usr/bin/env python3
"""Deobfuscate Python code by replacing placeholder names with meaningful ones."""

import json
import os
import sys
import time
from openai import OpenAI

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SRC_FILE = os.path.join(DATA_DIR, "codexglue_py_2k.jsonl")
OUT_FILE = os.path.join(DATA_DIR, "codexglue_py_deobfuscated.jsonl")
LOCK_FILE = os.path.join(DATA_DIR, ".deobfuscate.lock")

PROMPT = """你是代码分析专家。下面这段 Python 代码使用了占位符名称。请重命名为有意义的英文名称。只返回重命名后的代码，不要添加任何解释。"""


def deobfuscate_one(client, code):
    for _ in range(2):
        try:
            resp = client.chat.completions.create(
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                messages=[{"role": "system", "content": PROMPT},
                          {"role": "user", "content": code[:1200]}],
                temperature=0.1, max_tokens=2048,
            )
            text = resp.choices[0].message.content.strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:])
            if text.endswith("```"):
                text = text[:-3]
            return text.strip()
        except Exception:
            time.sleep(2)
    return None


def main():
    if not DEEPSEEK_KEY:
        print("Set DEEPSEEK_API_KEY"); sys.exit(1)
    if os.path.exists(LOCK_FILE):
        print(f"Lock file exists: {LOCK_FILE}"); sys.exit(1)

    with open(LOCK_FILE, "w") as lf:
        lf.write(str(os.getpid()))

    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

    # Load all input
    items = []
    with open(SRC_FILE) as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    print(f"Input: {len(items)} items")

    # Load already-done IDs from output file
    done = set()
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE) as f:
            for line in f:
                if line.strip():
                    try:
                        done.add(json.loads(line)["id"])
                    except Exception:
                        pass
    print(f"Already done: {len(done)}, remaining: {len(items) - len(done)}")

    if len(done) >= len(items):
        print("All done!")
        os.remove(LOCK_FILE)
        return

    ok = err = 0
    with open(OUT_FILE, "a") as f:
        for item in items:
            if item["id"] in done:
                continue
            de_buggy = deobfuscate_one(client, item["python_buggy"])
            de_fixed = deobfuscate_one(client, item["python_fixed"])
            if de_buggy and de_fixed:
                item["deobfuscated_buggy"] = de_buggy
                item["deobfuscated_fixed"] = de_fixed
                ok += 1
            else:
                item["deobfuscated_buggy"] = item["python_buggy"]
                item["deobfuscated_fixed"] = item["python_fixed"]
                err += 1
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()

            total = len(done) + ok + err
            if total % 10 == 0:
                print(f"  [{total}/{len(items)}] ok={ok} err={err}")
                time.sleep(0.5)

    os.remove(LOCK_FILE)
    print(f"\nDone! ok={ok} err={err}, total={len(done)+ok+err}")


if __name__ == "__main__":
    main()
