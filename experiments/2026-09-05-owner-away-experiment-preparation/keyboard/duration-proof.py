#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reparse immutable harmless timing proof; never admits device capture."""
import hashlib
import json
from pathlib import Path
import re
import stat

HERE = Path(__file__).resolve().parent
SOURCE_NAMES = ('monitor.c', 'monitor-fixture.c', 'test-monitor.py', 'full-duration.py',
                'duration-proof.py', 'build-monitor.sh', '../../../LICENSE', '../baseline/scripts/buildbox_userspace.py')
FILES = {'inputs.json', 'process.json', 'stdout', 'stderr', 'observer.stdout',
         'observer.stderr', 'monitor.status', 'fixture'}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON member')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _value: require(False, 'nonfinite JSON number'))


def sources():
    return {name: sha((HERE / name).read_bytes()) for name in SOURCE_NAMES}


def read(path, bound=2097152):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= bound,
            'proof file type/size')
    return path.read_bytes()


def write(path, raw):
    import os
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def seal(root):
    import os
    raw = ''.join(sha(read(root / name)) + '  ' + name + '\n' for name in sorted(FILES)).encode()
    write(root / 'SHA256SUMS', raw)
    descriptor = os.open(root, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return sha(raw)


def classify(root, expected_sources):
    require(not root.is_symlink() and root.is_dir(), 'proof root type')
    require({p.name for p in root.iterdir()} == FILES | {'SHA256SUMS'}, 'proof inventory')
    raw = {name: read(root / name) for name in FILES}
    sums = ''.join(sha(raw[name]) + '  ' + name + '\n' for name in sorted(FILES)).encode()
    require(read(root / 'SHA256SUMS') == sums, 'proof checksum mismatch')
    inputs = decode(raw['inputs.json'])
    require(isinstance(inputs, dict) and set(inputs) == {'schema', 'sources', 'mode', 'fixture_sha256',
            'musl_archive_sha256', 'tool_inputs_sha256', 'tools', 'library'}, 'input inventory')
    require(set(expected_sources) == set(SOURCE_NAMES), 'expected source inventory')
    require(inputs['schema'] == 'keyboard-duration-inputs-v1' and
            inputs['sources'] == expected_sources, 'proof source mismatch')
    require(inputs['mode'] == 'harmless-ignore-production-duration-arm64-qemu' and
            inputs['fixture_sha256'] == sha(raw['fixture']) and raw['fixture'], 'fixture identity/mode')
    require(inputs['musl_archive_sha256'] == 'd585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a' and
            re.fullmatch('[0-9a-f]{64}', inputs['tool_inputs_sha256']), 'build input binding')
    require(isinstance(inputs['tools'], dict) and set(inputs['tools']) == {'compiler', 'qemu'} and
            isinstance(inputs['library'], dict) and inputs['library'] and
            inputs['library'].get('bin/musl-gcc') == inputs['tools']['compiler'], 'tool/library inventory')
    for value in [*inputs['tools'].values(), *inputs['library'].values()]:
        require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'tool/library hash')
    process = decode(raw['process.json'])
    require(isinstance(process, dict) and set(process) == {'error', 'returncode', 'elapsed_seconds'},
            'process inventory')
    failures = []
    def check(value, reason):
        if not value:
            failures.append(reason)
    check(process.get('error') is None and process.get('returncode') == 2,
          'process-incomplete-or-unexpected')
    check(isinstance(process.get('elapsed_seconds'), (int, float)) and
          202 <= process['elapsed_seconds'] < 225, 'outer-duration')
    check(raw['stderr'] == raw['observer.stderr'] == b'', 'stderr')
    check(raw['stdout'] == raw['observer.stdout'] and
          raw['stdout'].count(b'fixture-observation-boundary=202000\n') == 1, 'observation-forwarding')
    fields = {}
    try:
        for line in raw['monitor.status'].decode('ascii').splitlines():
            key, value = line.split('=', 1)
            require(key not in fields, 'duplicate status field')
            fields[key] = value
        fixed = {'schema': 'keyboard-monitor-v1', 'reason': 'deadline', 'reaped': '1',
                 'identity_lost': '0', 'exit': '-1', 'signal': '9', 'cancel': '0',
                 'term_errno': '0', 'kill_errno': '0', 'late': '0', 'stderr_bytes': '0'}
        require(set(fields) == set(fixed) | {'term_ms', 'kill_ms', 'reap_ms', 'stdout_bytes',
                                            'forwarded_bytes'}, 'status inventory')
        check(all(fields[k] == v for k, v in fixed.items()), 'control-status')
        term, kill, reap = (int(fields[k]) for k in ('term_ms', 'kill_ms', 'reap_ms'))
        check(209000 <= term <= 210000 and 213000 <= kill <= 214000 and kill <= reap <= 215000,
              'signal-or-reap-deadline')
        check(int(fields['stdout_bytes']) == int(fields['forwarded_bytes']) == len(raw['stdout']),
              'byte-accounting')
    except (ValueError, KeyError, UnicodeError):
        failures.append('malformed-status')
    return {'schema': 'keyboard-duration-classification-v1',
            'classification': 'failed' if failures else 'passed', 'failures': failures,
            'proof_sha256': sha(sums), 'device_action': 'none', 'keyboard_result': 'not-tested'}
