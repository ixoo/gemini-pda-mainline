#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Phase A host: release overrides and scan selection, offline."""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
private_dir = tempfile.TemporaryDirectory()
private = private_dir.name
os.environ['GEMINI_PRIVATE_REPO'] = private
spec = importlib.util.spec_from_file_location('phase_a_host', HERE / 'passive-host.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)

release = '7.1.3-gemini-a53-wifi-phase-a'
assert host.HOST.DOMAIN.RELEASE == release and host.SCAN.RELEASE == release
assert release.encode() in host.SCAN.PARENT.WIPHY_PROBE
assert b'scan-tuning-sample' not in host.SCAN.PARENT.WIPHY_PROBE
assert host.SCAN.SCAN_SOURCE == HERE / 'phase-a-scan.sh'
assert (b'[ "$kernel" = ' + release.encode() + b' ]') in host.SCAN.SCAN_SOURCE.read_bytes()
for level in (host.SCAN.PARENT, host.HOST, host.HOST.DOMAIN, host.HOST.DOMAIN.HOST):
    assert level.HERE == HERE, level
for level in (host.SCAN, host.SCAN.PARENT, host.HOST, host.HOST.DOMAIN, host.HOST.DOMAIN.HOST):
    assert level.ROOT.parent.name == 'wifi-phase-a', level
for level in (host.SCAN, host.SCAN.PARENT, host.HOST):
    assert level.CAPTURE.name == 'capture-1' and level.CAPTURE.parent.name == 'wifi-phase-a'
# Ready: the scan-injecting prepare. Not ready: the wiphy-probe prepare only.
assert host.select_prepare(True) is host.SCAN.prepare
assert host.select_prepare(False) is host.SCAN.PREPARE
assert host.SCAN.PREPARE.__name__ == 'prepare_with_wiphy'

# Not ready (here: no capture result at all): the session runs directly through
# the scan-free prepare; the inherited host main and the scan are never called.
calls = []


class Finish:
    REPO = None

    def sync_directory(self, path):
        calls.append(('sync', path))


def fake_prepare(candidate):
    calls.append(('prepare', candidate))
    finish = Finish()

    def execute(prepared):
        assert prepared['finish'].REPO == host.PRIVATE_REPO
        host.ROOT.mkdir(parents=True)
        calls.append(('execute',))
        return {'regression_pass': True, 'recovery_confirmed': True}
    return {'finish': finish, 'execute': execute}


def forbidden(*args, **kwargs):
    raise AssertionError('scan host main must not run')


host.SCAN.PREPARE = fake_prepare
host.SCAN.main = forbidden
host.HOST.main = forbidden
sys.argv = ['passive-host.py', '--candidate', '/nonexistent/candidate', '--execute']
assert host.main() == 0
assert [c[0] for c in calls] == ['prepare', 'execute', 'sync']
assert (host.ROOT / 'failure-session-result.json').is_file()
combined = (host.ROOT / 'phase-a-session-result.json').read_text()
assert '"scan_attempted": false' in combined and '"phase_a_capture": null' in combined

# Phase A success: the inherited exit 1 from the obsolete marker becomes 0 only
# when every inherited condition holds with the renamed CONSYS marker.
import json
import shutil
setup = host.SETUP_MARKER
deferred = {'regression_pass': True, 'recovery_confirmed': True,
            'preservation': {'log_complete': True, 'provider_probe': {'registered': True}},
            'deferred_start_records': {'record_counts': {setup.decode(): 1}}}
good_log = b'x ' + setup + b'\ny ' + host.PREPOWER_MARKER + b'\n'


def session(dir_, deferred_, scan_, log_):
    if dir_.exists():
        shutil.rmtree(dir_)
    dir_.mkdir(parents=True)
    (dir_ / 'deferred-start-result.json').write_text(json.dumps(deferred_))
    (dir_ / 'passive-scan-result.json').write_text(json.dumps(scan_))
    (dir_ / 'kmsg.log').write_bytes(log_)
    return dir_


root = Path(private) / 'phase-a-success'
assert host.phase_a_success(session(root, deferred, {'passive_scan_demonstrated': True}, good_log))
assert not host.phase_a_success(session(root, deferred, {'passive_scan_demonstrated': False}, good_log))
assert not host.phase_a_success(session(root, deferred, {'passive_scan_demonstrated': True},
                                        good_log + good_log.split(b'\n')[1] + b'\n'))
assert not host.phase_a_success(session(root, deferred, {'passive_scan_demonstrated': True},
                                        good_log.replace(b'CONSYS after', b'WLAN after')))
for key, value in (('regression_pass', False), ('recovery_confirmed', False)):
    assert not host.phase_a_success(session(root, {**deferred, key: value},
                                            {'passive_scan_demonstrated': True}, good_log))
bad_counts = {**deferred, 'deferred_start_records': {'record_counts': {setup.decode(): 0}}}
assert not host.phase_a_success(session(root, bad_counts, {'passive_scan_demonstrated': True}, good_log))
unsealed = {**deferred, 'preservation': {'log_complete': False, 'provider_probe': {'registered': True}}}
assert not host.phase_a_success(session(root, unsealed, {'passive_scan_demonstrated': True}, good_log))
shutil.rmtree(root)
assert not host.phase_a_success(root)
private_dir.cleanup()
print('phase-a host: release and path overrides at every level; scan only when ready; '
      'direct failure session without capture prerequisites; Phase A success marker')
