#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pinned-source and patch-scope tests; this does not compile or execute C."""
import json
from pathlib import Path
import runpy
import unittest

HERE = Path(__file__).resolve().parent
API = runpy.run_path(str(HERE / 'derive-topic.py'))
FETCH = runpy.run_path(str(HERE / 'audit-inputs.py'))['fetch']
SOURCES = {}


class Derivation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((HERE.parent / 'derivation-inputs.json').read_text())
        for entry in manifest['remote']:
            SOURCES[entry['path']] = FETCH(entry)
        cls.stages = API['expected_stages'](lambda entry: SOURCES[entry['path']])

    def test_exact_phase_footprints(self):
        clk = API['CLK']
        expected = [
            {clk + 'reset.c', clk + 'reset-internal.h'},
            {clk + 'Kconfig', clk + 'Makefile', clk + 'reset-test.c'},
            {API['BINDING'], API['SCHEMA']},
            {clk + 'clk-mt6797.c', clk + 'clk-mt6797-reset.h'},
            {clk + 'Kconfig', clk + 'Makefile', clk + 'clk-mt6797-reset-test.c'},
            {API['DTS']},
        ]
        for i, paths in enumerate(expected):
            with self.subTest(phase=API['PHASES'][i]):
                self.assertEqual({name for name, text in self.stages[i + 1].items()
                                  if self.stages[i].get(name) != text}, paths)

    def test_every_changed_parent_refused(self):
        for path in SOURCES:
            with self.subTest(path=path):
                def mutated(entry):
                    source = SOURCES[entry['path']]
                    return source + '\n' if entry['path'] == path else source
                with self.assertRaisesRegex(ValueError, 'pinned derivation input mismatch'):
                    API['expected_stages'](mutated)

    def test_repeated_phase_refused(self):
        for i, phase in enumerate(API['PHASES']):
            with self.subTest(phase=phase):
                with self.assertRaises(ValueError):
                    API['phase_edits'](self.stages[i + 1], phase)

    def test_ambiguous_anchor_refused(self):
        with self.assertRaises(ValueError):
            API['replace']('anchor\nanchor', 'anchor', 'replacement')

    def test_missing_anchor_refused(self):
        with self.assertRaises(ValueError):
            API['replace']('other', 'anchor', 'replacement')

    def test_unknown_phase_refused(self):
        with self.assertRaises(ValueError):
            API['phase_edits'](self.stages[0], 'unknown')

    def test_registration_precedes_platform_clock_mutation(self):
        source = self.stages[-1][API['CLK'] + 'clk-mt6797.c']
        init = source.split('static int mtk_infrasys_init(', 1)[1].split('\n}\n', 1)[0]
        self.assertLess(init.index('mtk_register_reset_controller_with_dev'),
                        init.index('if (!infra_clk_data)'))
        self.assertIn('if (ret)\n\t\treturn ret;', init)

    def test_no_consumer_or_toprgu_additions(self):
        before = self.stages[0][API['DTS']]
        after = self.stages[-1][API['DTS']]
        self.assertEqual(after.replace('\t\t#reset-cells = <1>;\n', ''), before)
        header = self.stages[-1][API['BINDING']]
        self.assertNotIn('TOPRGU', header)
        self.assertEqual(sum(line.startswith('#define MT6797_')
                             for line in header.splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
