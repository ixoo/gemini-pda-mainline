#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the completed host-main ownership fixture to fresh P1 namespaces."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-no-scan-host-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp-p1').replace('CCMP2', 'P1')
# Production resolves the runtime root; /tmp aliases /private/tmp on macOS.
fixture = fixture.replace('root = Path(temporary)', 'root = Path(temporary).resolve()').replace(
    'root = Path(tmp);', 'root = Path(tmp).resolve();')
fixture = fixture.replace('join-ccmp.sh', 'join-ccmp-p1.sh')
exec(compile(fixture, str(HERE / 'ccmp2-no-scan-host-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
