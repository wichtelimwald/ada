from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from collections.abc import Callable

from ada import __version__
from ada.application.calendar_drafts import render_calendar_draft_response
from ada.application.local_chat_safety import render_conversation_only_reply
from ada.core.actions import CreateCalendarEventDraft
from ada.ports.agent_runtime import AgentRequest, AgentRuntimePort


def _doctor() -> int:
    payload = {
        "status": "ok",
        "ada_version": __version__,
        "python": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def _chat_loop(
    runtime: AgentRuntimePort,
    *,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> int:
    write("Ada local chat. Type /reset to clear this session or /quit to exit.")

    while True:
        try:
            text = read("you> ").strip()
        except EOFError:
            return 0

        if not text:
            continue
        if text in {"/quit", "/exit"}:
            return 0
        if text == "/reset":
            reset_session = getattr(runtime, "reset_session", None)
            if callable(reset_session):
                reset_session()
                write("Ada: Session context cleared.")
            else:
                write("Ada: This runtime has no session context to clear.")
            continue

        try:
            response = runtime.run(AgentRequest(text=text))
        except Exception as exc:
            write(
                "Ada: I could not reliably process that request. "
                "No action was executed."
            )
            if os.getenv("ADA_DEBUG"):
                print(f"debug: {exc}", file=sys.stderr)
            continue

        if response.text:
            write(f"Ada: {render_conversation_only_reply(response.text)}")
        for draft in response.drafts:
            if isinstance(draft, CreateCalendarEventDraft):
                write(f"Ada: {render_calendar_draft_response(draft, source_text=text)}")
            else:
                write(
                    "Ada: I formed an incomplete action draft, but nothing "
                    "was executed."
                )
        if response.proposals:
            write(
                "Ada: I formed an action proposal, but this local-chat slice "
                "does not execute proposals yet."
            )


def _chat(*, model: str, ollama_url: str) -> int:
    from ada.adapters.local_ollama import (
        LocalModelConfigurationError,
        LocalModelUnavailableError,
        LocalOllamaConfig,
        build_local_ollama_runtime,
        check_local_ollama_ready,
    )

    config = LocalOllamaConfig(model=model, base_url=ollama_url)
    try:
        check_local_ollama_ready(config)
        runtime = build_local_ollama_runtime(config)
    except (LocalModelConfigurationError, LocalModelUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        return _chat_loop(runtime)
    except KeyboardInterrupt:
        print()
        return 130
    except Exception as exc:
        print(f"error: local model request failed: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ada",
        description="Ada local-first personal assistant",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "doctor",
        help="Print a local scaffold/runtime sanity check.",
    )

    chat = subparsers.add_parser(
        "chat",
        help="Start an ephemeral local text chat through Ollama.",
    )
    chat.add_argument(
        "--model",
        default=os.getenv("ADA_OLLAMA_MODEL", "qwen3.5:9b"),
        help="Local Ollama model name (default: qwen3.5:9b).",
    )
    chat.add_argument(
        "--ollama-url",
        default=os.getenv(
            "ADA_OLLAMA_BASE_URL",
            "http://localhost:11434/v1",
        ),
        help="Loopback Ollama OpenAI-compatible /v1 endpoint.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "doctor":
        raise SystemExit(_doctor())
    if args.command == "chat":
        raise SystemExit(
            _chat(
                model=args.model,
                ollama_url=args.ollama_url,
            )
        )

    parser.print_help()
    raise SystemExit(0)


if __name__ == "__main__":
    main()
