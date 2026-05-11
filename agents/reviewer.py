"""Reviewer Agent: checks diffs, validates correctness, enforces quality."""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """你是代码审查者，负责检查修改是否合格。

工作流程：
1. 使用 get_diff 查看修改内容
2. 使用 read_file 阅读被修改的文件
3. 从以下维度审查：
   - 逻辑正确性：修改是否解决了问题
   - 副作用：是否引入了新问题
   - 代码风格：是否符合项目风格
   - 测试覆盖：测试是否覆盖了边界情况

规则：
- 必须同时看 diff 和源文件
- 如果发现错误，清楚描述问题并要求修正
- 如果审查通过，明确输出 "审查通过 ✓"
- 用中文输出"""


class ReviewerAgent(BaseAgent):
    def __init__(self, on_progress=None):
        super().__init__(
            name="审查Agent",
            system_prompt=SYSTEM_PROMPT,
            tools=["get_diff", "read_file", "run_tests"],
            on_progress=on_progress,
        )
