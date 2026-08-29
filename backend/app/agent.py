"""The AI agent: builds the context, runs the tool loop, and assembles a
structured answer.

The agent's prompt includes the dataset context block (shape, columns, types,
missing values, sample rows) so the model knows what data is available, but
it cannot see raw full data — it must use tools to compute anything concrete.
This is a core anti-hallucination choice: the model reasons over the schema
and uses tools to get real numbers.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .frame import Dataframe
from .llm import LLMClient
from .tools import TOOL_DEFINITIONS, ToolExecutor

SYSTEM_PROMPT = """You are a precise artificial-intelligence agent that answers \
questions about a dataset the user has uploaded. Your job is to reason over real \
data using the tools you have been given — not to guess.

You have access to a set of tools. ALWAYS use tools to compute facts — never \
invent numbers, columns, or rows. If you do not know the answer from the data, \
say so clearly rather than guessing.

Rules:
- First understand the dataset with analyze_data before answering specifics.
- For any numeric claim ("top product", "total revenue", "average price"), \
compute it with the calculate tool and use the returned number verbatim.
- If a chart would help, use the chart tool and pass through the data rows \
from your calculate result unchanged.
- Be concise. Structure your answer as plain text with short markdown bullets \
where useful.
- If a requested metric isn't possible with the available columns, explain why.

The user is asking about the dataset described in the system context."""


async def run_agent(llm: LLMClient, df: Dataframe, question: str) -> Dict[str, Any]:
    executor = ToolExecutor(df)
    context = df.context_block()

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Dataset context:\n{context}"},
        {"role": "user", "content": question},
    ]

    result = await llm.chat_with_tools(messages, TOOL_DEFINITIONS, executor)
    return result
