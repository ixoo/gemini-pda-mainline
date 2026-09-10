#!/bin/sh
# SPDX-License-Identifier: MIT
# Run only inside the isolated temporary runtime root, after dropping privileges.
# shellcheck disable=SC3045 # The pinned BusyBox ash supplies these ulimit flags.
set -eu
[ "$#" -eq 1 ]
ulimit -c 0
ulimit -t 6
ulimit -v 262144
ulimit -n 64
export LC_ALL=C
/usr/bin/python3.11 -I -B - "$1" <<'PY'
import hashlib
import os
import platform
import struct
import sys
import threading
import time

assert os.getuid() != 0 and os.geteuid() == os.getuid()
assert not os.getgroups()
assert os.sched_getaffinity(0) == {0}
assert platform.machine() == 'aarch64' and platform.release() == sys.argv[1]
assert struct.calcsize('P') == 8 and sys.byteorder == 'little'
assert threading.active_count() == 1
assert all(not os.path.exists(path) for path in ('/dev', '/proc', '/sys', '/run', '/init'))
assert hashlib.sha256(b'abc').hexdigest() == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
start = time.monotonic_ns()
time.sleep(0.001)
assert time.monotonic_ns() > start
print('native_runtime=' + sys.version.split()[0])
print('native_kernel=' + platform.release())
print('abi_hash_clock_privilege_affinity_isolation=pass')
PY
/usr/bin/python3.11 -I -B /opt/wifi-cycle/test-cycle-controller.py
/usr/bin/python3.11 -I -B /opt/wifi-cycle/test-respond-once.py
printf 'native_runtime_fixtures=pass\n'
