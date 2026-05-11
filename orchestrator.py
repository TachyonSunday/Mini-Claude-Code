"""Orchestrator: serial chain Planner → Coder → Reviewer with context passing."""

import os
from typing import Callable

from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent


class Orchestrator:
    """Schedules agents in sequence and passes context between them.

    Supports ablation: set planner=None or reviewer=None to skip that phase.
    """

    def __init__(self, use_rag: bool = False, use_stats: bool = False,
                 self_consistency: int = 1,
                 on_progress: Callable = None):
        stats = ""
        if use_stats:
            stats = self._load_stats()
        self.planner = PlannerAgent(on_progress=on_progress, stats=stats)
        self.coder = CoderAgent(on_progress=on_progress)
        self.reviewer = ReviewerAgent(on_progress=on_progress)
        self.use_rag = use_rag
        self.use_stats = use_stats
        self.self_consistency = self_consistency
        self.on_progress = on_progress
        self.trace: list[dict] = []

    def _run_self_consistency(self, plan_text: str, context: str) -> str:
        """Run coder N times and select the most consistent output."""
        n = self.self_consistency
        self._emit("code", f"Self-Consistency: 运行 {n} 次独立采样...")
        answers = []
        for i in range(n):
            self._emit("code", f"  第 {i+1}/{n} 次...")
            self.coder.reset()
            # Snapshot workspace before each run to restore
            from tools.file_tools import WORKSPACE_ROOT
            import shutil
            ws = str(WORKSPACE_ROOT) if WORKSPACE_ROOT else None
            snapshot = None
            if ws:
                snapshot = os.path.join(os.path.dirname(ws), ".snapshot")
                if os.path.exists(snapshot):
                    shutil.rmtree(snapshot)
                shutil.copytree(ws, snapshot, dirs_exist_ok=True)

            self.coder.run(
                task=f"按照以下方案执行代码修改：\n{plan_text}",
                context=context,
            )
            answers.append(self.coder.final_answer)

            # Restore workspace from snapshot for next run
            if snapshot and os.path.exists(snapshot):
                for f in os.listdir(ws):
                    p = os.path.join(ws, f)
                    if os.path.isfile(p):
                        os.remove(p)
                    elif os.path.isdir(p) and f != ".git":
                        shutil.rmtree(p)
                for f in os.listdir(snapshot):
                    sp = os.path.join(snapshot, f)
                    if os.path.isfile(sp):
                        shutil.copy2(sp, os.path.join(ws, f))
                    elif os.path.isdir(sp):
                        shutil.copytree(sp, os.path.join(ws, f), dirs_exist_ok=True)

        # Simple consistency check: do answers agree?
        if len(set(a[:200] for a in answers)) == 1:
            self._emit("code", f"Self-Consistency: {n}/{n} 次结果一致 ✗")
            # Run once more to apply changes
            self.coder.reset()
            self.coder.run(
                task=f"按照以下方案执行代码修改：\n{plan_text}",
                context=context,
            )
            return self.coder.final_answer
        else:
            self._emit("code", f"Self-Consistency: {n} 次结果存在分歧，选取最详细方案")
            # Pick the longest (most detailed) answer
            return max(answers, key=len)

    @staticmethod
    def _load_stats() -> str:
        try:
            import json
            data_dir = os.path.join(os.path.dirname(__file__), "data")
            path = os.path.join(data_dir, "fix_patterns.json")
            with open(path, "r", encoding="utf-8") as f:
                stats = json.load(f)
            sorted_cats = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)
            lines = [
                "\n## 统计知识（来自2000个历史bug分析）",
                "常见bug类型及修复模式分布：",
            ]
            for cat, s in sorted_cats:
                lines.append(f"  - {cat}: {s['pct']}% ({s['count']}例)")
            lines.append("制定方案时优先对照以上常见类型。")
            return "\n".join(lines)
        except Exception:
            return ""

    def _emit(self, phase: str, msg: str) -> None:
        if self.on_progress:
            self.on_progress(phase, msg)

    def _get_rag_context(self, task: str) -> str:
        if not self.use_rag:
            return ""
        try:
            from rag.retriever import set_paths, retrieve, format_few_shot
            data_dir = os.path.join(os.path.dirname(__file__), "data")
            set_paths(data_dir)
            examples = retrieve(task, k=3)
            return format_few_shot(examples)
        except Exception:
            return ""

    def run(self, task: str, max_review_rounds: int = 2) -> dict:
        """Execute the agent pipeline. Reviewer may trigger rework."""
        self.trace = []

        # --- Plan phase ---
        self._emit("plan", "启动规划Agent...")
        if self.planner is not None:
            rag_ctx = self._get_rag_context(task)
            plan_prompt = f"分析以下任务需求，制定修改方案：\n{task}"
            if rag_ctx:
                plan_prompt = rag_ctx + "\n" + plan_prompt
            plan_steps = self.planner.run(task=plan_prompt)
            plan_text = self.planner.final_answer
            self.trace.append({"phase": "plan", "steps": plan_steps, "output": plan_text})
            self._emit("plan", "规划完成")
        else:
            plan_text = f"直接执行任务：{task}"
            self.trace.append({"phase": "plan", "steps": [], "output": plan_text})

        # --- Code + Review loop ---
        review_text = ""
        for round_num in range(max_review_rounds):
            # Code phase (with optional self-consistency)
            self._emit("code", f"启动编码Agent (第{round_num+1}轮)...")
            code_context = ""
            if round_num > 0 and review_text:
                code_context = f"上一轮审查反馈：\n{review_text}"

            if self.self_consistency > 1 and round_num == 0:
                # Self-consistency: run coder N times, pick majority
                code_text = self._run_self_consistency(plan_text, code_context)
                code_steps = []
            else:
                code_steps = self.coder.run(
                    task=f"按照以下方案执行代码修改：\n{plan_text}",
                    context=code_context,
                )
                code_text = self.coder.final_answer

            self.trace.append({
                "phase": f"code_round{round_num+1}",
                "steps": code_steps,
                "output": code_text,
            })
            self._emit("code", "编码完成")

            # Review phase (skip if no reviewer)
            if self.reviewer is None:
                return {
                    "success": True,
                    "trace": self.trace,
                    "plan": plan_text,
                    "code": code_text,
                    "review": "(no reviewer)",
                }

            self._emit("review", "启动审查Agent...")
            review_steps = self.reviewer.run(
                task=f"审查以下任务的修改是否正确：\n原始任务：{task}\n规划方案：{plan_text}\n编码结果：{code_text}",
            )
            review_text = self.reviewer.final_answer
            self.trace.append({
                "phase": f"review_round{round_num+1}",
                "steps": review_steps,
                "output": review_text,
            })
            self._emit("review", "审查完成")

            if "审查通过" in review_text or "通过" in review_text:
                return {
                    "success": True,
                    "trace": self.trace,
                    "plan": plan_text,
                    "code": code_text,
                    "review": review_text,
                }

        return {
            "success": False,
            "trace": self.trace,
            "plan": plan_text,
            "code": code_text,
            "review": review_text,
        }
