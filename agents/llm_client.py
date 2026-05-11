"""DeepSeek API wrapper with OpenAI-compatible function calling."""

import json
import os
import re
from openai import OpenAI

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

_client = None

# Regex to match lone surrogates that break JSON encoding
_SURROGATE_RE = re.compile(r'[\ud800-\udfff]')


def _sanitize_str(s: str) -> str:
    """Remove lone surrogate characters that break JSON encoding."""
    return _SURROGATE_RE.sub('�', s)


def _sanitize(obj):
    """Recursively sanitize all strings in a nested structure."""
    if isinstance(obj, str):
        return _sanitize_str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


def chat_with_tools(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """Send a chat completion request with optional tool definitions."""
    client = get_client()
    clean_messages = _sanitize(messages)
    clean_tools = _sanitize(tools) if tools else None
    kwargs = dict(
        model=model,
        messages=clean_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if clean_tools:
        kwargs["tools"] = clean_tools
    response = client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    msg = choice.message
    result = {
        "role": "assistant",
        "content": msg.content,
        "finish_reason": choice.finish_reason,
    }
    if msg.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc.id,
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    return result


def execute_tool_calls(tool_calls: list[dict], tool_functions: dict) -> list[dict]:
    """Execute tool calls and return result messages."""
    results = []
    for tc in tool_calls:
        name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"]["arguments"])
        except json.JSONDecodeError:
            args = {}
        fn = tool_functions.get(name)
        if fn is None:
            result = {"success": False, "error": f"Unknown tool: {name}"}
        else:
            try:
                result = fn(**args)
            except TypeError as e:
                result = {"success": False, "error": f"Tool argument error: {e}"}
        # Sanitize before serializing to avoid surrogate issues
        clean = _sanitize(result)
        results.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": json.dumps(clean, ensure_ascii=False),
        })
    return results
