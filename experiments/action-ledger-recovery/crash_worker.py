from __future__ import annotations

import os
import sys
from pathlib import Path

from ledger import Ledger
from provider import FakeProvider


ledger = Ledger(Path(sys.argv[1]))
provider = FakeProvider(Path(sys.argv[2]))
operation_id = sys.argv[3]

ledger.transition(operation_id, "authorized", "executing")
provider.create(operation_id)

# Simulate hard process death after provider commit but before ledger commit.
os._exit(17)
