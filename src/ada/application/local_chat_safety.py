from __future__ import annotations


def sanitize_terminal_text(text: str) -> str:
    """Neutralize terminal control characters in untrusted model output.

    Preserve ordinary text plus newlines/tabs, but remove C0/C1 controls such
    as ESC, backspace, carriage return, BEL, and DEL. Removing ESC is enough to
    make ANSI/OSC control sequences inert before Ada appends trusted status text.
    """

    return "".join(
        char
        for char in text
        if char in {"\n", "\t"}
        or (
            ord(char) >= 0x20
            and not 0x7F <= ord(char) <= 0x9F
        )
    )


def render_conversation_only_reply(text: str) -> str:
    """Render model text without allowing it to serve as action truth.

    The current local-chat slice cannot execute external actions. Raw model text
    is therefore always explicitly marked as conversational content; only Ada's
    structured draft/proposal/outcome channels may describe authoritative action
    state.
    """

    safe_text = sanitize_terminal_text(text)
    return (
        f"{safe_text}\n"
        "[Conversation only: no external action was executed in this turn.]"
    )
