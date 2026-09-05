#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the guarded shutdown script with all device operations injected."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SHELL = json.loads(os.environ.get('GEMINI_TEST_SHELL', '["sh"]'))


def main():
    cases = ('pass', 'kernel', 'boot', 'online', 'offline', 'identity',
             'lifecycle', 'snapshots', 'frequency', 'mounts')
    source = (HERE / 'remote-recovery-shutdown.sh').read_text()
    assert source.count('BB=/bin/busybox') == 1
    with tempfile.TemporaryDirectory(prefix='gemini-recovery-shutdown-', dir='/tmp') as tmp:
        root = Path(tmp); adapter = root / 'bb'; events = root / 'events'
        adapter.write_text('''#!/bin/sh
case "$1" in
 uname) if [ "$CASE" = kernel ]; then echo wrong; else echo 7.1.3-gemini-thermal-snapshot; fi; exit;;
 cat)
  case "$2" in
   /proc/sys/kernel/random/boot_id) key=boot; value=056703de-bf29-4956-891e-ff69d19fdd68;;
   /sys/devices/system/cpu/online) key=online; value=0-9;;
   /sys/devices/system/cpu/offline) key=offline; value=;;
   */gemini_admission/status) key=unused; value=fixture-status;;
   */mt6797_temperature_snapshot_status) key=snapshots; value='abi=1 attempts=3 limit=3';;
   *) echo forbidden-cat >> "$EVENTS"; exit 90;;
  esac
  if [ "$CASE" = "$key" ]; then echo wrong; else printf '%s\\n' "$value"; fi; exit;;
 od) if [ "$CASE" = identity ]; then echo wrong; else echo 7d67a19b3ae40ae1521293d7ffc834e6d06ae14a2d55de693ee9c815bdaee552; fi; exit;;
 sha256sum)
  cat >/dev/null
  if [ "$CASE" = lifecycle ]; then echo wrong; else echo 8aac24ee30576659fe7d4ffb5e58d17dab087165bf1dc3e6f6d800593e310044; fi; exit;;
 dmesg)
  echo GEMINI_A72_FREQUENCY_OBSERVATION_V1
  echo GEMINI_A72_FREQUENCY_OBSERVATION_V1
  [ "$CASE" = frequency ] || echo GEMINI_A72_FREQUENCY_OBSERVATION_V1
  exit 0;;
 awk) if [ "$CASE" = mounts ]; then echo 1; else echo 0; fi; exit;;
 sync|poweroff) printf '%s\\n' "$*" >> "$EVENTS"; exit;;
 tr|grep|printf) ;;
 *) echo forbidden-operation >> "$EVENTS"; exit 91;;
esac
if [ -n "${GEMINI_TEST_BUSYBOX:-}" ]; then exec "$GEMINI_TEST_BUSYBOX" "$@"; fi
exec "$@"
''')
        adapter.chmod(0o700)
        for case in cases:
            events.write_text('')
            env = os.environ | {'CASE': case, 'EVENTS': str(events), 'TEST_BB': str(adapter)}
            outcome = subprocess.run(SHELL, input=source.replace('BB=/bin/busybox', 'BB=$TEST_BB'),
                                     env=env, text=True, capture_output=True)
            assert (outcome.returncode == 0) == (case == 'pass'), (case, outcome.stderr)
            assert events.read_text() == ('sync\npoweroff -f\n' if case == 'pass' else ''), case
            assert ('__THERMAL_RECOVERY_SHUTDOWN_END__' in outcome.stdout) == (case == 'pass')
    print('recovery_shutdown_guard_cases=10 actual_shutdowns=0 device_action=none')


if __name__ == '__main__':
    main()
