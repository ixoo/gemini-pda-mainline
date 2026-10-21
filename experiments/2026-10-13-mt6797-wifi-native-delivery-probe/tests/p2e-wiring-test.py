#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the pinned P2 source-routing and custody fixtures against P2E selectors."""
import hashlib
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PINS = {'ccmp-p2-session-sources-test.py': '381c89169b240b496e243d388daa5768bdd8310548ed69a8f9648c60957dd712',
 'p2-parent-gate-test.py': 'ac0606f0fe644fde3b2e1b4809e9d092306fc5dfb1a2f386397359a6d5a4cfe1'}
retained = Path(sys.argv[1]).resolve(strict=True)


def replace(source, old, new, count=1):
    if source.count(old) != count:
        raise ValueError('P2E fixture anchor changed: ' + old)
    return source.replace(old, new)


for name in ('ccmp-p2-session-sources-test.py', 'p2-parent-gate-test.py'):
    source = (HERE / name).read_text()
    if hashlib.sha256(source.encode()).hexdigest() != PINS[name]:
        raise ValueError('reviewed P2 fixture changed: ' + name)
    if name == 'ccmp-p2-session-sources-test.py':
        source = replace(source, 'laptop-session-ccmp-p2.py', 'laptop-session-ccmp-p2e.py', 2)
        source = replace(source, "'ccmp-stable-monitor/session-ccmp-p2'",
                          "'ccmp-stable-monitor/session-ccmp-p2e'")
        anchor = "    class ReachedPinnedHost(Exception):\n"
        source = replace(source, anchor,
            "    # Imports are offline and must not construct a transport child.\n"
            "    from unittest.mock import patch\n"
            "    with patch.object(subprocess, 'Popen', side_effect=AssertionError('device process forbidden')):\n"
            "        prepared = g['ORIGINAL_RUN_PATH'](str(probe / 'prepare-ccmp-p2e.py'))\n"
            "        captured = g['ORIGINAL_RUN_PATH'](str(probe / 'laptop-capture-ccmp-p2e.py'))\n"
            "    assert prepared['GLOBALS']['SESSION'] == 'session-ccmp-p2e'\n"
            "    assert prepared['GLOBALS']['CAPTURE'] == 'capture-ccmp-p2e'\n"
            "    assert captured['CAP'].WMT.CAPTURE_DIR.name == 'capture-ccmp-p2e'\n"
            "    assert captured['CAP'].WMT.CAPTURE.DEPLOYMENT.parent.name == 'session-ccmp-p2e'\n"
            "    assert captured['CAP'].WMT.CAPTURE.RECEIPT.name == 'ccmp-stable-monitor-candidate-p2.json'\n"
            + anchor)
    else:
        source = replace(source, 'passive-host-ccmp-p2.py', 'passive-host-ccmp-p2e.py')
        source = replace(source, '    host.PH.HELPER.join_and_record=lambda active:None\n',
            "    host.PH.HELPER.join_and_record=lambda active:None\n"
            "    from types import SimpleNamespace\n"
            "    spawns=[]\n"
            "    def spawn(argv, **kwargs):\n"
            "        spawns.append((argv,kwargs))\n"
            "        return SimpleNamespace(pid=12345)\n"
            "    host.PH.HELPER.spawn=spawn\n")
        source = replace(source, '    helper=host.PH.HELPER\n',
            "    helper=host.PH.HELPER\n"
            "    helper.start(); helper.start()\n"
            "    assert len(spawns)==1\n"
            "    assert spawns[0][0][1]==str(HERE/'laptop-wifi-ssh-connected-p2e.py')\n"
            "    assert spawns[0][1]['start_new_session'] is True\n"
            "    assert helper.receipt_path.parent.name=='session-ccmp-p2e'\n")
    prefix = '__file__ = ' + repr(str(Path(__file__).resolve())) + '\n'
    subprocess.run([sys.executable, '-c', prefix+source, str(retained)], check=True, timeout=30)
print('P2E selectors: fresh roots, exact helper, retained sources, logger and custody gates PASS')
