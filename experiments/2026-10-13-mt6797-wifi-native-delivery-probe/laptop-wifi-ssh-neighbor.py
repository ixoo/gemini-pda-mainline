#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""D2: bounded local route/ARP observations around the original SSH attempt."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'laptop-wifi-ssh-observe.py'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != \
        'b2582322fbe354c15991da524aa48e3e333a44fdcac95274884d3d7265e1e332':
    raise ValueError('D1 output observer changed')
SPEC = importlib.util.spec_from_file_location('d1_ssh_observer', SOURCE)
O = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(O)


def neighbor_runner(root, runner=subprocess.run, monotonic_ns=time.monotonic_ns):
    def invoke(argv, **kwargs):
        if not any(arg.startswith('HostKeyAlias=') for arg in argv):
            return runner(argv, **kwargs)
        address = argv[-2].removeprefix('root@')
        if not argv[-2].startswith('root@') or not O.C.M.ADDRESS.fullmatch(address):
            raise ValueError('local query requires the validated numeric SSH target')
        queries = []

        def query(label, command):
            entry = {'label': label, 'started_ns': monotonic_ns(),
                     'exit': None, 'timeout': False, 'error': None}
            try:
                result = runner(command, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=0.5)
                data = result.stdout
                entry['exit'] = result.returncode
            except subprocess.TimeoutExpired as exc:
                data = exc.output or b''
                entry['timeout'] = True
            except OSError as exc:
                data = b''
                entry['error'] = type(exc).__name__
            entry.update(ended_ns=monotonic_ns(), bytes=len(data))
            with (root / (label + '.bin')).open('xb') as stream:
                stream.write(data)
            queries.append(entry)

        query('route-before', ['/sbin/route', '-n', 'get', address])
        query('arp-before', ['/usr/sbin/arp', '-n', address])
        client_started = monotonic_ns()
        try:
            return runner(argv, **kwargs)  # same command, streams and timeout as D1
        finally:
            client_ended = monotonic_ns()
            query('arp-after', ['/usr/sbin/arp', '-n', address])
            with (root / 'local-queries.json').open('x') as stream:
                json.dump({'queries': queries, 'client_started_ns': client_started,
                           'client_ended_ns': client_ended,
                           'client_timeout_s': kwargs['timeout']},
                          stream, indent=2, sort_keys=True)
                stream.write('\n')
    return invoke


def main():
    if sys.platform != 'darwin':
        raise ValueError('D2 runtime requires the custodian laptop system tools')
    original = O.observing_runner
    O.observing_runner = lambda root: original(root, runner=neighbor_runner(root))
    return O.main()


if __name__ == '__main__':
    sys.exit(main())
