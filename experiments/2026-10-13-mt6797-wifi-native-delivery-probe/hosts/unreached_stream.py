#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A measurement whose SSH never connected can still prove its remote owner absent.

usage: unreached_stream.py <work-dir>   (after bind rendered hosts/; before prepare)

Boot R's measurement SSH over Wi-Fi never connected ("ssh: connect to host ...
port 22: Operation timed out", exit 255, no output), so the device never
printed TP1_OWNER_PID. Without that PID the helper forces the remote owner
scan to fail (owners=1), because it cannot check the owner's process group.
The session then refused the export, seal and recovery on "P2 remote owner not
confirmed quiescent", and no graded receipt was written.

When the TCP connection itself failed, no remote shell ran, so there is no
owner and no process group to check. Only in that case, proved from the
retained SSH observation (exit 255, no timeout, no stdout, stderr exactly one
connect failure line), the tagged-owner scan runs unmodified and its result
stands; the remote record names the case. Any other missing PID still fails.
"""
import sys
from pathlib import Path

CONNECT_FAILURES = ('Operation timed out', 'Connection refused', 'No route to host',
                    'Network is unreachable', 'Host is down')


def unreached(root):
    """True only when the retained SSH observation shows the connection never opened."""
    import json
    import re
    try:
        process = json.loads((root / 'process.json').read_text())
        out, err = (root / 'stdout.bin').read_bytes(), (root / 'stderr.bin').read_bytes()
    except (OSError, ValueError):
        return False
    pattern = rb'ssh: connect to host [0-9.]+ port 22: (' + '|'.join(CONNECT_FAILURES).encode() + rb')\r?\n'
    return bool(process.get('exit') == 255 and process.get('timeout') is False and not out and
                re.fullmatch(pattern, err))


def apply(path):
    import inspect
    s = path.read_text()
    old = "        if owner is None:\n            return script.replace('owners=0', 'owners=1')\n"
    assert s.count(old) == 1, 'helper anchor (missing owner)'
    s = s.replace(old, "        if owner is None:\n"
                       "            # unreached_stream.py: no connection, no owner; the tagged scan alone stands\n"
                       "            if _us_unreached(root):\n"
                       "                return script\n"
                       "            return script.replace('owners=0', 'owners=1')\n")
    old = "    remote['scope'] = 'exact tagged owner and observed PTY process group/session absent; bounded proc scans'\n"
    assert s.count(old) == 1, 'helper anchor (remote scope)'
    s = s.replace(old, old + "    if owner is None and _us_unreached(root):\n"
                             "        remote.update(ssh_unreached=True, scope='measurement SSH never connected; '\n"
                             "                      'tagged owner absent; bounded proc scan')\n")
    old = "\ndef main():\n"
    assert s.count(old) == 1, 'helper anchor (main)'
    helper = inspect.getsource(unreached).replace('def unreached(', 'def _us_unreached(')
    s = s.replace(old, '\nCONNECT_FAILURES = %r\n\n\n%s\n%s' % (CONNECT_FAILURES, helper, old))
    compile(s, str(path), 'exec')
    path.write_text(s)


if __name__ == '__main__':
    apply(Path(sys.argv[1]) / 'hosts/throughput-helper.py')
    print('unreached stream: a measurement SSH that never connected is proved ownerless by the tagged scan (helper)')
