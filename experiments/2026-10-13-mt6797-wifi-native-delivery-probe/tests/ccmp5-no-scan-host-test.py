#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the completed host-main ownership fixture to fresh CCMP5 namespaces."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-no-scan-host-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp5').replace('CCMP2', 'CCMP5')
exec(compile(fixture, str(HERE / 'ccmp2-no-scan-host-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
