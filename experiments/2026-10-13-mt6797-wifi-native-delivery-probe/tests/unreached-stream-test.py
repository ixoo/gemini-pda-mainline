#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""An SSH that never connected leaves a gradable receipt (unreached_stream.py, throughput_verdict.py)."""
from pathlib import Path
import json
import runpy
import tempfile
import unittest

HERE = Path(__file__).resolve().parent.parent
US = runpy.run_path(str(HERE/'hosts/unreached_stream.py'), run_name='unreached_stream')
TV = runpy.run_path(str(HERE/'hosts/throughput_verdict.py'), run_name='throughput_verdict')
TIMED_OUT = b'ssh: connect to host 192.0.2.1 port 22: Operation timed out\r\n'

# The derived helper's shape at the three anchors, reduced to what they touch.
HELPER = '''import json, re
def execute(root, owner, quiesced):
    def argument(b):
        script = 'owners=0'
        if owner is None:
            return script.replace('owners=0', 'owners=1')
        return script
    remote = {'quiesced': quiesced(argument('b'))}
    remote['scope'] = 'exact tagged owner and observed PTY process group/session absent; bounded proc scans'
    return remote

def main():
    pass
'''
RECEIPT = '''CHUNKS = 5
def grade(result, measured, remote, control, directions_ok):
    counter_names = {'rx_packets'}
    for direction in measured.values():
        directions_ok = bool(directions_ok and direction.get('completed') and
                             direction['bytes']>0)
    result['all_pass'] = bool(result['all_pass'] and remote['quiesced'] and
                              control['accepted'] and directions_ok)
    return result
'''


def observation(exit=255, timeout=False, out=b'', err=TIMED_OUT):
    root = Path(tempfile.mkdtemp())
    (root/'process.json').write_text(json.dumps({'exit': exit, 'timeout': timeout}))
    (root/'stdout.bin').write_bytes(out)
    (root/'stderr.bin').write_bytes(err)
    return root


class UnreachedStreamTests(unittest.TestCase):
    def test_only_a_failed_connect_is_unreached(self):
        self.assertTrue(US['unreached'](observation()))
        self.assertTrue(US['unreached'](observation(err=b'ssh: connect to host 192.0.2.1 port 22: Connection refused\n')))
        for case in (dict(exit=0), dict(timeout=True), dict(out=b'x'),
                     dict(err=TIMED_OUT + b'more\n'), dict(err=b'Connection closed by 192.0.2.1 port 22\r\n')):
            self.assertFalse(US['unreached'](observation(**case)), case)
        self.assertFalse(US['unreached'](Path(tempfile.mkdtemp())))

    def apply(self):
        path = Path(tempfile.mkdtemp())/'helper.py'
        path.write_text(HELPER)
        US['apply'](path)
        return runpy.run_path(str(path))

    def test_missing_owner_passes_only_when_unreached(self):
        execute = self.apply()['execute']
        scan = lambda script: script == 'owners=0'
        remote = execute(observation(), None, scan)
        self.assertTrue(remote['quiesced'] and remote['ssh_unreached'])
        self.assertFalse(execute(observation(out=b'x'), None, scan)['quiesced'])
        self.assertNotIn('ssh_unreached', execute(observation(), '42', scan))

    def test_failure_names_survive_a_measurement_that_never_ran(self):
        path = Path(tempfile.mkdtemp())/'helper.py'
        path.write_text(RECEIPT)
        TV['apply_receipt'](path)
        grade = runpy.run_path(str(path))['grade']
        never = {'bytes': None, 'errors': 0, 'chunks': [], 'device_cpu': {'valid': False}}
        result = grade({'all_pass': False}, {'TX': dict(never, bytes=0), 'RX': never},
                       {'quiesced': True}, {'accepted': False}, False)
        self.assertFalse(result['all_pass'])
        self.assertIn('RX.bytes', result['all_pass_failed'])
        self.assertIn('core disconnect', result['all_pass_failed'])
        self.assertNotIn('remote quiescence', result['all_pass_failed'])


if __name__ == '__main__':
    unittest.main()
