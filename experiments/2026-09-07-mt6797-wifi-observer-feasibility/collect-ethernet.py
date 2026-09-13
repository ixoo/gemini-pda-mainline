#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Wait for one attributable USB Ethernet interface, then preserve one snapshot."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
NETWORK = HERE.parent / '2026-09-05-owner-away-experiment-preparation/emmc/mainline_host.py'
NETWORK_SHA256 = '57491d7ac60a380ee85215e391274e5ced2733b33ab6df70e0757db7b67bf082'
RECEIVER = HERE / 'capture-export.py'
SERIAL = 'GEMINI_WIFI_EXPORT_TCP_1'
NODE = re.compile(r'^.*\+-o .*<class IOUSBHostDevice, id (0x[0-9a-f]+),.*$', re.M)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def devices(text):
    nodes = list(NODE.finditer(text))
    result = []
    for i, node in enumerate(nodes):
        section = text[node.end():nodes[i + 1].start() if i + 1 < len(nodes) else len(text)]
        own = section.split('+-o', 1)[0]
        properties = {}
        for key in ('idVendor', 'idProduct', 'USB Product Name', 'USB Serial Number'):
            found = re.findall(r'^\s*(?:\|\s*)*"' + re.escape(key) + r'" = (.+)$', own, re.M)
            properties[key] = json.loads(found[0]) if len(found) == 1 else None
        interfaces = re.findall(r'^\s*(?:\|\s*)*"BSD Name" = "(en[0-9]+)"$', section, re.M)
        result.append({'registry_id': node.group(1), 'usb': properties, 'interfaces': interfaces})
    return result


def select(records, before, interfaces, routes, network):
    matches = [r for r in records if r['usb']['USB Serial Number'] == SERIAL]
    if len(matches) > 1:
        raise ValueError('ambiguous USB capture parent')
    if not matches:
        return None
    selected = matches[0]
    if selected['registry_id'] in before:
        raise ValueError('capture parent predates this armed observation')
    if selected['usb'] != {'idVendor': 0x0525, 'idProduct': 0xa4a2,
                           'USB Product Name': 'RNDIS/Ethernet Gadget', 'USB Serial Number': SERIAL}:
        raise ValueError('USB capture descriptors changed')
    if not selected['interfaces']:
        return None
    if len(selected['interfaces']) != 1:
        raise ValueError('ambiguous Ethernet child')
    name = selected['interfaces'][0]
    blocks = re.split(r'(?m)^(?=[A-Za-z0-9]+:)', interfaces)
    block = [b for b in blocks if b.startswith(name + ':')]
    if len(block) != 1:
        return None
    if re.findall(r'(?m)^\s+ether ([0-9a-f:]+)\s*$', block[0]) != ['42:00:15:19:82:00']:
        raise ValueError('Ethernet protocol address mismatch')
    if not re.search(r'(?m)^\s+inet 10\.15\.19\.1 netmask 0xffffff00(?:\s|$)', block[0]):
        return None
    status = network.inspect(interfaces, routes, '10.15.19.82', '10.15.19.1/24')
    if not status['ready']:
        return None
    return dict(selected, interface=name, network=status)


def read_command(command, limit):
    result = subprocess.run(command, capture_output=True, timeout=5, check=True)
    if result.stderr or len(result.stdout) > limit:
        raise ValueError('host inventory incomplete or exceeds its bound')
    return result.stdout


def save(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-boot-id', required=True)
    parser.add_argument('--session-sha256', required=True)
    parser.add_argument('--receiver-sha256', required=True)
    parser.add_argument('output', type=Path, help='new directory below a private parent')
    args = parser.parse_args()
    os.umask(0o077)
    if hashlib.sha256(RECEIVER.read_bytes()).hexdigest() != args.receiver_sha256:
        raise ValueError('selected receiver changed')
    if hashlib.sha256(NETWORK.read_bytes()).hexdigest() != NETWORK_SHA256:
        raise ValueError('reviewed network prerequisite changed')
    export = load('capture_export', RECEIVER)
    network = load('mainline_host', NETWORK)
    export.identities(args.previous_boot_id, args.session_sha256)
    export.check_destination(args.output)
    args.output.mkdir(mode=0o700)
    usb_command = ['/usr/sbin/ioreg', '-r', '-c', 'IOUSBHostDevice', '-l', '-w', '0']
    initial = read_command(usb_command, 2 * 1024 * 1024)
    initial_records = devices(initial.decode())
    before = {r['registry_id'] for r in initial_records}
    save(args.output / 'usb-before.txt', initial)
    if any(r['usb']['USB Serial Number'] == SERIAL for r in initial_records):
        raise ValueError('capture gadget is already present; no new boot observation armed')
    save(args.output / 'armed.json', (json.dumps({'utc_seconds': time.time(),
        'seconds': 600, 'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'network_helper_sha256': hashlib.sha256(NETWORK.read_bytes()).hexdigest(),
        'receiver_sha256': args.receiver_sha256, 'previous_boot_id': args.previous_boot_id,
        'session_sha256': args.session_sha256}) + '\n').encode())
    deadline = time.monotonic() + 600
    previous = None
    raw, interface_bytes, route_bytes = initial, b'', b''
    print('Collector armed: waiting up to 600 seconds for the USB Ethernet capture.', flush=True)
    for poll in range(600):
        if time.monotonic() >= deadline:
            break
        raw = read_command(usb_command, 2 * 1024 * 1024)
        records = devices(raw.decode())
        # Preserve descriptor/child changes, including unexpected USB devices.
        if records != previous:
            save(args.output / f'usb-change-{poll:03}.json', json.dumps(records, indent=2).encode())
            previous = records
        interface_bytes = read_command(['/sbin/ifconfig', '-a'], 262144)
        route_bytes = read_command(['/usr/sbin/netstat', '-rn', '-f', 'inet'], 262144)
        selected = select(records, before, interface_bytes.decode(), route_bytes.decode(), network)
        if selected:
            save(args.output / 'usb-selected.txt', raw)
            save(args.output / 'interfaces-selected.txt', interface_bytes)
            save(args.output / 'routes-selected.txt', route_bytes)
            save(args.output / 'selection.json', json.dumps(selected, indent=2).encode())
            print('USB Ethernet and its direct route identified; starting one capture request.', flush=True)
            with (args.output / 'receiver.stdout').open('xb') as out, (args.output / 'receiver.stderr').open('xb') as err:
                result = subprocess.run([sys.executable, str(RECEIVER), '--tcp', '--acknowledge',
                    '--previous-boot-id', args.previous_boot_id, '--session-sha256', args.session_sha256,
                    str(args.output / 'usb-export')], stdout=out, stderr=err, timeout=70)
                out.flush(); os.fsync(out.fileno())
                err.flush(); os.fsync(err.fileno())
            save(args.output / 'receiver-status.json', json.dumps({'exit': result.returncode}).encode())
            return result.returncode
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    save(args.output / 'usb-final.txt', raw)
    save(args.output / 'interfaces-final.txt', interface_bytes)
    save(args.output / 'routes-final.txt', route_bytes)
    print('No ready attributed USB Ethernet link; no capture request sent.', flush=True)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
