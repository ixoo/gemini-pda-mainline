#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The data-phase wait ends on a failed join and nowhere else (join_failure_exit.py)."""
from pathlib import Path
import os
import runpy
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent.parent
MODULE = runpy.run_path(str(HERE/'hosts/join_failure_exit.py'), run_name='join_failure_exit')
STUB = '''#!/bin/sh
cmd=$1; shift
case "$cmd" in
  cat) [ "$1" = /proc/sys/kernel/random/boot_id ] && { echo test-boot; exit 0; }; exec cat "$@";;
  dmesg) cat "$DMESG_FILE"; exit 0;;
  *) exec "$cmd" "$@";;
esac
'''
RUN = '''BB=$ROOT/bb; EXPECTED_BOOT=test-boot
data_re='one-shot WLAN native-diag: state=2 '
terminal_re='one-shot WLAN join cleanup: stage=3 '
now_s() { date +%s; }
. "$ROOT/wait_record.sh"
deadline=$(( $(now_s) + 20 ))
wpa_log=$ROOT/wpa.log
[ -z "$BOUND" ] || join_bound_s=$BOUND
wait_record "$PATTERN" 1
'''


def render():
    leaf = (HERE/'join-ccmp-p2.sh').read_text()
    assert leaf.count(MODULE['ANCHOR']) == 1
    return leaf.replace(MODULE['ANCHOR'], MODULE['ANCHOR'] + MODULE['ADDED'])


@unittest.skipUnless(shutil.which('dash') or shutil.which('sh'), 'a POSIX shell is required')
class JoinFailureExitTests(unittest.TestCase):
    def run_wait(self, wpa, dmesg, pattern, bound=''):
        with tempfile.TemporaryDirectory() as root:
            r = Path(root)
            (r/'bb').write_text(STUB); (r/'bb').chmod(0o700)
            body = render()
            start = body.index('wait_record() {')
            (r/'wait_record.sh').write_text(body[start:body.index('\n}\n', start) + 3])
            (r/'wpa.log').write_text(wpa); (r/'dmesg').write_text(dmesg)
            (r/'run.sh').write_text(RUN)
            env = dict(os.environ, ROOT=root, DMESG_FILE=str(r/'dmesg'), PATTERN=pattern, BOUND=bound)
            return subprocess.run([shutil.which('dash') or shutil.which('sh'), str(r/'run.sh')],
                                  env=env, capture_output=True, text=True, timeout=30)

    def test_supplicant_end_of_join_ends_the_data_wait(self):
        for phrase in ('Deauthentication notification', 'CTRL-EVENT-DISCONNECTED', 'Auto connect disabled'):
            result = self.run_wait('wlan0: %s\n' % phrase, '', 'one-shot WLAN native-diag: state=2 ')
            self.assertEqual(result.returncode, 5, phrase)
            self.assertIn('join_failure_exit reason=supplicant', result.stdout)

    def test_bound_ends_the_data_wait(self):
        result = self.run_wait('', '', 'one-shot WLAN native-diag: state=2 ', bound='1')
        self.assertEqual(result.returncode, 6)
        self.assertIn('join_failure_exit reason=bound', result.stdout)

    def test_data_record_wins_and_other_waits_are_unchanged(self):
        self.assertEqual(self.run_wait('wlan0: Deauthentication notification\n',
                                       'one-shot WLAN native-diag: state=2 act=0\n',
                                       'one-shot WLAN native-diag: state=2 ').returncode, 0)
        self.assertEqual(self.run_wait('wlan0: Deauthentication notification\n',
                                       'one-shot WLAN join cleanup: stage=3 x\n',
                                       'one-shot WLAN join cleanup: stage=3 ').returncode, 0)

    def test_rendered_leaf_is_valid_shell(self):
        with tempfile.NamedTemporaryFile('w', suffix='.sh') as f:
            f.write(render()); f.flush()
            self.assertEqual(subprocess.run([shutil.which('dash') or shutil.which('sh'), '-n', f.name]).returncode, 0)


if __name__ == '__main__':
    unittest.main()
