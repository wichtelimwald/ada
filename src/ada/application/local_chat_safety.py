from __future__ import annotations

import re

from ada.ports.agent_runtime import AgentResponse


_CALENDAR_CONTEXT_RE = re.compile(
    r"\b(?:kalender|calendar|termin|appointment|event|ereignis)\b",
    re.IGNORECASE,
)

_COMPLETION_CLAIM_RE = re.compile(
    r"(?:"
    r"\b(?:ich\s+habe|ich\s+hab|i\s+have|i've)\b"
    r"[^.!?\n]{0,120}"
    r"\b(?:eingetragen|hinzugefügt|erstellt|angelegt|gespeichert|gebucht|"
    r"geändert|gelöscht|added|created|scheduled|saved|booked|changed|deleted)\b"
    r"|"
    r"\b(?:termin|appointment|event|ereignis|kalendereintrag|calendar\s+entry)\b"
    r"[^.!?\n]{0,80}"
    r"\b(?:ist|wurde|has\s+been|was|is\s+now)\b"
    r"[^.!?\n]{0,60}"
    r"\b(?:eingetragen|hinzugefügt|erstellt|angelegt|gespeichert|gebucht|"
    r"geändert|gelöscht|added|created|scheduled|saved|booked|changed|deleted)\b"
    r"|"
    r"^\s*(?:done|erledigt|fertig)\s*[.!]?$"
    r")",
    re.IGNORECASE,
)


def enforce_local_chat_action_truth(
    *,
    request_text: str,
    response: AgentResponse,
) -> AgentResponse:
    """Block unverified calendar-action completion claims in local chat.

    The current local-chat slice does not execute external actions. Therefore a
    free-text completion claim about a calendar action can never be authoritative.
    Typed drafts/proposals remain separate and are preserved unchanged.
    """

    if not response.text:
        return response

    context = f"{request_text}\n{response.text}"
    if not _CALENDAR_CONTEXT_RE.search(context):
        return response
    if not _COMPLETION_CLAIM_RE.search(response.text):
        return response

    return AgentResponse(
        text=(
            "I cannot confirm that calendar action as completed. "
            "No calendar action was executed."
        ),
        drafts=response.drafts,
        proposals=response.proposals,
    )
