#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""PID1 for an admitted native observation candidate; never a general launcher."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import sys
import time
import uuid

ROOT = Path('/')
INPUT_PATHS = {
    'lib/firmware/ROMv3_patch_1_1_hdr.bin': 46472,
    'lib/firmware/ROMv3_patch_1_0_hdr.bin': 210904,
    'lib/firmware/WMT_SOC.cfg': 80,
    'vendor/firmware/WIFI_RAM_CODE_6797': 411632,
    'data/nvram/APCFG/APRDEB/WIFI': 514,
}
RUNTIME = '16e8ab61ac39d3cf22146b0a945f5eea41c53fb67020a6fc2a6f30d50d51077f'
BOOT_ENTRY_CYCLE_ID = '7f21b732-da47-4245-ad83-e985044054a6'
CHIP, VERSION = 0x0279, 0x8a00
STAGE = 'python-entry'
LOG_WRITES = 0


def mark(stage):
    """Fixed call-site labels only; never pass input values or exception text."""
    global STAGE
    STAGE = stage


def log_stage(status):
    global LOG_WRITES
    if LOG_WRITES >= 8:
        raise ValueError('bootstrap log budget exhausted')
    LOG_WRITES += 1  # Consume before the syscall; no write retry.
    info = os.fstat(3)
    if not stat.S_ISCHR(info.st_mode) or info.st_rdev != os.makedev(1, 11):
        raise ValueError('expected inherited kernel log descriptor')
    boot = str(uuid.UUID(text('proc/sys/kernel/random/boot_id')))
    data = f'<11>wifi-bootstrap-v1 boot={boot} python={STAGE} status={status}\n'.encode('ascii')
    if len(data) > 192 or os.write(3, data) != len(data):
        raise OSError('bootstrap log write failed')


def file_bytes(relative, limit):
    path = ROOT / relative
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('expected a regular input')
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError('input exceeds its bound')
    return value


def text(relative, limit=65536):
    return file_bytes(relative, limit).decode().rstrip('\n')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def digest_field(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('expected a lowercase SHA-256 identity')
    if not any(bytes.fromhex(value)):
        raise ValueError('empty identity')
    return value


def validate_session(session):
    required = {'schema', 'cycle_id', 'kernel_release', 'kernel_version',
                'kernel_image_sha256', 'kernel_inputs_sha256', 'kernel_config_sha256',
                'runtime_sha256', 'input_manifest_sha256', 'startup_files', 'cpu_online',
                'startup_action'}
    if set(session) != required or session['schema'] != 2:
        raise ValueError('unknown session schema')
    if session['startup_action'] not in ('export', 'cycle', 'boot-entry'):
        raise ValueError('unknown startup action')
    if session['startup_action'] == 'boot-entry' and session['cycle_id'] != BOOT_ENTRY_CYCLE_ID:
        raise ValueError('boot-entry control identity mismatch')
    cycle = uuid.UUID(session['cycle_id'])
    if str(cycle) != session['cycle_id'] or cycle.int == 0:
        raise ValueError('invalid cycle identity')
    for key in required:
        if key.endswith('_sha256'):
            digest_field(session[key])
    if session['runtime_sha256'] != RUNTIME:
        raise ValueError('runtime identity mismatch')
    if set(session['startup_files']) != {'init', 'opt/wifi-cycle/startup.py',
            'opt/wifi-cycle/cycle-controller.py', 'opt/wifi-cycle/respond-once.py',
            'opt/wifi-cycle/check-retained-patches.py', 'opt/wifi-cycle/capture-export.py',
            'opt/wifi-cycle/capture-device.py'}:
        raise ValueError('startup source inventory mismatch')
    for value in session['startup_files'].values():
        digest_field(value)
    for key in ('kernel_release', 'kernel_version', 'cpu_online'):
        if not isinstance(session[key], str) or not session[key] or '\n' in session[key]:
            raise ValueError('missing startup expectation')
    return cycle.bytes


def check_runtime(session):
    mark('kernel-identity')
    if platform.machine() != 'aarch64' or platform.release() != session['kernel_release']:
        raise ValueError('kernel ABI or release mismatch')
    if text('proc/version') != session['kernel_version']:
        raise ValueError('kernel version mismatch')
    # Bind the selected cycle to its boot command line; reject duplicate keys.
    words = text('proc/cmdline').split()
    mark('boot-parameters')
    if any(word.partition('=')[0] == 'sysrq_always_enabled' for word in words):
        raise ValueError('SysRq override present')
    for key, expected in {'rdinit': '/init', 'panic': '0', 'cpuidle.off': '1',
                          'wifi_cycle': session['cycle_id']}.items():
        matches = [word.partition('=')[2] for word in words if word.partition('=')[0] == key]
        if matches != [expected]:
            raise ValueError('boot parameter mismatch')
    for path, expected in {
        'proc/sys/kernel/panic': '0',
        'proc/sys/kernel/sysrq': '0',
        'proc/sys/kernel/hotplug': '',
        'sys/module/cpuidle/parameters/off': '1',
        'sys/module/firmware_class/parameters/path': '',
        'sys/devices/system/cpu/online': session['cpu_online'],
    }.items():
        mark('runtime:' + path)
        if text(path) != expected:
            raise ValueError('kernel startup state mismatch')
    import gzip
    mark('kernel-config')
    config = gzip.decompress(file_bytes('proc/config.gz', 262144))
    if sha(config) != session['kernel_config_sha256']:
        raise ValueError('kernel configuration mismatch')
    # Linux PF_KTHREAD is 0x00200000. Empty cmdline alone would also admit zombies.
    mark('process-isolation')
    for process in (ROOT / 'proc').iterdir():
        if not process.name.isdecimal() or process.name == '1':
            continue
        try:
            fields = (process / 'stat').read_text().rsplit(')', 1)[1].split()
        except FileNotFoundError:
            continue
        if not int(fields[6]) & 0x00200000:
            raise ValueError('another userspace process exists')
    mark('network-isolation')
    for interface in (ROOT / 'sys/class/net').iterdir():
        if int((interface / 'flags').read_text(), 16) & 1:
            raise ValueError('a network interface is administratively up')


def prepare():
    mark('input-mounts')
    if os.getpid() != 1 or os.geteuid() != 0:
        raise ValueError('startup requires root PID1')
    for directory in ('lib/firmware', 'vendor/firmware', 'data/nvram',
                      'etc/wifi-cycle', 'opt/wifi-cycle', 'init'):
        if not os.statvfs(ROOT / directory).f_flag & os.ST_RDONLY:
            raise ValueError('startup input mount is writable')
    mark('session')
    raw = file_bytes('etc/wifi-cycle/session.json', 65536)
    session = json.loads(raw)
    cycle = validate_session(session)
    mark('startup-hashes')
    for path, expected in session['startup_files'].items():
        if sha(file_bytes(path, 1048576)) != expected:
            raise ValueError('startup source mismatch')
    mark('input-manifest')
    manifest_raw = file_bytes('etc/wifi-cycle/input-manifest.json', 65536)
    if sha(manifest_raw) != session['input_manifest_sha256']:
        raise ValueError('input manifest mismatch')
    manifest = json.loads(manifest_raw)
    if manifest['runtime_sha256'] != RUNTIME or set(manifest['files']) != set(INPUT_PATHS):
        raise ValueError('private input inventory mismatch')
    mark('private-inputs')
    for path, size in INPUT_PATHS.items():
        expected = manifest['files'][path]
        value = file_bytes(path, size)
        if len(value) != size or expected['size'] != size or sha(value) != expected['sha256']:
            raise ValueError('private input bytes mismatch')
    mark('input-lookups')
    for directory in ('lib/firmware', 'vendor/firmware', 'data/nvram'):
        actual = {str(p.relative_to(ROOT)) for p in (ROOT / directory).rglob('*') if p.is_symlink() or not p.is_dir()}
        if actual != {p for p in INPUT_PATHS if p.startswith(directory + '/')}:
            raise ValueError('alternate input exists')
    if os.path.lexists(ROOT / 'storage') or os.path.lexists(ROOT / 'data/misc/wifi/wifi.cfg'):
        raise ValueError('earlier WLAN lookup exists')
    check_runtime(session)
    boot = uuid.UUID(text('proc/sys/kernel/random/boot_id')).bytes
    identity = cycle + bytes.fromhex(sha(raw)) + boot + bytes.fromhex(sha(manifest_raw))
    return session, identity


def main():
    if os.getpid() != 1:
        raise SystemExit('requires candidate PID1; no standalone run')
    mark('python-entry')
    try:
        log_stage('entered')
        session, identity = prepare()
        if session['startup_action'] == 'boot-entry':
            raise ValueError('boot-entry control requires its dedicated init')
        mark('preflight')
        log_stage('passed')
        if session['startup_action'] == 'export':
            mark('export-import')
            spec = importlib.util.spec_from_file_location('capture_device', ROOT / 'opt/wifi-cycle/capture-device.py')
            device = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(device)
            # Intentionally retain the open serial descriptor while PID1 parks.
            device.export_snapshot(sys.modules[__name__], session, identity)
            mark('export')
            log_stage('queued')
            print('wifi-startup: snapshot queued; host preservation required', flush=True)
            while True:
                time.sleep(3600)
        mark('cycle-import')
        spec = importlib.util.spec_from_file_location('cycle', ROOT / 'opt/wifi-cycle/cycle-controller.py')
        controller = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(controller)
        mark('detector-open')
        fd = os.open(ROOT / 'dev/wmtdetect', os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            # Opening the detector is not initialization; recheck immediately before takeover.
            check_runtime(session)
            mark('cycle')
            result = controller.run_cycle(fd, identity, session['kernel_release'],
                                          ROOT / 'lib/firmware', CHIP, VERSION)
        finally:
            os.close(fd)
        print('wifi-startup: ' + result['stage'] + '; recovered classification required', flush=True)
    except BaseException as error:
        try:
            log_stage('stopped')
        except BaseException:
            pass  # Logging failure must still leave PID1 parked.
        # Never print private input contents or hashes into the console.
        try:
            print('wifi-startup: stopped (' + type(error).__name__ + '); no retry', flush=True)
        except OSError:
            pass
    while True:
        time.sleep(3600)  # Before takeover, wait for the owner; afterward, retain the watchdog cutoff.


if __name__ == '__main__':
    main()
