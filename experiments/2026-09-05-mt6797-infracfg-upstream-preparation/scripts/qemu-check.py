#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exact-package validation and one bounded pure-KUnit QEMU run. Dry-run default."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import resource
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE.parent / 'qemu-contract.json').read_text())
MAX_LOG = 2 * 1024 * 1024
MAX_QMP = 65536


class Refusal(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Refusal(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    require(stat.S_ISREG(path.lstat().st_mode), 'non-regular file: ' + path.name)
    with path.open('rb') as stream:
        return stream.read()


def verify_package(package, contract=CONTRACT):
    require(package.is_dir() and not package.is_symlink(), 'package must be a real directory')
    inventory = regular(package / 'SHA256SUMS')
    require(digest(inventory) == contract['inventory_sha256'], 'inventory identity')
    entries = {}
    for line in inventory.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  \./(.+)', line)
        require(match is not None, 'malformed inventory')
        checksum, name = match.groups()
        require(not name.startswith('/') and all(x not in ('', '.', '..') for x in name.split('/')),
                'unsafe inventory member')
        require(name not in entries, 'duplicate inventory member')
        entries[name] = checksum
    actual = set()
    for root, dirs, files in os.walk(package, followlinks=False):
        for name in dirs:
            require(not (Path(root) / name).is_symlink(), 'directory symlink')
        for name in files:
            path = Path(root) / name
            require(stat.S_ISREG(path.lstat().st_mode), 'non-regular package member')
            actual.add(path.relative_to(package).as_posix())
    require(actual == set(entries) | {'SHA256SUMS'}, 'missing or extra package member')
    for name, checksum in entries.items():
        require(digest(regular(package / name)) == checksum, 'member digest: ' + name)
    provenance = json.loads(regular(package / 'provenance/build.json'))
    for key, value in contract['provenance'].items():
        require(provenance.get(key) == value, 'provenance: ' + key)
    require(digest(regular(package / 'Image.gz')) == contract['image_sha256'], 'image identity')
    config = regular(package / 'kernel.config').decode()
    enabled = set(re.findall(r'^(CONFIG_\w*KUNIT\w*)=y$', config, re.M))
    require(enabled == set(contract['enabled_kunit']), 'unexpected enabled KUnit symbols')
    return {'inventory_sha256': digest(inventory), 'members': len(entries),
            'image_sha256': contract['image_sha256'], 'kernel_release': provenance['kernel_release']}


def classify_log(raw, contract=CONTRACT):
    require(len(raw) <= MAX_LOG, 'log limit')
    text = raw.decode('utf-8', errors='strict').replace('\r\n', '\n')
    require('\x00' not in text and '\x1b' not in text, 'control characters')
    lines = [re.sub(r'^\[\s*\d+\.\d+\] ', '', line) for line in text.splitlines()]
    text = '\n'.join(lines)
    require(not re.search(r'not ok|Bail out!|Kernel panic|Oops:|BUG:|WARNING:|#\s*(?:SKIP|TODO)\b', text, re.I),
            'failure, skip, bailout or kernel diagnostic')
    banners = [line for line in lines if line.startswith('Linux version ')]
    require(len(banners) == 1 and banners[0].startswith('Linux version ' + contract['provenance']['kernel_release'] + ' '),
            'missing, duplicate or wrong release banner')
    require(lines.count('Kernel command line: ' + contract['command_line']) == 1, 'command line')
    require(lines.count('reboot: Power down') == 1, 'poweroff marker')
    tokens = []
    first = None
    last = None
    for pos, line in enumerate(lines):
        stripped = line.lstrip()
        if re.match(r'(?:KTAP\b|TAP\b|1\.\.|ok\b|not ok\b|# Subtest:)', stripped):
            tokens.append(line)
            first = pos if first is None else first
            last = pos
        if re.search(r'\b(?:fail|skip):[1-9]\d*', line):
            raise Refusal('nonzero diagnostic result count')
    accepted = []
    for order in itertools.permutations(contract['suites']):
        wanted = ['KTAP version 1', '1..2']
        for number, name in enumerate(order, 1):
            wanted += ['    KTAP version 1', '    # Subtest: ' + name, '    1..4']
            wanted += [f'    ok {i} {case}' for i, case in enumerate(contract['suites'][name], 1)]
            wanted += [f'ok {number} {name}']
        accepted.append(wanted)
    require(tokens in accepted, 'incomplete, unexpected or duplicate KTAP structure')
    require(first is not None and last < lines.index('reboot: Power down'), 'poweroff before completion')
    return {'suites_passed': 2, 'cases_passed': 8, 'complete_ktap': True}


def classify_exit(facts, contract=CONTRACT):
    require(facts['returncode'] == 0, 'QEMU exit failure')
    require(facts['stop_reason'] is None, 'host stop: ' + str(facts['stop_reason']))
    require(0 < facts['elapsed_seconds'] <= contract['timeout_seconds'], 'runtime budget')
    events = facts['qmp_events']
    shutdowns = [e for e in events if e.get('event') == 'SHUTDOWN']
    require(len(shutdowns) == 1, 'missing or duplicate QMP shutdown')
    data = shutdowns[0].get('data', {})
    require(data.get('guest') is True and data.get('reason') == 'guest-shutdown', 'not guest poweroff')
    require(not any(e.get('event') in ('GUEST_PANICKED', 'WATCHDOG', 'RESET') for e in events),
            'unexpected guest event')
    require(facts['qmp_capabilities'] is True and facts['qmp_cont'] is True, 'QMP start handshake')


def command(binary, image, serial, contract=CONTRACT):
    return [str(binary), '-machine', 'virt', '-accel', 'tcg', '-cpu', 'max',
            '-smp', '2', '-m', '512M', '-nodefaults', '-nic', 'none',
            '-display', 'none', '-monitor', 'none', '-serial', 'file:' + str(serial),
            '-qmp', 'stdio', '-S', '-no-reboot', '-kernel', str(image),
            '-append', contract['command_line']]


def child_limits():
    # Protect the evidence filesystem even if QEMU floods a file between polls.
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_LOG, MAX_LOG))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def capture(argv, output, contract=CONTRACT):
    """Internal process primitive; tests supply tiny fake processes, never a guest."""
    started = time.monotonic()
    facts = {'stop_reason': None, 'qmp_events': [], 'qmp_capabilities': False, 'qmp_cont': False}
    process = None
    pending = b''
    qmp_count = 0
    greeting = False
    try:
        with (output / 'qemu.stderr').open('xb') as err, (output / 'qmp.jsonl').open('xb') as qmp:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=err, start_new_session=True, preexec_fn=child_limits)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    elapsed = time.monotonic() - started
                    if elapsed >= contract['timeout_seconds']:
                        facts['stop_reason'] = 'timeout'
                        break
                    if any(p.exists() and p.stat().st_size >= MAX_LOG
                           for p in (output / 'serial.log', output / 'qemu.stderr')):
                        facts['stop_reason'] = 'log-limit'
                        break
                    for key, _ in selector.select(min(0.05, contract['timeout_seconds'] - elapsed)):
                        chunk = os.read(key.fileobj.fileno(), 4096)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        qmp_count += len(chunk)
                        require(qmp_count <= MAX_QMP, 'QMP output limit')
                        qmp.write(chunk)
                        pending += chunk
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            message = json.loads(line)
                            require(isinstance(message, dict), 'QMP object required')
                            if 'QMP' in message:
                                require(not greeting, 'duplicate QMP greeting')
                                greeting = True
                                process.stdin.write(b'{"execute":"qmp_capabilities","id":"caps"}\n')
                                process.stdin.flush()
                            elif message.get('id') == 'caps':
                                require(greeting and not facts['qmp_capabilities'] and message.get('return') == {}, 'QMP caps refusal')
                                facts['qmp_capabilities'] = True
                                process.stdin.write(b'{"execute":"cont","id":"start"}\n')
                                process.stdin.flush()
                            elif message.get('id') == 'start':
                                require(facts['qmp_capabilities'] and not facts['qmp_cont'] and message.get('return') == {}, 'QMP cont refusal')
                                facts['qmp_cont'] = True
                            elif 'event' in message:
                                facts['qmp_events'].append(message)
                            else:
                                raise Refusal('unexpected QMP reply')
                require(not pending, 'truncated QMP record')
            if facts['stop_reason'] is None:
                try:
                    process.wait(timeout=max(0.001, contract['timeout_seconds'] - (time.monotonic() - started)))
                except subprocess.TimeoutExpired:
                    facts['stop_reason'] = 'timeout'
    except (ValueError, OSError) as exc:
        facts['stop_reason'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if process is not None:
            if process.poll() is None or facts['stop_reason'] is not None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=contract['kill_after_seconds'])
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=1)
                # Also stop descendants if their group leader exited first.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            facts['returncode'] = process.returncode
            process.stdin.close()
            process.stdout.close()
        else:
            facts['returncode'] = None
        facts['elapsed_seconds'] = round(time.monotonic() - started, 6)
    return facts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='one run only after integration review')
    parser.add_argument('--output', type=Path, help='new evidence directory; never reused or removed')
    args = parser.parse_args()
    package = args.package.absolute()
    identity = verify_package(package)
    if not args.execute:
        print(json.dumps({'package': identity, 'execution': 'not requested'}, sort_keys=True))
        return
    require(sys.platform.startswith('linux'), 'execution requires Linux Buildbox')
    require(args.output is not None, 'explicit output required')
    output = args.output.absolute()
    require(output.parent.is_dir() and output.parent.resolve() == output.parent,
            'real pre-existing evidence parent required')
    require(output != package and package not in output.parents, 'output inside package')
    binary = shutil.which('qemu-system-aarch64')
    require(binary is not None, 'QEMU missing')
    binary = Path(binary).resolve()
    version = subprocess.run([str(binary), '--version'], capture_output=True, timeout=5, check=True)
    output.mkdir(mode=0o700)  # Existing evidence consumes this attempt; no overwrite/retry.
    receipt = {'package': identity, 'qemu_sha256': digest(regular(binary)),
               'qemu_version': version.stdout.decode().strip(), 'result': 'INCOMPLETE'}
    try:
        argv = command(binary, package / 'Image.gz', output / 'serial.log')
        # Receipt uses neutral paths; raw QMP/serial/stderr contain no host credentials.
        receipt['argv'] = command(binary.name, '<package>/Image.gz', '<output>/serial.log')
        (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
        facts = capture(argv, output)
        receipt['process'] = facts
        verify_package(package)  # Any input change during execution rejects the result.
        classify_exit(facts)
        receipt['tests'] = classify_log(regular(output / 'serial.log'))
        require(not regular(output / 'qemu.stderr').strip(), 'unexpected QEMU stderr')
        receipt['result'] = 'PASS'
    except (OSError, ValueError) as exc:
        receipt['result'] = 'REFUSED'
        receipt['reason'] = str(exc)
    finally:
        receipt['logs'] = {p.name: digest(regular(p)) for p in output.iterdir()
                           if p.name != 'result.json' and p.is_file()}
        with (output / 'result.json').open('w') as stream:
            stream.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    print(json.dumps(receipt, sort_keys=True))
    require(receipt['result'] == 'PASS', 'run refused; preserve evidence and review before any retry')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('REFUSED: ' + str(error), file=sys.stderr)
        sys.exit(1)
