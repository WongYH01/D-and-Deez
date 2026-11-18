"""Claude client: send a request, optionally stream text deltas, return the final message.

`AnthropicClient` wraps the Anthropic SDK; tests use a scripted fake with the same `send`.
The API key comes from the environment (ANTHROPIC_API_KEY) and is never logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from d_and_deez.config import env


@dataclass
class Usage:
    input_tokens: int = 0  # all input, cached or not
    output_tokens: int = 0
    cached_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cached_tokens += other.cached_tokens


@dataclass
class Reply:
    content: list[dict]  # content blocks as plain dicts (text, thinking, tool_use, ...)
    stop_reason: str
    usage: Usage = field(default_factory=Usage)


class ClaudeError(Exception):
    def __init__(self, message: str, usage: Usage | None = None):
        super().__init__(message)
        self.usage = usage or Usage()


class ClaudeClient(Protocol):
    def send(self, *, system: str | list[dict], messages: list[dict], tools: list[dict], tools_enabled: bool,
             on_text: Callable[[str], None] | None, force_tool: str | None = None) -> Reply: ...


DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_RECAP_MODEL = "claude-haiku-5-5"


def plan_client() -> "AnthropicClient":
    """The client that writes Campaign bibles; DND_PLAN_MODEL lets Opus be compared without a code change."""
    return AnthropicClient(model=env("PLAN_MODEL", DEFAULT_MODEL))


def recap_client() -> "AnthropicClient":
    """The client that writes Recaps; DND_RECAP_MODEL trades cost for quality without a code change."""
    return AnthropicClient(model=env("RECAP_MODEL", DEFAULT_RECAP_MODEL), max_tokens=2000)


class AnthropicClient:
    def __init__(self, model: str | None = None, max_tokens: int = 16000, max_retries: int = 4):
        import anthropic

        self.model = model or env("MODEL", DEFAULT_MODEL)
        self.max_tokens = max_tokens
        # The SDK retries 429, 5xx and connection errors with exponential backoff.
        self.client = anthropic.Anthropic(max_retries=max_retries)

    def send(self, *, system, messages, tools, tools_enabled, on_text=None, force_tool=None) -> Reply:
        import anthropic

        # Tools stay in the request (stable prefix) but can't be called on the narration-only call.
        # force_tool stays "auto": Sonnet 5.5 rejects forced tool_choice with a 400, so the system prompt names the
        # tool and the caller retries when no call comes back.
        tool_args = {"tools": tools, "tool_choice": {"type": "auto" if tools_enabled or force_tool else "none"}} if tools else {}
        try:
            with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=messages,
                **tool_args,
                # Server-side fallback when a request is declined (refusal stop reason).
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                if on_text:
                    for text in stream.text_stream:
                        on_text(text)
                msg = stream.get_final_message()
        except anthropic.APIError as e:
            raise ClaudeError(f"Claude API error: {type(e).__name__}") from e
        u = msg.usage
        cached = u.cache_read_input_tokens or 0
        usage = Usage(
            input_tokens=u.input_tokens + cached + (u.cache_creation_input_tokens or 0),
            output_tokens=u.output_tokens,
            cached_tokens=cached,
        )
        if msg.stop_reason == "refusal":
            raise ClaudeError("Claude declined this request.", usage)
        return Reply(content=[b.to_dict() for b in msg.content], stop_reason=msg.stop_reason, usage=usage)
