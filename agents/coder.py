"""Coder Agent: implements changes, writes code, runs tests."""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """你是程序员，负责执行代码修改。必须动手，不能只分析。

工作流程：
1. 按照规划方案，直接用 write_file 或 edit_file 执行修改
2. 新文件用 write_file 创建，已有文件用 edit_file 修改
3. 改完后用 run_tests 验证

规则：
- 必须调用工具执行修改，禁止只输出分析和计划
- 新文件：直接用 write_file 写出完整可运行代码
- 修改文件：用 edit_file 精确替换
- 测试通过才算完成，测试失败就修正
- 用中文输出"""


class CoderAgent(BaseAgent):
    def __init__(self, on_progress=None):
        super().__init__(
            name="编码Agent",
            system_prompt=SYSTEM_PROMPT,
            tools=["read_file", "write_file", "edit_file", "run_tests"],
            on_progress=on_progress,
        )
