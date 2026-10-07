#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""join-once.sh names the failing prerequisite on stderr and gates NO-IR after the scan.

Runs a test copy of the script under busybox ash with a stub busybox so that
early prerequisites fail in a controlled order, asserting an empty stdout and a
single __STAGE_FAIL__ line on stderr naming the stage. Static assertions keep
the success path's stdout prefix unchanged, keep 'no IR' out of the pre-scan
gate (channel 40 is NO-IR under the world domain until a beacon is found) and
require the post-scan NO-IR gate before any connect. No device action.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SOURCE = (HERE / 'join-once.sh').read_text()

# Static review.
assert SOURCE.count('BB=/bin/busybox\n') == 1
pre = SOURCE[SOURCE.index('stage=channel40_pre_scan'):SOURCE.index('stage=wlan0_add')]
assert "grep -Eq 'disabled|radar detection'" in pre and 'no IR' not in pre
post = SOURCE[SOURCE.index('stage=channel40_ir_after_beacon'):SOURCE.index('stage=join_readiness')]
assert "grep -Eq 'disabled|no IR|radar detection'" in post and 'exit 1' in post
assert SOURCE.index('stage=channel40_ir_after_beacon') < SOURCE.index('/bin/join-connect wlan0')
assert SOURCE.index('__IW_PASSIVE_BEGIN__') < SOURCE.index('stage=channel40_ir_after_beacon')
# Only the exit trap prints the stage marker, and only to stderr.
markers = [m.start() for m in re.finditer('__STAGE_FAIL__', SOURCE)]
assert len(markers) == 1 and SOURCE[markers[0]:].split('\n')[0].rstrip().endswith('>&2')
before_begin = SOURCE[:SOURCE.index("__IW_PASSIVE_BEGIN__")]
prints = [l for l in before_begin.splitlines() if re.match(r'\s*(\$BB )?printf', l) and '>&2' not in l]
assert all('wc -c' in l or 'grep' in l or 'TARGET_BSSID' in l for l in prints), prints
# An absent target is reported as bss_match, distinct from a failed passive scan.
assert SOURCE.index('[ "$scan_exit" = 0 ]') < SOURCE.index('stage=bss_match') < SOURCE.index('$BB awk -v target')
# The connect's diagnostics stay inside the framed stdout body, so a refused
# join cannot be read as a failed scan by the inherited stderr check.
connect = [l for l in SOURCE.splitlines() if '/bin/join-connect wlan0' in l]
assert len(connect) == 1 and connect[0].rstrip().endswith('2>&1'), connect
assert 'iw dev wlan0 connect' not in SOURCE and 'key' not in connect[0], 'no iw connect, no key'
assert ' 5200 "$TARGET_BSSID"' in connect[0] and 'timeout 3' in connect[0]
# The helper is pinned with the other userspace tools before use.
sums = SOURCE[SOURCE.index("<<'SUMS'"):SOURCE.index('\nSUMS\n')]
assert sums.count('  bin/join-connect') == 1 and SOURCE.index('bin/join-connect\nSUMS') < SOURCE.index('/bin/join-connect wlan0')
stages = re.findall(r'^stage=([a-z0-9_]+)$', SOURCE, re.M)
assert all(re.fullmatch(r'[a-z0-9_]+', s) for s in stages) and len(set(stages)) == len(stages)
assert stages[:4] == ['start', 'target_input', 'kernel_release', 'boot_identity'] and 'connect' in stages

busybox = shutil.which('busybox')
if not busybox or subprocess.run([busybox, 'ash', '-c', 'true']).returncode:
    print('join-once: PASS (static only; busybox ash unavailable here)')
    sys.exit(0)

with tempfile.TemporaryDirectory(prefix='mt6797-join-once-') as directory:
    work = Path(directory)
    stub = work / 'busybox'
    stub.write_text('#!/bin/sh\n'
                    'cmd=$1; shift\n'
                    'case $cmd in\n'
                    '  uname) printf "%s\\n" "$FAKE_RELEASE" ;;\n'
                    '  cat) printf "%s\\n" "$FAKE_BOOT" ;;\n'
                    '  *) exec ' + busybox + ' "$cmd" "$@" ;;\n'
                    'esac\n')
    stub.chmod(0o700)
    script = work / 'join-once.sh'
    script.write_text(SOURCE.replace('BB=/bin/busybox\n', 'BB=' + str(stub) + '\n', 1))
    env = dict(os.environ, TARGET_SSID='x', TARGET_BSSID='02:00:00:00:00:01',
               FAKE_RELEASE='7.1.3-gemini-a53-wifi-phase-b-compile', FAKE_BOOT='boot-a')

    def run(**overrides):
        e = dict(env, **overrides)
        e.pop('EXPECTED_BOOT', None) if overrides.get('EXPECTED_BOOT') == '' else None
        return subprocess.run([busybox, 'ash', str(script)], env=e, capture_output=True, timeout=30)

    def expect(result, stage):
        assert result.returncode != 0 and result.stdout == b'', result
        lines = result.stderr.splitlines()
        assert lines[-1] == ('__STAGE_FAIL__ stage=%s rc=%d' % (stage, result.returncode)).encode(), result.stderr
        assert sum(b'__STAGE_FAIL__' in l for l in lines) == 1

    expect(run(EXPECTED_BOOT=''), 'target_input')
    expect(run(EXPECTED_BOOT='boot-a', FAKE_RELEASE='other'), 'kernel_release')
    expect(run(EXPECTED_BOOT='boot-b'), 'boot_identity')
    # With identity satisfied the next gate needs /sys/class/ieee80211/phy0, absent here.
    result = run(EXPECTED_BOOT='boot-a')
    expect(result, 'single_phy0')
print('join-once: PASS (stage marker on stderr only, empty stdout; NO-IR gated after the beacon)')
