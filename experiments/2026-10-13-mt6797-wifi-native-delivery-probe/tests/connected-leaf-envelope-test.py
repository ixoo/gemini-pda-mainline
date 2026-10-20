#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual periodic leaf and bound both SSH server envelopes."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent.parent
source = (HERE / 'join-ccmp-p1.sh').read_text()
server = re.search(r'\$BB timeout (\d+) /bin/dropbear .*? -T 2', source, re.S)
assert server is not None
options = server[0]
maximum = int(re.search(r' -M (\d+)', options)[1])
idle = int(re.search(r' -I (\d+)', options)[1])
assert 135 < maximum <= int(server[1]) == 180 and idle == 30
assert source.count("periodic_progress cycle=%s ordinal=%s exit=%s replies=%s\\n") == 1
# Actual leaf code, with only its evidence directory relocated. Dependencies
# supply deterministic successful ping observations and advance the clock to
# each declared slot; neither network nor device access is performed.
body = source.split('periodic_data_checks() {\n', 1)[1].split('\nstage=target_input', 1)[0]
body = 'periodic_data_checks() {\n' + body
anchor = 'pc_dir="/tmp/mt6797-wifi-phase-b-1/c$pc_cyc"'
assert body.count(anchor) == 1
body = body.replace(anchor, 'pc_dir="$TEST_ROOT/c$pc_cyc"')
busybox = shutil.which('busybox')
if busybox is None:
    raise SystemExit('Linux fixture requires busybox; static server-envelope checks passed')
with tempfile.TemporaryDirectory(prefix='connected-leaf-') as td:
    root = Path(td)
    (root / 'c1').mkdir()
    (root / 'c1/router').write_text('192.0.2.1\n')
    wrapper = root / 'bb'
    wrapper.write_text('#!/bin/sh\nif [ "$1" = dmesg ]; then\n'
                       ' printf "one-shot WLAN PM credit clock: ns=1000000000\\n"\n'
                       'else exec ' + busybox + ' "$@"; fi\n')
    wrapper.chmod(0o700)
    script = '''set -eu
BB="$1"
TEST_ROOT="$2"
EXPECTED_BOOT=$($BB cat /proc/sys/kernel/random/boot_id)
deadline=300
now_s() { echo 1; }
window_ok() { return 0; }
periodic_now_ns() { echo "$((pc_clock + pc_sec * 1000000000 + 1000000))"; }
run_bounded() {
    printf '64 bytes from fixture: seq=0 ttl=64 time=1.000 ms\n1 packets transmitted, 1 packets received\n' > "$3"
}
''' + body + '\nperiodic_data_checks 1\n'
    result = subprocess.run(['/bin/sh', '-s', '--', str(wrapper), str(root)],
                            input=script.encode(), capture_output=True, timeout=10)
    assert result.returncode == 0 and not result.stderr, result.stderr
    expected = ''.join('periodic_progress cycle=1 ordinal=%d exit=0 replies=1\n' % n
                       for n in range(1, 12))
    assert result.stdout.decode() == expected
    log = (root / 'c1/ping.log').read_text()
    assert len(re.findall(r'^periodic_ping ', log, re.M)) == 11
    assert [int(n) for n in re.findall(r'scheduled_offset_ns=(\d+)', log)] == list(range(10**10, 111*10**9, 10**10))
print('Actual leaf: 180-second server envelope, 11 bounded numeric progress records and unchanged scheduled probes PASS')
