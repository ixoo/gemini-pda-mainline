#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Archive inspection refusals; no download or extraction."""
import io
import hashlib
import tempfile
import pathlib
import runpy
import tarfile
import unittest

API = runpy.run_path(str(pathlib.Path(__file__).with_name('acquire-upstream-archive.py')))
ROOT = API['ARCHIVE_ROOT']


class Members(unittest.TestCase):
    def member(self, name, kind=tarfile.REGTYPE, link=''):
        member = tarfile.TarInfo(name)
        member.type = kind
        member.linkname = link
        return member

    def test_regular_and_internal_links(self):
        for member in (self.member(ROOT + '/file'), self.member(ROOT, tarfile.DIRTYPE),
                       self.member(ROOT + '/dir/link', tarfile.SYMTYPE, '../file'),
                       self.member(ROOT + '/hard', tarfile.LNKTYPE, ROOT + '/file')):
            API['safe_member'](member, ROOT)

    def test_unsafe_names(self):
        for name in ('/absolute', '../file', ROOT + '/../file', ROOT + '//file',
                     ROOT + '/./file', 'other/file', ROOT + '/line\nbreak'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                API['safe_member'](self.member(name), ROOT)

    def test_escaping_links(self):
        for kind, target in ((tarfile.SYMTYPE, '../../outside'), (tarfile.SYMTYPE, '/absolute'),
                             (tarfile.LNKTYPE, '../outside'), (tarfile.LNKTYPE, '/absolute')):
            with self.subTest(kind=kind, target=target), self.assertRaises(ValueError):
                API['safe_member'](self.member(ROOT + '/link', kind, target), ROOT)

    def test_archive_content_refusals(self):
        expected = [{'path': 'file', 'bytes': 3, 'sha256': hashlib.sha256(b'abc').hexdigest()}]
        for case in ('valid', 'missing', 'duplicate', 'wrong-content', 'wrong-size', 'wrong-type'):
            with self.subTest(case=case), tempfile.NamedTemporaryFile(suffix='.tar.gz', dir='/tmp') as tmp:
                with tarfile.open(tmp.name, 'w:gz') as archive:
                    if case != 'missing':
                        name = ROOT + '/file'
                        data = b'ab' if case == 'wrong-size' else b'abd' if case == 'wrong-content' else b'abc'
                        member = self.member(name)
                        member.size = len(data)
                        if case == 'wrong-type':
                            member.type = tarfile.SYMTYPE
                            member.linkname = 'other'
                            member.size = 0
                        archive.addfile(member, io.BytesIO(data) if member.isfile() else None)
                        if case == 'duplicate':
                            archive.addfile(member, io.BytesIO(data))
                if case == 'valid':
                    self.assertEqual(API['inspect'](pathlib.Path(tmp.name), expected)['member_count'], 1)
                else:
                    with self.assertRaises(ValueError):
                        API['inspect'](pathlib.Path(tmp.name), expected)

    def test_special_nodes(self):
        for kind in (tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                API['safe_member'](self.member(ROOT + '/device', kind), ROOT)


if __name__ == '__main__':
    unittest.main()
