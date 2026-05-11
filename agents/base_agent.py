"""Base Agent with ReAct loop and Tool Use capability."""

import json
from agents.llm_client import chat_with_tools, execute_tool_calls
from tools import TOOLS_SCHEMA, TOOL_FUNCTIONS


MAX_ITERATIONS = 5


class BaseAgent:
    """Generic ReAct agent that can call tools to complete tasks."""

    def __init__(self, name: str, system_prompt: str, tools: list[str] | None = None,
                 on_progress=None):
        self.name = name
        self.system_prompt = system_prompt
        self.tool_names = tools or []
        self.on_progress = on_progress
        self.history: list[dict] = []

    @property
    def tools_schema(self) -> list[dict]:
        if not self.tool_names:
            return None
        return [t for t in TOOLS_SCHEMA if t["function"]["name"] in self.tool_names]

    @property
    def tool_functions(self) -> dict:
        return {k: v for k, v in TOOL_FUNCTIONS.items() if k in self.tool_names}

    def reset(self) -> None:
        self.history = []

    def run(self, task: str, context: str = "") -> list[dict]:
        """Execute ReAct loop: think → act → observe → repeat."""
        self.history = [
            {"role": "system", "content": self.system_prompt},
        ]
        if context:
            self.history.append({"role": "user", "content": f"上下文信息:\n{context}"})
        self.history.append({"role": "user", "content": task})

        steps = []
        for _ in range(MAX_ITERATIONS):
            response = chat_with_tools(
                messages=self.history,
                tools=self.tools_schema,
            )

            # Record step
            step = {
                "agent": self.name,
                "thought": response.get("content", ""),
                "tool_calls": [],
                "tool_results": [],
            }

            # Handle tool calls
            if response.get("tool_calls"):
                for tc in response["tool_calls"]:
                    if self.on_progress:
                        name = tc["function"]["name"]
                        args = tc["function"]["arguments"]
                        self.on_progress(self.name, f"📎 {name}({args[:80]})")
                step["tool_calls"] = response["tool_calls"]
                self.history.append({
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": tc["function"],
                        }
                        for tc in response["tool_calls"]
                    ],
                })

                # Execute tools
                tool_results = execute_tool_calls(response["tool_calls"], self.tool_functions)
                step["tool_results"] = [
                    {"tool_call_id": tr["tool_call_id"], "content": tr["content"]}
                    for tr in tool_results
                ]
                self.history.extend(tool_results)
            else:
                self.history.append({"role": "assistant", "content": response.get("content")})

            steps.append(step)

            # Stop if no more tool calls
            if not response.get("tool_calls"):
                break

        return steps

    @property
    def final_answer(self) -> str:
        for msg in reversed(self.history):
            if msg["role"] == "assistant" and msg.get("content"):
                return msg["content"]
        return ""
