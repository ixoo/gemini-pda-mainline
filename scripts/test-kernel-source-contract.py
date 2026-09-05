#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Source selection and backward-compatible package provenance refusals."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from kernel_source_contract import check_provenance, load_manifest, normalize, resolve


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.source = dict(version='7.3-rc1', released='2026-09-05',
                           source_url='https://example.invalid/linux.tar.gz',
                           sha256='a' * 64, archive_format='tar.gz',
                           archive_root='linux-test', git_commit='b' * 40)
        self.manifest = {'schema': 1, 'kernel': dict(self.source),
                         'config': {'default_profile': 'full',
                                    'profiles': {'full': {}, 'topic': {'kernel': self.source}}}}

    def test_legacy_metadata_remains_checksum_only(self):
        for metadata in ({'sha256': 'a' * 64}, {'version': 'test', 'sha256': 'a' * 64}):
            for profiled in (False, True):
                with self.subTest(metadata=metadata, profiled=profiled):
                    manifest = copy.deepcopy(self.manifest)
                    manifest['kernel'] = metadata
                    build = {'source_sha256': 'a' * 64}
                    if profiled:
                        build['build_profile'] = 'full'
                    else:
                        manifest['config'] = {'base': 'defconfig'}
                    self.assertEqual(check_provenance(manifest, build)['selection'], 'global')
                    build['source_sha256'] = 'c' * 64
                    with self.assertRaisesRegex(ValueError, 'source_sha256 does not match'):
                        check_provenance(manifest, build)

    def test_complete_tuple_on_global_and_override(self):
        for profile in ('full', 'topic'):
            build = {'build_profile': profile, 'source_sha256': 'a' * 64,
                     'kernel_source': dict(self.source)}
            check_provenance(self.manifest, build)
            for key in self.source:
                mutated = copy.deepcopy(build)
                del mutated['kernel_source'][key]
                with self.subTest(profile=profile, missing=key), self.assertRaises(ValueError):
                    check_provenance(self.manifest, mutated)
                mutated['kernel_source'][key] = 'different'
                with self.subTest(profile=profile, changed=key), self.assertRaises(ValueError):
                    check_provenance(self.manifest, mutated)

    def test_override_cannot_omit_provenance_or_merge_fallback(self):
        build = {'build_profile': 'topic', 'source_sha256': 'a' * 64}
        with self.assertRaises(ValueError):
            check_provenance(self.manifest, build)
        for value in (None, {}, {'sha256': 'a' * 64}):
            manifest = copy.deepcopy(self.manifest)
            manifest['config']['profiles']['topic']['kernel'] = value
            with self.assertRaises(ValueError):
                resolve(manifest, 'topic')

    def test_selected_override_does_not_use_global_digest(self):
        self.manifest['kernel']['sha256'] = 'c' * 64
        build = {'build_profile': 'topic', 'source_sha256': 'a' * 64,
                 'kernel_source': dict(self.source)}
        check_provenance(self.manifest, build)
        build['source_sha256'] = 'c' * 64
        with self.assertRaises(ValueError):
            check_provenance(self.manifest, build)

    def test_legacy_defaults(self):
        source = {k: v for k, v in self.source.items()
                  if k not in {'archive_format', 'archive_root', 'git_commit'}}
        result = normalize(source)
        self.assertEqual(result['archive_format'], 'tar.xz')
        self.assertEqual(result['archive_root'], 'linux-7.3-rc1')

    def test_duplicate_json_refused(self):
        with tempfile.TemporaryDirectory(prefix='kernel-source-test-') as root:
            path = Path(root) / 'manifest.json'
            path.write_text('{"schema": 1, "schema": 1}')
            with self.assertRaises(ValueError):
                load_manifest(path)
            path.write_text(json.dumps(self.manifest))
            self.assertEqual(load_manifest(path), self.manifest)

    def test_existing_profiles_select_identical_global_source(self):
        manifest = load_manifest(Path(__file__).resolve().parents[1] / 'kernel/manifest.json')
        for name, profile in manifest['config']['profiles'].items():
            if 'kernel' not in profile:
                self.assertEqual(resolve(manifest, name)['kernel'], normalize(manifest['kernel']))


if __name__ == '__main__':
    unittest.main()
