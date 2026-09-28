from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import httpx2
from dbos import DBOS, DBOSConfig

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.profile import IONOS_PROFILE
from ada.adapters.dbos_durable_actions import DBOSDurableCalendarActions
from ada.core.action_outcomes import (
    AuthorizationEvidence,
    BusinessOutcomeStatus,
    OperationId,
    ProviderOutcomeStatus,
)
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.durable_action import DurableCalendarCreate
from caldav_test_support import BASE_URL, FAKE_AUTH, build_fake_server, default_family_ref


def _proposal() -> CreateCalendarEventProposal:
    return CreateCalendarEventProposal(
        title="Parent-teacher meeting",
        start=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 12, 16, 30, tzinfo=timezone.utc),
        calendar_id="family",
        location="School North",
    )


class CalDAVCreateDurableActionTests(unittest.TestCase):
    """Proves the DBOS durable-action layer does not reinterpret an
    already-known provider commit as ambiguous merely because CalDAV
    read-back metadata is unavailable (ADR-0009 section 6: any 2xx status is
    success).
    """

    _counter = 0

    def setUp(self) -> None:
        type(self)._counter += 1
        self.tmp = tempfile.TemporaryDirectory()
        DBOS.destroy()
        config: DBOSConfig = {
            "name": f"ada-caldav-durable-test-{self._counter}",
            "application_version": "test",
            "run_admin_server": False,
            "log_level": "WARNING",
            "console_log_level": "WARNING",
            "system_database_url": (
                f"sqlite:///{Path(self.tmp.name) / 'dbos.sqlite'}"
            ),
        }
        DBOS(config=config)

    def tearDown(self) -> None:
        DBOS.destroy()
        self.tmp.cleanup()

    def test_read_back_failure_after_2xx_still_reports_committed_end_to_end(
        self,
    ) -> None:
        server = build_fake_server()

        def dispatch(request: httpx2.Request) -> httpx2.Response:
            if request.method == "GET":
                raise httpx2.ReadTimeout("simulated failure reading back the event")
            return server(request)

        calendar = CalDAVCalendarAdapter(
            base_url=BASE_URL,
            auth=FAKE_AUTH,
            calendars=(default_family_ref(),),
            profile=IONOS_PROFILE,
            transport=httpx2.MockTransport(dispatch),
        )
        self.addCleanup(calendar.close)

        durable = DBOSDurableCalendarActions(
            calendar,
            instance_name=f"calendar-actions-caldav-durable-{self._counter}",
        )
        DBOS.launch()

        request = DurableCalendarCreate(
            operation_id=OperationId("op-caldav-readback-fails-durable"),
            proposal=_proposal(),
            authorization=AuthorizationEvidence(
                policy_version="test-policy-v1",
                matched_rule_ids=("grant-family-calendar",),
            ),
        )

        result = durable.create_calendar_event(request)

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.COMMITTED)
        self.assertEqual(result.business.status, BusinessOutcomeStatus.COMMITTED)


if __name__ == "__main__":
    unittest.main()
