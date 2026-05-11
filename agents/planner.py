"""Planner Agent: reads code, analyzes problems, proposes solutions."""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """你是软件架构师，负责阅读代码、分析问题、制定修改方案。

工作流程：
1. 如果工作区已有代码，用 read_file 阅读后再制定方案
2. 如果工作区是空的（read_file "." 返回空列表），直接根据任务描述制定方案
3. 制定清晰、可执行的方案

规则：
- 创建新文件的任务：不需要先读文件，直接给出文件名和完整代码结构
- 修改已有代码：必须先读文件再制定方案
- 方案要具体到文件名、函数名、关键代码逻辑
- 输出格式：先描述要做什么 → 再给出具体方案 → 最后列出需要创建/修改的文件
- 用中文输出，方案要简洁让编码Agent能直接执行"""


class PlannerAgent(BaseAgent):
    def __init__(self, on_progress=None, stats: str = ""):
        prompt = SYSTEM_PROMPT
        if stats:
            prompt += "\n" + stats
        super().__init__(
            name="规划Agent",
            system_prompt=prompt,
            tools=["read_file"],
            on_progress=on_progress,
        )
