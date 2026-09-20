from __future__ import annotations

import re

from ada.ports.agent_runtime import AgentResponse


_CALENDAR_CONTEXT_RE = re.compile(
    r"(?:\bkalender\b|\bcalendar\b|\b\w*termin\b|\bappointment\b|"
    r"\bevent\b|\bereignis\b)",
    re.IGNORECASE,
)

_CALENDAR_ACTION_RE = re.compile(
    r"(?:"
    r"\beintragen\b|\beingetragen\b|\bhinzufügen\b|\bhinzugefügt\b|"
    r"\berstellen\b|\berstellt\b|\banlegen\b|\bangelegt\b|"
    r"\bspeichern\b|\bgespeichert\b|\bbuchen\b|\bgebucht\b|"
    r"\bändern\b|\bgeändert\b|\blöschen\b|\bgelöscht\b|"
    r"\bverschieben\b|\bverschoben\b|\bplanen\b|\bgeplant\b|"
    r"\badd\b|\badded\b|\bcreate\b|\bcreated\b|"
    r"\bschedule\b|\bscheduled\b|\bsave\b|\bsaved\b|"
    r"\bbook\b|\bbooked\b|\bchange\b|\bchanged\b|"
    r"\bdelete\b|\bdeleted\b|\bremove\b|\bremoved\b|"
    r"\bmove\b|\bmoved\b|\bupdate\b|\bupdated\b"
    r")",
    re.IGNORECASE,
)


def _is_calendar_action_request(request_text: str) -> bool:
    return bool(
        _CALENDAR_CONTEXT_RE.search(request_text)
        and _CALENDAR_ACTION_RE.search(request_text)
    )


def enforce_local_chat_action_truth(
    *,
    request_text: str,
    response: AgentResponse,
) -> AgentResponse:
    """Fail closed when a calendar action request produces free model text.

    The current local-chat slice does not execute external actions. A calendar
    action request must therefore become a typed draft/proposal path. If the
    model instead returns free text, Ada must not trust or forward any claimed
    status, including phrasings a deny-list did not anticipate.
    """

    if not response.text or not _is_calendar_action_request(request_text):
        return response

    return AgentResponse(
        text=(
            "I could not safely turn that calendar action request into a "
            "typed draft. No calendar action was executed."
        ),
        drafts=response.drafts,
        proposals=response.proposals,
    )
