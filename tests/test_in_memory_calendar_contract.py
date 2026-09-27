from __future__ import annotations

import unittest

from ada.adapters.in_memory_calendar import InMemoryCalendarAdapter
from ada.ports.calendar import CalendarPort
from calendar_port_contract import CalendarPortContractTests


class InMemoryCalendarContractTests(CalendarPortContractTests, unittest.TestCase):
    def make_calendar(self) -> CalendarPort:
        return InMemoryCalendarAdapter()


if __name__ == "__main__":
    unittest.main()
