from __future__ import annotations

import unittest

from ada.ports.calendar import CalendarPort
from caldav_test_support import build_adapter, build_fake_server
from calendar_port_contract import CalendarPortContractTests


class CalDAVCalendarContractTests(CalendarPortContractTests, unittest.TestCase):
    """The generic CalDAV adapter must pass the same contract as every adapter.

    ADR-0009 section 2: "Every adapter and profile must pass a shared
    CalendarPort contract test suite."
    """

    def make_calendar(self) -> CalendarPort:
        server = build_fake_server()
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)
        return adapter


if __name__ == "__main__":
    unittest.main()
