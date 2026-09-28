#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pre-arm one USB-stage watch for the installed passive CONN-domain-link candidate."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HOST = HERE / 'passive-host.py'
NETWORK = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/emmc/mainline_host.py'
OUTPUT = REPO / 'artifacts/conn-domain-link'
ABSENT = 'mainline USB host prerequisite absent; no observation claim or connection'
SECONDS = 900


def utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def stage():
    result = subprocess.run(['/usr/sbin/ioreg', '-p', 'IOUSB', '-l'],
                            capture_output=True, timeout=5)
    if result.returncode or result.stderr or len(result.stdout) > 1048576:
        raise ValueError('local USB inventory incomplete')
    raw = result.stdout
    if b'Gemini-L-Observability' in raw:
        return 'candidate-gadget'
    if (b'"idVendor" = 3725' in raw and b'"idProduct" = 8447' in raw and
            b'"USB Product Name" = "Unknown"' in raw):
        return 'mediatek-20ff'
    if b'MT65xx Preloader' in raw:
        return 'preloader'
    return 'other-or-absent'


def ready(network):
    try:
        return network.require_ready()
    except ValueError as error:
        if str(error) != ABSENT:
            raise
        return None


def record(stream, event, **fields):
    stream.write(json.dumps({'utc': utc(), 'event': event, **fields}, sort_keys=True) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    preflight = subprocess.run([sys.executable, str(HOST), '--candidate',
                               str(args.candidate)], capture_output=True, text=True,
                              timeout=30)
    if preflight.returncode or preflight.stdout.strip() != \
            'offline-preparation=pass; device_action=none':
        parser.exit(2, 'passive collector offline preparation refused\n')
    spec = importlib.util.spec_from_file_location('mainline_host', NETWORK)
    network = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(network)
    if ready(network) is not None:
        parser.exit(2, 'mainline USB route already present before arm\n')
    first = stage()
    if not args.execute:
        print('offline-preparation=pass; initial_usb_stage=' + first + '; device_action=none')
        return 0

    output = OUTPUT / ('watch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(mode=0o700)
    with (output / 'events.jsonl').open('x', encoding='utf-8') as stream:
        record(stream, 'armed', stage=first, budget_seconds=SECONDS)
        print('watch=armed; stage=' + first + '; budget_seconds=' + str(SECONDS), flush=True)
        previous = first
        deadline = time.monotonic() + SECONDS
        while time.monotonic() < deadline:
            try:
                current = stage()
            except (OSError, ValueError, subprocess.TimeoutExpired):
                current = 'inventory-error'
            if current != previous:
                record(stream, 'usb-stage', stage=current)
                print('usb-stage=' + current, flush=True)
                previous = current
            status = ready(network)
            if status is not None:
                record(stream, 'mainline-route', stage=current)
                print('mainline_usb_route=ready', flush=True)
                result = subprocess.run([sys.executable, str(HOST), '--candidate',
                                         str(args.candidate), '--execute'], cwd=REPO)
                record(stream, 'collector-exit', exit_status=result.returncode)
                return result.returncode
            time.sleep(1)
        record(stream, 'expired', stage=previous, mainline_route=False,
               device_ssh_attempts=0)
    print('watch=expired; mainline_usb_route=absent', flush=True)
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
