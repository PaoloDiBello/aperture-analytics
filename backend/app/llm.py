"""OpenRouter (OpenAI-compatible) chat client with tool calling support.

Uses httpx directly rather than the openai SDK to keep dependencies minimal
and to give us full control over streaming. The base URL defaults to
OpenRouter so we can use free/low-cost models during development.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from .config import settings


class LLMError(Exception):
    pass


class ToolCall:
    def __init__(self, id: str, name: str, arguments: Dict[str, Any]):
        self.id = id
        self.name = name
        self.arguments = arguments

    def to_message(self, result: str) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": self.id,
            "content": result,
        }


class ChatMessage:
    def __init__(
        self,
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
    ):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        return d


class LLMClient:
    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            raise LLMError("OPENROUTER_API_KEY is not set.")
        self.headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send a chat completion; yields SSE-ish text fragments when streaming.

        When not streaming, this yields a single final content string.
        """
        payload: Dict[str, Any] = {
            "model": settings.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": stream,
        }
        if not stream:
            payload.pop("stream")

        async with httpx.AsyncClient(timeout=120) as client:
            if stream:
                async with client.stream(
                    "POST",
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise LLMError(f"LLM error {response.status_code}: {body.decode()}")
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        text = delta.get("content")
                        if text:
                            yield text
            else:
                response = await client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                if response.status_code != 200:
                    raise LLMError(f"LLM error {response.status_code}: {response.text}")
                data = response.json()
                choices = data.get("choices")
                if not choices:
                    err = data.get("error") or data
                    raise LLMError(f"LLM returned no completion: {err}")
                content = choices[0].get("message", {}).get("content") or ""
                yield content

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        executor: Any,
        max_rounds: int = 3,
    ) -> Dict[str, Any]:
        """Run the agent loop: let the model call tools, execute them, and
        feed results back until it produces a final text answer.

        Returns the final assistant message (text) after the tool loop.
        """
        working = list(messages)

        for _ in range(max_rounds):
            content_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []

            # Fetch the complete assistant message (may include tool_calls).
            response_data = await self._complete(working, tools)
            msg = response_data["choices"][0]["message"]
            content = msg.get("content")
            calls_raw = msg.get("tool_calls")

            if calls_raw:
                assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content}
                parsed_calls: List[ToolCall] = []
                tc_list = []
                for c in calls_raw:
                    fn = c.get("function", {})
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    tc = ToolCall(c.get("id", ""), fn.get("name", ""), args)
                    parsed_calls.append(tc)
                    tc_list.append(
                        {
                            "id": c.get("id", ""),
                            "type": "function",
                            "function": {"name": fn.get("name", ""), "arguments": json.dumps(args)},
                        }
                    )
                assistant_msg["tool_calls"] = tc_list
                working.append(assistant_msg)

                for tc in parsed_calls:
                    result = executor.execute(tc.name, tc.arguments)
                    working.append(tc.to_message(json.dumps(result)))
                continue

            # No tool calls -> final answer
            return {"content": content or "", "tool_calls": calls_raw or []}

        return {"content": "I could not produce a complete answer within the allowed steps.", "tool_calls": []}

    async def _complete(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], max_retries: int = 3) -> Dict[str, Any]:
        """Send a non-streamed chat completion, returning the full response.

        Free OpenRouter models are frequently rate-limited or overloaded
        (HTTP 429 / "Service temporarily overloaded"), so we retry transient
        failures with a short backoff. Permanent errors (bad model, auth) are
        raised immediately.
        """
        import asyncio

        payload: Dict[str, Any] = {
            "model": settings.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=120) as client:
            last_error: Optional[str] = None
            for attempt in range(max_retries + 1):
                try:
                    response = await client.post(
                        f"{settings.openrouter_base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                except httpx.HTTPError as e:
                    last_error = f"network error: {e}"
                    retryable = True
                else:
                    try:
                        data = response.json()
                    except ValueError:
                        data = {}
                        last_error = f"invalid JSON body: {response.text[:200]}"
                        retryable = False
                    else:
                        error_obj = data.get("error") if isinstance(data, dict) else None
                        if response.status_code == 200 and not error_obj:
                            if "choices" not in data:
                                last_error = f"unexpected payload: {response.text[:200]}"
                                retryable = False
                            else:
                                return data
                        else:
                            message = (
                                error_obj.get("message") if isinstance(error_obj, dict) else ""
                            ) or response.text
                            last_error = f"HTTP {response.status_code}: {message[:250]}"
                            # 429 (rate limit) and 5xx (overload) are transient.
                            retryable = response.status_code in (429, 500, 502, 503, 504)

                if retryable and attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise LLMError(f"LLM error: {last_error}")

        raise LLMError(f"LLM error: {last_error}")
