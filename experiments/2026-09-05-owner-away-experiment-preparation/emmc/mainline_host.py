#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One-shot local USB route prerequisite. Never gates Gemian LAN transport."""
import ipaddress
import json
from pathlib import Path
import re
import runpy
import subprocess


def inspect(interfaces, routes, destination, host_address):
    target = ipaddress.IPv4Address(destination)
    host = ipaddress.IPv4Interface(host_address)
    if target not in host.network:
        raise ValueError('destination outside admitted USB subnet')
    entries = {}
    current = None
    for line in interfaces.splitlines():
        match = re.match(r'^([a-zA-Z0-9]+):', line)
        if match:
            current = match[1]; entries[current] = {'active': False, 'addresses': []}
        elif current:
            if line.strip() == 'status: active': entries[current]['active'] = True
            match = re.match(r'\s+inet (\S+) netmask (0x[0-9a-f]+)', line)
            if match: entries[current]['addresses'].append((match[1], int(match[2],16)))
    matches = [name for name, value in entries.items() if
        (str(host.ip), int(host.network.netmask)) in value['addresses']]
    active = len(matches) == 1 and entries[matches[0]]['active']
    direct = False
    conflicting = False
    for line in routes.splitlines():
        parts = line.split()
        if len(parts) < 4 or not re.fullmatch(r'[0-9./]+', parts[0]): continue
        value = parts[0]
        address, _, prefix = value.partition('/')
        components = address.split('.')
        if not prefix: prefix = str(len(components)*8)
        address = '.'.join(components + ['0']*(4-len(components)))
        try: network = ipaddress.IPv4Network(address+'/'+prefix, strict=False)
        except ValueError: continue
        if target not in network: continue
        usable = 'U' in parts[2] and not any(flag in parts[2] for flag in 'GRB')
        same = active and parts[3] == matches[0]
        if network == host.network and parts[1].startswith('link#') and usable and same:
            direct = True
        if network.prefixlen >= host.network.prefixlen and (not same or not usable):
            conflicting = True
    return {'unique_expected_address': len(matches)==1, 'interface_active': active,
            'direct_subnet_route': direct, 'conflicting_target_route': conflicting,
            'ready': active and direct and not conflicting,
            'scope': 'mainline-usb-only', 'device_packets_sent': False}


def require_ready(destination='10.15.19.82', host_address='10.15.19.1/24'):
    # Both commands inspect local kernel state. No route lookup, ARP, ping or SSH.
    outputs = []
    for command in (['/sbin/ifconfig','-a'], ['/usr/sbin/netstat','-rn','-f','inet']):
        result = subprocess.run(command, capture_output=True, timeout=5)
        if result.returncode or result.stderr or len(result.stdout)>262144:
            raise ValueError('local interface/route inventory incomplete')
        outputs.append(result.stdout.decode('ascii'))
    result = inspect(*outputs, destination, host_address)
    if not result['ready']:
        raise ValueError('mainline USB host prerequisite absent; no observation claim or connection')
    return result


def identity_once(prepared, directory):
    """Call only for a separately authorized fresh identity observation."""
    status = require_ready()  # Before imports, claim, files or any device transport.
    module = runpy.run_path(str(Path(__file__).with_name('collect-emmc.py')))
    C = module['C']
    directory = Path(directory).absolute()
    C['ignored'](module['REPO'],directory)
    C['directory'](directory.parent)
    directory.mkdir(mode=0o700)
    script = (b'BB=/bin/busybox\nexport LC_ALL=C\nset -eu\n'
        b'$BB cat /proc/sys/kernel/random/boot_id\n$BB uname -r\n$BB cat /proc/uptime\n'
        + module['observer_guard'](prepared['candidate']))
    C['write_new'](directory/'host-prerequisite.json',module['json_bytes'](status))
    C['write_new'](directory/'command.sh',script)
    C['write_new'](directory/'claim.json',module['json_bytes']({'connections':1,'seconds':10,
        'stdout_limit':4096,'stderr_limit':4096,'command_sha256':module['sha'](script)}))
    process = C['run_once'](C['ssh_command'](prepared['keys']),script,directory,10,
        stdout_limit=4096,stderr_limit=4096)
    C['write_new'](directory/'process.json',module['json_bytes'](process))
    return process


if __name__ == '__main__':
    try:
        print(json.dumps(require_ready(),sort_keys=True))
    except ValueError as exc:
        print(json.dumps({'ready':False,'scope':'mainline-usb-only','reason':str(exc)}))
        raise SystemExit(2)
