#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Source identity refusal fixtures, including every current profile fallback."""
import copy
import json
from pathlib import Path
import unittest
import tempfile
import kernel_source_contract as contract
import profile_inputs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GLOBAL = {'version': '7.1.3', 'released': '2026-07-04',
          'source_url': 'https://cdn.kernel.org/linux-7.1.3.tar.xz', 'sha256': '1' * 64}
OVERRIDE = {'version': '7.3.0-rc1', 'released': '2026-09-05',
            'source_url': 'https://codeload.github.com/torvalds/linux/tar.gz/' + 'a' * 40,
            'sha256': '2' * 64, 'archive_format': 'tar.gz',
            'archive_root': 'linux-' + 'a' * 40, 'git_commit': 'a' * 40}


def fixture():
    return {'schema': 1, 'architecture': 'arm64', 'kernel': dict(GLOBAL), 'config': {
        'default_profile': 'full', 'profiles': {'full': {}, 'upstream': {'kernel': dict(OVERRIDE)}}}}


class SourceContract(unittest.TestCase):
    def test_every_baseline_profile_unchanged(self):
        before = contract.load_manifest(HERE.parent / 'results/baseline-profile-inputs.json')
        result = profile_inputs.compare(before, profile_inputs.snapshot(ROOT))
        self.assertEqual(result['existing_profiles_preserved'], 189)

    def test_profile_inventory_mutations(self):
        before = {'default_profile': 'full', 'profiles': {
            'full': {'effective_inputs_sha256': 'a', 'patch_count': 1, 'fragment_count': 1}}}
        for change in ('default', 'remove', 'patch', 'fragment', 'source'):
            with self.subTest(change=change):
                after = copy.deepcopy(before)
                if change == 'default':
                    after['default_profile'] = 'other'
                elif change == 'remove':
                    after['profiles'].clear()
                elif change == 'patch':
                    after['profiles']['full']['patch_count'] = 2
                elif change == 'fragment':
                    after['profiles']['full']['fragment_count'] = 2
                else:
                    after['profiles']['full']['effective_inputs_sha256'] = 'b'
                with self.assertRaises(ValueError):
                    profile_inputs.compare(before, after)
        after = copy.deepcopy(before)
        after['profiles']['new'] = before['profiles']['full']
        self.assertEqual(profile_inputs.compare(before, after)['added_profiles'], ['new'])

    def test_default_and_explicit_profile(self):
        self.assertEqual(contract.resolve(fixture())['kernel'], contract.normalize(GLOBAL))
        self.assertEqual(contract.resolve(fixture(), 'upstream')['kernel'], OVERRIDE)

    def test_legacy_source_provenance(self):
        manifest = fixture()
        manifest['config'] = {'base': 'defconfig', 'fragments': []}
        self.assertEqual(contract.check_provenance(manifest, {'source_sha256': GLOBAL['sha256']})['selection'], 'global')
        with self.assertRaises(ValueError):
            contract.resolve(manifest, 'full')

    def test_unknown_profile_and_missing_build_profile(self):
        with self.assertRaises(ValueError):
            contract.resolve(fixture(), 'missing')
        with self.assertRaises(ValueError):
            contract.check_provenance(fixture(), {'source_sha256': GLOBAL['sha256']})

    def test_no_partial_override_fallback(self):
        for value in (None, {}, [], 'invalid', True):
            with self.subTest(value=value):
                manifest = fixture()
                manifest['config']['profiles']['upstream']['kernel'] = value
                with self.assertRaises(ValueError):
                    contract.resolve(manifest, 'upstream')
        for field in contract.REQUIRED | contract.ARCHIVE:
            with self.subTest(field=field):
                manifest = fixture()
                del manifest['config']['profiles']['upstream']['kernel'][field]
                with self.assertRaises(ValueError):
                    contract.resolve(manifest, 'upstream')

    def test_mutated_source_fields(self):
        cases = [('sha256', '2'*63), ('sha256', 'X'*64), ('sha256', True),
                 ('version', '../7'), ('version', '7/other'), ('released', '2026-99-01'),
                 ('released', '20260905'), ('source_url', 'http://example.org/source'),
                 ('source_url', 'file:///tmp/source'), ('source_url', 'https://u:p@example.org/source'),
                 ('source_url', 'https://example.org/source?token=x'),
                 ('source_url', 'https://example.org/source#fragment'),
                 ('source_url', 'https://example.org:444/source'),
                 ('source_url', 'https://example.org/\nsource'),
                 ('archive_format', 'zip'), ('archive_root', '../linux-7'),
                 ('archive_root', '/linux-7'), ('archive_root', 'linux-7/child'),
                 ('git_commit', 'HEAD'), ('git_commit', 'a'*39), ('unknown', 'value')]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                manifest = fixture()
                manifest['config']['profiles']['upstream']['kernel'][field] = value
                with self.assertRaises(ValueError):
                    contract.resolve(manifest, 'upstream')

    def test_invalid_global_is_not_masked_by_override(self):
        manifest = fixture()
        del manifest['kernel']['sha256']
        with self.assertRaises(ValueError):
            contract.resolve(manifest, 'upstream')

    def test_same_release_different_source_identity(self):
        manifest = fixture()
        manifest['config']['profiles']['upstream']['kernel']['version'] = GLOBAL['version']
        expected = contract.resolve(manifest, 'upstream')['kernel']
        build = {'build_profile': 'upstream', 'source_sha256': expected['sha256'], 'kernel_source': expected}
        contract.check_provenance(manifest, build)
        build['source_sha256'] = GLOBAL['sha256']
        with self.assertRaises(ValueError):
            contract.check_provenance(manifest, build)

    def test_override_requires_full_provenance(self):
        build = {'build_profile': 'upstream', 'source_sha256': OVERRIDE['sha256']}
        with self.assertRaises(ValueError):
            contract.check_provenance(fixture(), build)
        build['kernel_source'] = dict(OVERRIDE)
        contract.check_provenance(fixture(), build)
        for field in OVERRIDE:
            with self.subTest(field=field):
                altered = copy.deepcopy(build)
                altered['kernel_source'][field] += '-wrong'
                with self.assertRaises(ValueError):
                    contract.check_provenance(fixture(), altered)

    def test_global_provenance_compatibility(self):
        build = {'build_profile': 'full', 'source_sha256': GLOBAL['sha256']}
        contract.check_provenance(fixture(), build)
        build['kernel_source'] = contract.normalize(GLOBAL)
        contract.check_provenance(fixture(), build)
        build['kernel_source']['archive_root'] = 'linux-wrong'
        with self.assertRaises(ValueError):
            contract.check_provenance(fixture(), build)

    def test_effective_input_changes_and_series_relocation(self):
        with tempfile.TemporaryDirectory(prefix='gemini-profile-inputs-', dir='/tmp') as temporary:
            root = Path(temporary)
            (root / 'patches').mkdir()
            (root / 'configs').mkdir()
            (root / 'patches/a.patch').write_text('patch a\n')
            (root / 'patches/b.patch').write_text('patch b\n')
            (root / 'patches/series').write_text('a.patch\nb.patch\n')
            (root / 'configs/base.fragment').write_text('CONFIG_KUNIT=y\n')
            manifest = fixture()
            manifest['patch_series'] = 'patches/series'
            manifest['config']['profiles']['full'] = {'base': 'defconfig',
                'fragments': ['configs/base.fragment']}
            before = profile_inputs.fingerprint(root, manifest, 'full')
            manifest['config']['profiles']['full']['patch_series'] = None
            self.assertEqual(before, profile_inputs.fingerprint(root, manifest, 'full'))
            (root / 'patches/frozen-series').write_text('a.patch\nb.patch\n')
            relocated = copy.deepcopy(manifest)
            relocated['config']['profiles']['full']['patch_series'] = 'patches/frozen-series'
            self.assertEqual(before, profile_inputs.fingerprint(root, relocated, 'full'))
            for name in ('patches/a.patch', 'configs/base.fragment', 'patches/series'):
                with self.subTest(file=name):
                    original = (root / name).read_text()
                    (root / name).write_text('b.patch\na.patch\n' if name.endswith('series') else original + 'changed\n')
                    self.assertNotEqual(before, profile_inputs.fingerprint(root, manifest, 'full'))
                    (root / name).write_text(original)
            for field in ('architecture', 'source', 'base'):
                with self.subTest(field=field):
                    changed = copy.deepcopy(manifest)
                    if field == 'architecture':
                        changed['architecture'] = 'arm'
                    elif field == 'source':
                        changed['kernel']['sha256'] = '3' * 64
                    else:
                        changed['config']['profiles']['full']['base'] = 'tinyconfig'
                    self.assertNotEqual(before, profile_inputs.fingerprint(root, changed, 'full'))

    def test_unsafe_input_paths(self):
        for name in ('/tmp/file', '../file', 'configs/./file', 'configs//file', 'configs/file name'):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    profile_inputs.file_identity(ROOT, name)

    def test_boolean_schema_refused(self):
        manifest = fixture()
        manifest['schema'] = True
        with self.assertRaises(ValueError):
            contract.resolve(manifest)

    def test_duplicate_json_fields(self):
        for text in ('{"kernel": {}, "kernel": {}}', '{"kernel":{"sha256":"a","sha256":"b"}}'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    json.loads(text, object_pairs_hook=contract.unique_object)


if __name__ == '__main__':
    unittest.main()
