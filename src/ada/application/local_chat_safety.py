from __future__ import annotations


def render_conversation_only_reply(text: str) -> str:
    """Render model text without allowing it to serve as action truth.

    The current local-chat slice cannot execute external actions. Raw model text
    is therefore always explicitly marked as conversational content; only Ada's
    structured draft/proposal/outcome channels may describe authoritative action
    state.
    """

    return (
        f"{text}\n"
        "[Conversation only: no external action was executed in this turn.]"
    )
