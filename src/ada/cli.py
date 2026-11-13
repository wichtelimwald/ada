from __future__ import annotations

import asyncio
import argparse
import json
import os
import platform
import sys
from collections.abc import Callable
from contextlib import ExitStack

from ada import __version__
from ada.adapters.file_memory import FileMemoryError, FileMemoryStore
from ada.bootstrap.personality import bootstrap_personality_memory
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


def _chat(
    *,
    model: str,
    ollama_url: str,
    memory_root: str | None = None,
    unlock_vault: bool = False,
    vault_root: str | None = None,
) -> int:
    from ada.adapters.local_ollama import (
        LocalModelConfigurationError,
        LocalModelUnavailableError,
        LocalOllamaConfig,
        build_local_ollama_runtime,
        check_local_ollama_ready,
    )

    from ada.adapters.kdbx_secrets import SecretVaultError

    config = LocalOllamaConfig(model=model, base_url=ollama_url)
    normalized_memory_root = (
        memory_root.strip()
        if isinstance(memory_root, str) and memory_root.strip()
        else None
    )
    try:
        personality = None
        if normalized_memory_root is not None:
            memory = FileMemoryStore(normalized_memory_root)
            personality = bootstrap_personality_memory(memory)

        check_local_ollama_ready(config)
    except (LocalModelConfigurationError, LocalModelUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except FileMemoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Keep the decrypted vault in the same process as the chat session.
    # It is deliberately NOT passed to the agent/model runtime as a tool.
    with ExitStack() as resources:
        if unlock_vault:
            location = vault_root or normalized_memory_root
            if not location:
                print(
                    "error: --unlock-vault requires --vault-root or --memory-root",
                    file=sys.stderr,
                )
                return 2
            try:
                resources.enter_context(_unlock_vault(location))
            except SecretVaultError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2

        try:
            runtime = build_local_ollama_runtime(
                config,
                personality=personality,
            )
        except (LocalModelConfigurationError, LocalModelUnavailableError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        # The vault is closed AFTER model runtime cleanup, including /quit,
        # EOF, an interrupt or any request-loop failure.
        with asyncio.Runner() as runner:
            runner.get_loop()
            try:
                return _chat_loop(runtime)
            except KeyboardInterrupt:
                print()
                return 130
            except Exception as exc:
                print(f"error: local model request failed: {exc}", file=sys.stderr)
                return 1
            finally:
                try:
                    runner.run(runtime.aclose())
                except Exception as exc:
                    print(f"warning: local model cleanup failed: {exc}", file=sys.stderr)


def _unlock_vault(vault_root: str):
    """Unlock only from a trusted local terminal, never from model input."""
    from getpass import GetPassWarning, getpass
    from warnings import catch_warnings, simplefilter
    from ada.adapters.kdbx_secrets import (
        KdbxSecrets,
        SecretVaultError,
        protect_credential_process,
    )

    if not sys.stdin.isatty():
        raise SecretVaultError("Ada vault unlock requires an interactive terminal")
    # Defense against same-UID /proc memory readers: fail before the prompt.
    protect_credential_process()
    vault = KdbxSecrets(vault_root)
    try:
        # getpass falls back to visible stdin when terminal echo cannot be
        # disabled. A password prompt must fail closed instead.
        with catch_warnings():
            simplefilter("error", GetPassWarning)
            passphrase = getpass("Ada vault passphrase: ")
    except (EOFError, KeyboardInterrupt, OSError, GetPassWarning):
        raise SecretVaultError("Ada vault unlock cancelled") from None

    try:
        vault.unlock(passphrase)
    finally:
        del passphrase
    return vault


def _secrets_check(memory_root: str) -> int:
    """Interactive one-shot PoC; does not unlock a different Ada process."""
    from ada.adapters.kdbx_secrets import SecretVaultError

    try:
        with _unlock_vault(memory_root):
            print("Ada vault unlocked for this check; now locked again.")
        return 0
    except SecretVaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


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
    chat.add_argument(
        "--memory-root",
        default=os.getenv("ADA_MEMORY_ROOT") or None,
        help=(
            "Development-only file-native Memory root; do not use real household "
            "data until protected domains are implemented."
        ),
    )
    chat.add_argument(
        "--unlock-vault",
        action="store_true",
        help="Experimental: require a terminal passphrase and keep Ada's KDBX "
             "vault unlocked only during this chat process.",
    )
    chat.add_argument(
        "--vault-root",
        default=os.getenv("ADA_VAULT_ROOT") or None,
        help="Root holding secrets/ada.kdbx; defaults to --memory-root.",
    )
    secret_check = subparsers.add_parser(
        "secrets-check",
        help="Experimental: interactively unlock and close an Ada-only KDBX vault.",
    )
    secret_check.add_argument(
        "--memory-root",
        required=True,
        help="Persistent Ada Memory root holding secrets/ada.kdbx.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "doctor":
        raise SystemExit(_doctor())
    if args.command == "secrets-check":
        raise SystemExit(_secrets_check(args.memory_root))
    if args.command == "chat":
        raise SystemExit(
            _chat(
                model=args.model,
                ollama_url=args.ollama_url,
                memory_root=args.memory_root,
                unlock_vault=args.unlock_vault,
                vault_root=args.vault_root,
            )
        )

    parser.print_help()
    raise SystemExit(0)


if __name__ == "__main__":
    main()
