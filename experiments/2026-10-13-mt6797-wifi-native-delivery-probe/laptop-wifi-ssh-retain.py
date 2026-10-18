#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Standard one-lifetime CCMP client: retain stderr and numeric local state.

Reuse the frozen verifier, SSH options, owned-child limits and ACK gates.
The active route observation uses netstat; completed D1/D2/D3 tools stay frozen.
"""
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('standard_client_observation',
                                            HERE / 'laptop-wifi-ssh-neighbor.py')
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


def retained_runner(root, runner=subprocess.run):
    def local_route(argv, **kwargs):
        if argv[:3] == ['/sbin/route', '-n', 'get']:
            # The underlying D2 observer already validates the numeric target.
            # Keep its timing/unknown-state rules, replacing only this syscall.
            if len(argv) != 4 or not D.O.C.M.ADDRESS.fullmatch(argv[3]):
                raise ValueError('numeric route observation required')
            argv = ['/usr/sbin/netstat', '-rn', '-f', 'inet']
        return runner(argv, **kwargs)
    return D.O.observing_runner(root, runner=D.neighbor_runner(root, local_route))


def run(root, keys, boot, cycles, poll_seconds, runner=subprocess.run):
    result = D.O.C.run(keys, boot, cycles, poll_seconds,
                       runner=retained_runner(root, runner))
    result['client_retention_enabled'] = True
    result['client_observation_created'] = root.exists()
    result['route_probe'] = 'netstat -rn -f inet; private IPv4 table snapshot'
    return result


def main():
    os.umask(0o077)
    if sys.platform != 'darwin' or sys.argv.count('--receipt') != 1:
        raise ValueError('custodian laptop and one owned receipt required')
    receipt = Path(sys.argv[sys.argv.index('--receipt') + 1])
    runtime = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True)
    if not re.fullmatch(r'session-ccmp(?:[1-9][0-9]*|-gtk[1-9][0-9]*)', receipt.parent.name):
        raise ValueError('receipt does not name a CCMP session')
    expected = runtime / 'ccmp-stable-monitor' / receipt.parent.name / 'wifi-ssh-receipt.json'
    if receipt != expected or receipt.parent.resolve(strict=True) != receipt.parent:
        raise ValueError('receipt is outside the owned session')
    D.O.C.M.run = lambda keys, boot, cycles, poll: run(
        receipt.parent / 'ssh-client-observation', keys, boot, cycles, poll)
    return D.O.C.M.main()


if __name__ == '__main__':
    sys.exit(main())
