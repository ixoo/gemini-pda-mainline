#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Extract only the optional-file function; never execute the remote probe."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[3] / 'artifacts/a53-authenticated/development/swap-probe-tests'


class OptionalConfigTests(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.temp = tempfile.TemporaryDirectory(prefix='case-', dir=WORK)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'optional'
        source = (HERE / 'probe-swap-prerequisite.sh').read_text()
        self.assertEqual(source.count('# BEGIN OPTIONAL_CONFIG\n'), 1)
        self.assertEqual(source.count('# END OPTIONAL_CONFIG\n'), 1)
        self.function = source.split('# BEGIN OPTIONAL_CONFIG\n')[1].split('# END OPTIONAL_CONFIG\n')[0]

    def run_function(self, prefix=''):
        # No other probe code is included; all paths stay in this fixture root.
        return subprocess.run(['bash', '-c', 'set -euo pipefail\n' + prefix + self.function +
                               '\noptional_config "$1"', 'fixture', str(self.path)],
                              capture_output=True, timeout=3)

    def test_absent_optional_configuration_is_explicit_success(self):
        result = self.run_function()
        self.assertEqual((result.returncode, result.stdout), (0, b'optional_config_state=absent\n'))

    def test_regular_configuration_hash(self):
        raw = b'# harmless fixture\n'
        self.path.write_bytes(raw)
        result = self.run_function()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, ('optional_config_state=regular\noptional_config_sha256=' +
                                        hashlib.sha256(raw).hexdigest() + '\n').encode())

    def test_directory_fifo_and_dangling_symlink_refuse(self):
        self.path.mkdir()
        self.assertNotEqual(self.run_function().returncode, 0)
        self.path.rmdir()
        os.mkfifo(self.path)
        self.assertNotEqual(self.run_function().returncode, 0)
        self.path.unlink()
        self.path.symlink_to(self.path.parent / 'absent')
        result = self.run_function()
        self.assertEqual((result.returncode, result.stdout), (1, b'optional_config_state=unsafe-type\n'))

    def test_symlink_to_regular_file_refuses(self):
        real = self.path.parent / 'real'
        real.write_text('fixture\n')
        self.path.symlink_to(real)
        self.assertNotEqual(self.run_function().returncode, 0)

    def test_oversized_configuration_refuses(self):
        self.path.write_bytes(b'x' * 65537)
        self.assertEqual(self.run_function().stdout, b'optional_config_state=invalid-size\n')

    def test_failed_or_malformed_hash_refuses(self):
        self.path.write_text('fixture\n')
        for replacement in ('sha256sum() { return 1; }\n', 'sha256sum() { printf "invalid\\n"; }\n'):
            with self.subTest(replacement=replacement):
                self.assertNotEqual(self.run_function(replacement).returncode, 0)

    def test_unreadable_count_refuses(self):
        self.path.write_text('fixture\n')
        result = self.run_function('wc() { return 1; }\n')
        self.assertEqual(result.stdout, b'optional_config_state=unreadable\n')

    def test_malformed_size_refuses(self):
        self.path.write_text('fixture\n')
        for value in ('broken', '-1', '080000', '999999999'):
            with self.subTest(value=value):
                result = self.run_function("wc() { printf '%s\\n' '" + value + "'; }\n")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'optional_config_state=invalid-size\n')

    def test_final_identity_check_follows_optional_config(self):
        source = (HERE / 'probe-swap-prerequisite.sh').read_text()
        call = source.index('optional_config /etc/fstab || config_ok=no')
        check = source.index('[[ $(cat /proc/sys/kernel/random/boot_id) == "$EXPECTED_BOOT_ID" ]]', call)
        self.assertLess(call, check)
        self.assertLess(check, source.index('[[ $config_ok == yes ]]', check))


if __name__ == '__main__':
    unittest.main()
