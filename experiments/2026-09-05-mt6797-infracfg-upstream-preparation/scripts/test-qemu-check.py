#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host fixtures: synthetic packages, KTAP and fake subprocesses; no QEMU."""
import copy
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('qemu-check.py')
spec = importlib.util.spec_from_file_location('qemu_check', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def good_log(order=None):
    c = m.CONTRACT
    lines = ['Linux version ' + c['provenance']['kernel_release'] + ' (fixture)',
             'Kernel command line: ' + c['command_line'], 'KTAP version 1', '1..2']
    for i, suite in enumerate(order or c['suites'], 1):
        lines += ['    KTAP version 1', '    # Subtest: ' + suite, '    1..4']
        lines += [f'    ok {j} {case}' for j, case in enumerate(c['suites'][suite], 1)]
        lines += [f'# {suite}: pass:4 fail:0 skip:0 total:4', f'ok {i} {suite}']
    return '\n'.join(lines + ['reboot: Power down', '']).encode()


def good_exit():
    return {'returncode': 0, 'stop_reason': None, 'elapsed_seconds': 1.0,
            'qmp_capabilities': True, 'qmp_cont': True,
            'qmp_events': [{'event': 'SHUTDOWN', 'data': {'guest': True, 'reason': 'guest-shutdown'}}]}


class LogTests(unittest.TestCase):
    def test_positive_orders_and_timestamp_prefix(self):
        for order in [list(m.CONTRACT['suites']), list(reversed(m.CONTRACT['suites']))]:
            raw = good_log(order)
            self.assertEqual(m.classify_log(raw)['cases_passed'], 8)
            raw = b'\n'.join(b'[    0.123456] ' + line for line in raw.splitlines())
            m.classify_log(raw)

    def test_each_missing_structural_line(self):
        raw = good_log()
        for line in raw.splitlines():
            if line.startswith(b'# '):
                continue
            with self.subTest(line=line), self.assertRaises(m.Refusal):
                m.classify_log(raw.replace(line + b'\n', b'', 1))

    def test_mutations(self):
        raw = good_log()
        first_case = next(iter(m.CONTRACT['suites'].values()))[0].encode()
        cases = [raw + raw, raw.replace(b'1..2', b'1..3'), raw.replace(b'1..4', b'1..5', 1),
                 raw.replace(b'    ok 1 ', b'    not ok 1 ', 1),
                 raw.replace(b'    ok 1 ', b'    ok 2 ', 1),
                 raw.replace(first_case, b'wrong_case'), raw.replace(b'    KTAP', b'  KTAP', 1),
                 raw.replace(b'KTAP version 1', b'TAP version 14', 1),
                 raw.replace(b'fail:0', b'fail:1', 1), raw.replace(b'skip:0', b'skip:1', 1),
                 raw.replace(b'    ok 1 ' + first_case, b'    ok 1 ' + first_case + b' # SKIP'),
                 b'reboot: Power down\n' + raw.replace(b'reboot: Power down\n', b''),
                 raw.replace(b'7.3.0-rc1-', b'7.1.3-'), raw.replace(b'kunit_shutdown=', b'kunit.shutdown='),
                 raw + b'    ok 5 surprise\n', raw + b'\x00', raw + b'\x1b[0m',
                 raw + b'Bail out!\n', raw + b'Kernel panic - fixture\n', raw + b'Oops: fixture\n',
                 raw + b'WARNING: fixture\n', raw + b'BUG: fixture\n', raw + b'x' * m.MAX_LOG]
        for index, candidate in enumerate(cases):
            with self.subTest(mutation=index), self.assertRaises(m.Refusal):
                m.classify_log(candidate)

    def test_exit_refusals(self):
        m.classify_exit(good_exit())
        mutations = [('returncode', 1), ('returncode', -signal.SIGTERM), ('stop_reason', 'timeout'),
                     ('elapsed_seconds', 46), ('elapsed_seconds', 0), ('qmp_capabilities', False),
                     ('qmp_cont', False), ('qmp_events', []),
                     ('qmp_events', good_exit()['qmp_events'] * 2),
                     ('qmp_events', [{'event': 'SHUTDOWN', 'data': {'guest': False, 'reason': 'host-qmp-quit'}}]),
                     ('qmp_events', good_exit()['qmp_events'] + [{'event': 'RESET'}])]
        for key, value in mutations:
            facts = good_exit(); facts[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(m.Refusal):
                m.classify_exit(facts)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gemini-qemu-package-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        (self.path / 'provenance').mkdir()
        (self.path / 'provenance/build.json').write_text(json.dumps(m.CONTRACT['provenance']))
        (self.path / 'Image.gz').write_bytes(b'fixture-image')
        (self.path / 'kernel.config').write_text('\n'.join(x + '=y' for x in m.CONTRACT['enabled_kunit']))
        self.contract = copy.deepcopy(m.CONTRACT)
        self.contract['image_sha256'] = m.digest(b'fixture-image')
        self.reseal()

    def reseal(self):
        paths = sorted(p for p in self.path.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
        raw = ''.join(m.digest(p.read_bytes()) + '  ./' + p.relative_to(self.path).as_posix() + '\n'
                      for p in paths).encode()
        (self.path / 'SHA256SUMS').write_bytes(raw)
        self.contract['inventory_sha256'] = m.digest(raw)

    def test_positive(self):
        self.assertEqual(m.verify_package(self.path, self.contract)['members'], 3)

    def test_changed_image(self):
        (self.path / 'Image.gz').write_bytes(b'changed')
        with self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)
        self.reseal()
        with self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)

    def test_changed_inventory(self):
        with (self.path / 'SHA256SUMS').open('ab') as f: f.write(b'\n')
        with self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)

    def test_missing_extra_symlink_fifo(self):
        p = self.path / 'surprise'
        for kind in ['extra', 'symlink', 'fifo']:
            if kind == 'extra': p.write_text('x')
            elif kind == 'symlink': p.symlink_to(self.path / 'Image.gz')
            else: m.os.mkfifo(p)
            with self.subTest(kind=kind), self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)
            p.unlink()
        (self.path / 'Image.gz').unlink()
        with self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)

    def test_directory_symlink(self):
        (self.path / 'alias').symlink_to(self.path / 'provenance', target_is_directory=True)
        with self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)

    def test_provenance_mutations(self):
        for key in m.CONTRACT['provenance']:
            data = copy.deepcopy(m.CONTRACT['provenance']); data[key] = None
            (self.path / 'provenance/build.json').write_text(json.dumps(data)); self.reseal()
            with self.subTest(key=key), self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)

    def test_unexpected_test(self):
        with (self.path / 'kernel.config').open('a') as f: f.write('\nCONFIG_SURPRISE_KUNIT_TEST=y\n')
        self.reseal()
        with self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)

    def test_traversal_duplicate_and_absolute(self):
        raw = (self.path / 'SHA256SUMS').read_bytes()
        for bad in [raw + raw.splitlines()[0] + b'\n', raw.replace(b'./Image.gz', b'./../escape'),
                    raw.replace(b'./Image.gz', b'.//absolute')]:
            (self.path / 'SHA256SUMS').write_bytes(bad); self.contract['inventory_sha256'] = m.digest(bad)
            with self.subTest(bad=bad[:100]), self.assertRaises(m.Refusal): m.verify_package(self.path, self.contract)


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gemini-qemu-process-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.contract = dict(m.CONTRACT, timeout_seconds=0.4, kill_after_seconds=0.1)

    def run_fake(self, code):
        return m.capture([sys.executable, '-u', '-c', code], self.path, self.contract)

    def test_handshake_and_guest_poweroff(self):
        code = '''import json,sys
print(json.dumps({'QMP': {'version': {}}}), flush=True)
assert json.loads(input()) == {'execute':'qmp_capabilities','id':'caps'}
print(json.dumps({'return':{},'id':'caps'}), flush=True)
assert json.loads(input()) == {'execute':'cont','id':'start'}
print(json.dumps({'return':{},'id':'start'}), flush=True)
print(json.dumps({'event':'SHUTDOWN','data':{'guest':True,'reason':'guest-shutdown'}}), flush=True)
'''
        facts = self.run_fake(code)
        m.classify_exit(facts, self.contract)

    def test_timeout_term_and_kill(self):
        facts = self.run_fake('import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(30)')
        self.assertEqual(facts['stop_reason'], 'timeout')
        self.assertEqual(facts['returncode'], -signal.SIGKILL)
        self.assertLess(facts['elapsed_seconds'], 2)

    def test_invalid_qmp(self):
        facts = self.run_fake('print("not json")')
        self.assertIsNotNone(facts['stop_reason'])
        with self.assertRaises(m.Refusal): m.classify_exit(facts, self.contract)

    def test_truncated_qmp(self):
        facts = self.run_fake('import sys;sys.stdout.write("{\\\"QMP\\\":{}")')
        self.assertIsNotNone(facts['stop_reason'])

    def test_qmp_flood(self):
        facts = self.run_fake('print("x" * 70000)')
        self.assertIsNotNone(facts['stop_reason'])

    def test_qmp_capability_error(self):
        facts = self.run_fake('import json;print(json.dumps({"QMP":{}}),flush=True);input();print(json.dumps({"id":"caps","error":{}}),flush=True)')
        self.assertIsNotNone(facts['stop_reason'])
        self.assertFalse(facts['qmp_cont'])

    def test_command_exclusions(self):
        argv = m.command('qemu-system-aarch64', 'Image.gz', 'serial.log')
        for forbidden in ['-drive', '-blockdev', '-initrd', '-dtb', '-netdev', '-enable-kvm']:
            self.assertNotIn(forbidden, argv)
        self.assertEqual(argv[argv.index('-nic')+1], 'none')
        self.assertEqual(argv[argv.index('-accel')+1], 'tcg')
        self.assertEqual(argv[argv.index('-append')+1], m.CONTRACT['command_line'])

    def test_default_never_executes(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--package', str(self.path)],
                                capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.path / 'serial.log').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
