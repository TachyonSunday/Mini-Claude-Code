#!/usr/bin/env python3
"""Interactive terminal demo for Mini Claude Code."""

import sys
import os
import unicodedata
import shutil

# Load .env if present
def load_dotenv():
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import set_workspace
from orchestrator import Orchestrator


def display_width(s: str) -> int:
    """Return visual column width accounting for CJK wide characters."""
    w = 0
    for ch in s:
        ea = unicodedata.east_asian_width(ch)
        w += 2 if ea in ('W', 'F') else 1
    return w


def pad_to_width(s: str, target: int) -> str:
    """Pad string on the right to reach target visual width."""
    current = display_width(s)
    return s + ' ' * max(0, target - current)


def make_banner() -> str:
    """Build a properly aligned banner with CJK-aware padding."""
    TOTAL = 48  # total visual columns (corners + border + corners)
    left = "║  "
    right = "  ║"
    inner_w = TOTAL - display_width(left) - display_width(right)  # 48 - 3 - 3 = 42

    return (
        f"╔{'═' * (TOTAL - 2)}╗\n"
        f"{left}{pad_to_width('Mini Claude Code', inner_w)}{right}\n"
        f"{left}{pad_to_width('多 Agent 编程助手', inner_w)}{right}\n"
        f"╚{'═' * (TOTAL - 2)}╝"
    )


DEMOS = {
    "1": {
        "name": "修复 utils.py 除零 bug",
        "desc": "展示理解已有代码并精准修复的能力",
        "setup": lambda ws: (
            open(os.path.join(ws, "utils.py"), "w").write(
                'def divide(a, b):\n    return a / b\n\n'
                'def multiply(a, b):\n    return a * b\n'
            ),
            open(os.path.join(ws, "test_utils.py"), "w").write(
                'from utils import divide, multiply\n\n'
                'def test_divide():\n'
                '    assert divide(10, 2) == 5\n\n'
                'def test_multiply():\n'
                '    assert multiply(3, 4) == 12\n'
            ),
        ),
        "task": "utils.py 的 divide 函数没有处理除零，帮我修一下",
    },
    "2": {
        "name": "从零生成井字棋游戏",
        "desc": "展示根据自然语言描述创造新代码的能力",
        "setup": lambda ws: None,
        "task": "写一个命令行井字棋游戏 tictactoe.py，两个玩家轮流输入坐标下棋，判断胜负或平局",
    },
    "3": {
        "name": "给未测试的函数补单元测试",
        "desc": "展示理解代码逻辑并补充测试的能力",
        "setup": lambda ws: (
            open(os.path.join(ws, "calc.py"), "w").write(
                'def add(a, b):\n    return a + b\n\n'
                'def subtract(a, b):\n    return a - b\n\n'
                'def fibonacci(n):\n'
                '    if n <= 1:\n'
                '        return n\n'
                '    return fibonacci(n - 1) + fibonacci(n - 2)\n'
            ),
        ),
        "task": "calc.py 缺少单元测试，请为所有函数编写测试文件 test_calc.py",
    },
}


def run_demo(demo_key: str) -> None:
    demo = DEMOS[demo_key]
    ws = os.path.join(os.path.dirname(__file__), "workspace")
    os.makedirs(ws, exist_ok=True)
    for f in os.listdir(ws):
        p = os.path.join(ws, f)
        if os.path.isfile(p):
            os.remove(p)
        elif os.path.isdir(p):
            shutil.rmtree(p)
    set_workspace(ws)

    print(make_banner())
    print(f"  📋 {demo['name']}")
    print(f"  💡 {demo['desc']}")
    print()
    print(f"📝 任务: {demo['task']}")
    print()

    if demo["setup"]:
        demo["setup"](ws)
        print("📂 初始文件：")
        for f in sorted(os.listdir(ws)):
            print(f"   └─ {f}")
        print()

    def on_progress(agent_name: str, msg: str):
        print(f"  {msg}")

    orch = Orchestrator(on_progress=on_progress)
    result = orch.run(demo["task"])

    _print_result(result, ws)


def _print_result(result: dict, ws: str) -> None:
    """Print the orchestrator result with phase summaries."""
    print()

    if not result.get("success"):
        _print_review_rejection(result)
        return

    for entry in result["trace"]:
        phase = entry["phase"]
        output = entry.get("output", "")
        if not output:
            continue
        if phase == "plan":
            _print_phase_box("🔍 规划Agent", output)
        elif phase.startswith("code"):
            _print_phase_box("✏️ 编码Agent", output)
        elif phase.startswith("review"):
            _print_phase_box("✅ 审查Agent", output)

    print("✅ 完成\n")

    print("📂 最终文件：")
    for f in sorted(os.listdir(ws)):
        p = os.path.join(ws, f)
        if os.path.isfile(p):
            print(f"   └─ {f} ({os.path.getsize(p)} bytes)")


def _print_review_rejection(result: dict) -> None:
    """Show review failure prominently with the actual feedback."""
    review = result.get("review", "")
    w = 62
    print("┌" + "─" * w + "┐")
    print("│ ❌ 审查未通过 — 以下是审查Agent的反馈" + " " * (w - 22) + "│")
    print("├" + "─" * w + "┤")
    for line in review.split("\n")[:24]:
        print(f"│ {line[:w]}")
    if len(review.split("\n")) > 24:
        print(f"│ ...")
    print("└" + "─" * w + "┘")
    print()
    print("💡 输入 /retry 让 Agent 根据反馈重新修改")
    print("   输入 /new   放弃当前任务，开始新的")


def _print_phase_box(title: str, output: str, max_lines: int = 12, verbose: bool = False) -> None:
    """Print a phase summary box. In verbose mode, show all lines."""
    lines = output.split("\n")
    if verbose:
        max_lines = len(lines)
    w = 60  # content width
    # Top: ┌─ title ──────┐  → total = w + 4
    # Bot: └──────────────┘  → same total
    dash_top = w - 1 - display_width(title)
    print(f"┌─ {title} " + "─" * max(0, dash_top) + "┐")
    for line in lines[:max_lines]:
        print(f"│ {line[:w]}")
    if len(lines) > max_lines:
        print(f"│ ... ({len(lines) - max_lines} more lines, /verbose 看全部)")
    print("└" + "─" * (w + 2) + "┘")
    print()


def _workspace_files(ws: str) -> list[str]:
    items = []
    for f in sorted(os.listdir(ws)):
        p = os.path.join(ws, f)
        if os.path.isfile(p):
            items.append(f"📄 {f} ({os.path.getsize(p)} bytes)")
        else:
            items.append(f"📁 {f}/")
    return items


def _clean_workspace(ws: str) -> None:
    for f in os.listdir(ws):
        p = os.path.join(ws, f)
        if os.path.isfile(p):
            os.remove(p)
        elif os.path.isdir(p) and f not in ('.git',):
            shutil.rmtree(p)


def interactive_mode(use_rag: bool = False, use_stats: bool = False,
                     use_classifier: bool = False, self_consistency: int = 1):
    """Interactive REPL: user types tasks, agents execute. Supports retry on failure."""
    ws = os.path.join(os.path.dirname(__file__), "workspace")
    os.makedirs(ws, exist_ok=True)
    set_workspace(ws)

    print(make_banner())
    print()
    rag_status = "(RAG 已启用)" if use_rag else ""
    stats_status = "(统计模式)" if use_stats else ""
    tags = " ".join(filter(None, [rag_status, stats_status]))
    print(f"💬 输入自然语言描述任务，三 Agent 自动协作完成。{tags}")
    print("   /help  帮助    /files  查看文件    /clear  清空工作区")
    print("   /new   新任务  /retry  根据审查反馈重新修改")
    print("   /verbose  切换完整输出    /rag  切换RAG    /stats  切换统计模式")
    print()

    last_task = ""
    last_result = None
    orch = None
    verbose = False

    def on_progress(agent_name: str, msg: str):
        print(f"  {msg}")

    while True:
        try:
            raw = input("🗣️  你说: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not raw:
            continue

        # --- Commands ---
        if raw in ("/quit", "/exit"):
            print("👋 再见！")
            break

        if raw == "/help":
            print("  📋 /help   帮助")
            print("  📂 /files  查看工作区文件")
            print("  🧹 /clear  清空工作区文件")
            print("  🆕 /new    开始新任务")
            print("  🔄 /retry  让Agent根据审查反馈重新修改")
            print()
            print("  示例: 写一个冒泡排序函数")
            print("  示例: math_utils.py 的 factorial 没有处理负数")
            print("  示例: 给 calc.py 写单元测试")
            continue

        if raw == "/files":
            files = _workspace_files(ws)
            if files:
                for f in files:
                    print(f"   {f}")
            else:
                print("   (空)")
            continue

        if raw == "/clear":
            _clean_workspace(ws)
            last_task = ""
            last_result = None
            print("   🧹 工作区已清空")
            continue

        if raw == "/rag":
            use_rag = not use_rag
            status = "开启" if use_rag else "关闭"
            print(f"   🔍 RAG检索：{status}")
            continue

        if raw == "/stats":
            use_stats = not use_stats
            status = "开启" if use_stats else "关闭"
            print(f"   📊 统计模式注入：{status}")
            continue

        if raw == "/verbose":
            verbose = not verbose
            status = "开启" if verbose else "关闭"
            print(f"   📝 完整输出模式：{status}")
            continue

        if raw == "/new":
            last_task = ""
            last_result = None
            orch = None
            print("   🆕 开始新任务")
            continue

        if raw == "/retry":
            if not last_result or last_result.get("success"):
                print("   没有需要修复的任务")
                continue
            review = last_result.get("review", "")
            task = f"根据以下审查反馈重新修改代码：\n{review}"
            print("   🔄 根据审查反馈重新修改...")
            # fall through to task execution
        elif raw.startswith("/"):
            print(f"   未知命令: {raw}，输入 /help 查看可用命令")
            continue
        else:
            last_task = raw
            task = raw

        print()
        orch = Orchestrator(on_progress=on_progress, use_rag=use_rag,
                             use_stats=use_stats, use_classifier=use_classifier,
                             self_consistency=self_consistency)
        last_result = orch.run(task if last_result is None or last_result.get("success")
                               else task)
        print()

        if last_result.get("success"):
            for entry in last_result["trace"]:
                phase = entry["phase"]
                output = entry.get("output", "")
                if not output:
                    continue
                w = 38
                if phase == "plan":
                    label = "🔍 规划Agent"
                elif phase.startswith("code"):
                    label = "✏️ 编码Agent"
                elif phase.startswith("review"):
                    label = "✅ 审查Agent"
                else:
                    continue
                _print_phase_box(label, output, verbose=verbose)
            print("   ✅ 完成\n")
        else:
            _print_review_rejection(last_result)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Mini Claude Code Demo")
    parser.add_argument("demo", nargs="?", choices=["1", "2", "3"],
                        help="Demo number (1-3)")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Interactive mode: talk to agents directly")
    parser.add_argument("--list", action="store_true", help="List available demos")
    parser.add_argument("--rag", action="store_true", help="Enable RAG few-shot retrieval")
    parser.add_argument("--stats", action="store_true", help="Inject fix pattern statistics into planner")
    parser.add_argument("--consistency", type=int, default=1, help="Self-consistency sampling count (default 1=off)")
    parser.add_argument("--classifier", action="store_true", help="Use trained fix-type classifier")
    args = parser.parse_args()

    if os.environ.get("DEEPSEEK_API_KEY", "").startswith("sk-your-"):
        print("错误：请先在 .env 文件中设置你的 DEEPSEEK_API_KEY")
        print("cp .env.example .env  →  编辑 .env  →  source .env")
        sys.exit(1)
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("错误：未设置 DEEPSEEK_API_KEY 环境变量")
        print("方式一: export DEEPSEEK_API_KEY='your-key'")
        print("方式二: cp .env.example .env，编辑后 source .env")
        sys.exit(1)

    if args.interactive:
        interactive_mode(use_rag=args.rag, use_stats=args.stats,
                         use_classifier=args.classifier,
                         self_consistency=args.consistency)
    elif args.list:
        print(make_banner())
        print()
        print("可用 Demo：")
        for k, v in DEMOS.items():
            print(f"  {k}. {v['name']} — {v['desc']}")
        print("\n运行: python demo.py <编号>")
    elif args.demo:
        run_demo(args.demo)
    else:
        print(make_banner())
        print()
        print("可用 Demo：")
        for k, v in DEMOS.items():
            print(f"  {k}. {v['name']} — {v['desc']}")
        print()
        print("运行方式:")
        print("  python demo.py 1         运行预设 Demo")
        print("  python demo.py -i        交互模式，自由对话")


if __name__ == "__main__":
    main()
