#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise only the active-record predicate with inert swap records."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = (HERE / 'temporary-zram.sh').read_text()
FUNCTION = SOURCE[SOURCE.index('active() {'):SOURCE.index('\ninactive() {')]


class AliasTests(unittest.TestCase):
    def test_exact_aliases_and_refusals(self):
        root = HERE.parents[3] / 'artifacts/a53-authenticated/development/swap-alias-tests'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            record = Path(directory) / 'swaps'
            script = FUNCTION.replace('/proc/swaps', '"$FIXTURE_SWAPS"')
            script = 'readlink() { printf "%s\\n" "$FIXTURE_RESOLVED"; }\n' + script + '\nactive\n'
            cases = [('/dev/block/zram0', '/dev/zram0', '0', '-1', True),
                     ('/dev/zram0', '/dev/zram0', '0', '-1', True),
                     ('/dev/block/zram0', '/dev/zram1', '0', '-1', False),
                     ('/dev/zram1', '/dev/zram0', '0', '-1', False),
                     ('/dev/zram0', '/dev/zram0', '1', '-1', False),
                     ('/dev/zram0', '/dev/zram0', '0', '1', False)]
            for path, resolved, used, priority, expected in cases:
                with self.subTest(path=path, resolved=resolved, used=used, priority=priority):
                    record.write_text('Filename Type Size Used Priority\n' +
                                      f'{path} partition 1930336 {used} {priority}\n')
                    result = subprocess.run(['bash', '-c', script],
                                            env=dict(os.environ, FIXTURE_SWAPS=str(record),
                                                     FIXTURE_RESOLVED=resolved),
                                            capture_output=True, timeout=3)
                    self.assertEqual(result.returncode == 0, expected, result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
