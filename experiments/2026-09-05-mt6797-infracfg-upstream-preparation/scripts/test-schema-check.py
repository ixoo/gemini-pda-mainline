#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic schema-gate fixtures; never execute make, dtschema or a kernel."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).with_name('schema-check.py')
spec = importlib.util.spec_from_file_location('schema_check', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gemini-schema-fixture-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve()

    def test_plan_scope(self):
        commands = m.plan()
        self.assertEqual([c['name'] for c in commands], ['dt_binding_check', 'dtbs_check',
                         'explicit-mt6797-evb', 'explicit-mt6797-x20-dev'])
        for c in commands[:2]:
            self.assertEqual(c['timeout'], 300)
            self.assertIn('-j1', c['argv'])
            self.assertIn('DT_SCHEMA_FILES=clock/mediatek,infracfg.yaml', c['argv'])
            self.assertNotIn('Image', c['argv'])
            self.assertNotIn('clean', c['argv'])
        for c in commands[2:]:
            self.assertEqual(c['timeout'], 30)
            self.assertEqual(c['argv'][c['argv'].index('-l') + 1], m.C['schema_filter'])
            self.assertIn('-v', c['argv'])

    def test_default_is_only_plan(self):
        r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, timeout=5, check=True)
        self.assertEqual(json.loads(r.stdout)['execution'], 'not requested')

    def test_dtb_node_contract(self):
        node = ('infracfg@10001000', [b'mediatek,mt6797-infracfg'], b'\0\0\0\1')
        self.assertEqual(m.inspect_reset_properties([node])['reset_cells'], 1)
        for nodes in [[], [node, node], [('wrong', [b'mediatek,other'], b'\0\0\0\1')],
                      [('infra', node[1], None)], [('infra', node[1], b'\0\0\0\2')],
                      [('infra', node[1], b'\1')]]:
            with self.subTest(nodes=nodes), self.assertRaises(m.Refusal): m.inspect_reset_properties(nodes)

    def test_processed_schema_contract(self):
        p = self.path / 'schema.json'
        schema_id = m.C['schema_id']
        entry = {'$id': schema_id, 'properties': {'compatible': {'const': 'mediatek,mt6797-infracfg'}}}
        p.write_text(json.dumps({schema_id.rstrip('#'): entry}))
        self.assertEqual(m.check_processed(p), m.sha(p))
        for data in [[], {}, {schema_id.rstrip('#'): {}}, {schema_id.rstrip('#'): {'$id': schema_id}},
                     {schema_id.rstrip('#'): dict(entry, **{'$id': 'wrong'})}]:
            p.write_text(json.dumps(data))
            with self.subTest(data=data), self.assertRaises(m.Refusal): m.check_processed(p)

    def test_nonzero_timeout_and_survivor_refusals(self):
        good = {'returncode': 0, 'stop_reason': None, 'cleanup': {'group_absent': True},
                'elapsed_seconds': 1, 'timeout_seconds': 300}
        m.accepted_command(good)
        for key, value in [('returncode', 1), ('stop_reason', 'timeout'), ('elapsed_seconds', 301),
                           ('cleanup', {'group_absent': False})]:
            bad = dict(good);bad[key] = value
            with self.subTest(key=key), self.assertRaises(m.Refusal): m.accepted_command(bad)

    def test_protected_files(self):
        c = copy.deepcopy(m.C)
        source, build = self.path / 'source', self.path / 'build'
        source.mkdir();build.mkdir()
        c['source_root'], c['build_root'] = str(source), str(build)
        for filename, value in [('.gemini-source-state', c['source_state']),
                                ('.gemini-source-integrity', c['source_integrity'])]:
            (source / filename).write_text(value + '\n')
        for root, key in [(source, 'source_files'), (build, 'protected_build_files')]:
            c[key] = {'fixture': hashlib.sha256(b'fixture').hexdigest()}
            (root / 'fixture').write_bytes(b'fixture')
        m.check_files(c)
        (build / 'fixture').write_bytes(b'changed')
        with self.assertRaises(m.Refusal): m.check_files(c)
        (build / 'fixture').unlink();(build / 'fixture').symlink_to(source / 'fixture')
        with self.assertRaises(m.Refusal): m.check_files(c)

    def test_collector_only_fake_process(self):
        lock = self.path / 'lock'
        lock.write_text('fixture-lock')
        descriptor = os.open(lock, os.O_RDONLY)
        self.addCleanup(os.close, descriptor)
        cmd = {'name': 'fixture', 'argv': [sys.executable, '-c',
               f'import os;print(os.read({descriptor},64).decode())'], 'timeout': 2}
        with m.guard.interruption_guard() as state:
            facts = m.collect(cmd, self.path, os.environ.copy(), descriptor, state)
        m.accepted_command(facts)
        self.assertEqual((self.path / 'fixture.stdout').read_text().strip(), 'fixture-lock')

    def test_lock_contention_refuses_before_tools(self):
        persistent = self.path / 'gemini-pda-buildbox'
        persistent.mkdir();lock = persistent / 'build.lock';lock.write_text('')
        descriptor = os.open(lock, os.O_RDONLY)
        self.addCleanup(os.close, descriptor)
        m.fcntl.flock(descriptor, m.fcntl.LOCK_EX | m.fcntl.LOCK_NB)
        with mock.patch.object(m.sys, 'platform', 'linux'), \
             mock.patch.object(m.Path, 'home', return_value=self.path), \
             mock.patch.object(m, 'check_tools') as check:
            with self.assertRaises(BlockingIOError): m.execute(self.path / 'unused-output')
            check.assert_not_called()
        self.assertFalse((self.path / 'unused-output').exists())

    def test_exact_log_ceiling_refuses_even_zero_exit(self):
        lock = self.path / 'lock';lock.write_text('')
        descriptor = os.open(lock, os.O_RDONLY);self.addCleanup(os.close, descriptor)
        cmd = {'name': 'log-ceiling', 'argv': [sys.executable, '-c', 'import os;os.write(1,b"x"*4096)'],
               'timeout': 2}
        c = dict(m.C, log_bytes=4096)
        with m.guard.interruption_guard() as state:
            facts = m.collect(cmd, self.path, os.environ.copy(), descriptor, state, c)
        self.assertEqual(facts['stop_reason'], 'log-limit')
        with self.assertRaises(m.Refusal): m.accepted_command(facts)
        self.assertLessEqual((self.path / 'log-ceiling.stdout').stat().st_size, 4096)

    def test_generated_output_above_log_limit(self):
        lock = self.path / 'lock';lock.write_text('')
        descriptor = os.open(lock, os.O_RDONLY);self.addCleanup(os.close, descriptor)
        generated = self.path / 'generated.json'
        code = "import sys;open(sys.argv[1],'wb').write(b'x'*(17*1024*1024));print('done')"
        cmd = {'name': 'generated', 'argv': [sys.executable, '-c', code, str(generated)], 'timeout': 5}
        with m.guard.interruption_guard() as state:
            facts = m.collect(cmd, self.path, os.environ.copy(), descriptor, state)
        m.accepted_command(facts)
        self.assertEqual(generated.stat().st_size, 17*1024*1024)
        self.assertEqual(facts['generated_file_bytes'], 128*1024*1024)
        self.assertEqual(facts['log_bytes'], 16*1024*1024)
        self.assertEqual((self.path / 'generated.stdout').read_text(), 'done\n')

    def test_each_stream_above_16_mib_is_bounded(self):
        lock = self.path / 'lock';lock.write_text('')
        descriptor = os.open(lock, os.O_RDONLY);self.addCleanup(os.close, descriptor)
        for fd, suffix in [(1, 'stdout'), (2, 'stderr')]:
            cmd = {'name': 'flood-' + suffix, 'argv': [sys.executable, '-c',
                   f'import os;os.write({fd},b"x"*(17*1024*1024))'], 'timeout': 5}
            with m.guard.interruption_guard() as state:
                facts = m.collect(cmd, self.path, os.environ.copy(), descriptor, state)
            self.assertEqual(facts['stop_reason'], 'log-limit')
            self.assertEqual((self.path / (cmd['name'] + '.' + suffix)).stat().st_size, 16*1024*1024)
            self.assertTrue(facts['cleanup']['group_absent'] or facts['cleanup']['term_sent'])
            with self.assertRaises(m.Refusal): m.accepted_command(facts)

    def test_generated_file_ceiling_still_enforced(self):
        lock = self.path / 'lock';lock.write_text('')
        descriptor = os.open(lock, os.O_RDONLY);self.addCleanup(os.close, descriptor)
        generated = self.path / 'too-large'
        cmd = {'name': 'file-ceiling', 'argv': [sys.executable, '-c',
               "import sys;f=open(sys.argv[1],'wb',buffering=0);assert f.write(b'x'*8192)==8192", str(generated)], 'timeout': 2}
        c = dict(m.C, generated_file_bytes=4096)
        with m.guard.interruption_guard() as state:
            facts = m.collect(cmd, self.path, os.environ.copy(), descriptor, state, c)
        self.assertLessEqual(generated.stat().st_size, 4096)
        with self.assertRaises(m.Refusal): m.accepted_command(facts)

    def test_collector_timeout(self):
        lock = self.path / 'lock';lock.write_text('')
        descriptor = os.open(lock, os.O_RDONLY);self.addCleanup(os.close, descriptor)
        cmd = {'name': 'timeout', 'argv': [sys.executable, '-c', 'import time;time.sleep(30)'], 'timeout': .1}
        c = dict(m.C, kill_after_seconds=.1)
        with m.guard.interruption_guard() as state:
            facts = m.collect(cmd, self.path, os.environ.copy(), descriptor, state, c)
        self.assertEqual(facts['stop_reason'], 'timeout')
        with self.assertRaises(m.Refusal): m.accepted_command(facts)


if __name__ == '__main__':
    unittest.main(verbosity=2)
