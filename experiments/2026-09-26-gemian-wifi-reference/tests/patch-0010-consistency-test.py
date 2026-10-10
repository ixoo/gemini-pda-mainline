#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The host-tested observer sources equal the files patch 0010 adds, byte for byte."""
import pathlib
import re
import unittest

HERE = pathlib.Path(__file__).resolve().parent.parent
PATCH = next(HERE.glob('patches/0010-*.patch'))


def added_file(patch_text, path):
    """The content of a new file in a git patch (every '+' line of its single hunk)."""
    match = re.search(r'^diff --git a/%s b/%s\n(?:.*\n)*?@@[^\n]*\n((?:[+\\].*\n)*)' % (re.escape(path), re.escape(path)),
                      patch_text, re.M)
    assert match, path
    return ''.join(line[1:] + '\n' for line in match.group(1).splitlines() if line.startswith('+'))


class Patch0010Test(unittest.TestCase):
    def test_observer_sources_match_the_patch(self):
        text = PATCH.read_text()
        base = 'drivers/misc/mediatek/connectivity/wlan/gen3/'
        self.assertEqual(added_file(text, base + 'common/gwref10.c'), (HERE / 'lifecycle/gwref10.c').read_text())
        self.assertEqual(added_file(text, base + 'include/gwref10.h'), (HERE / 'lifecycle/gwref10.h').read_text())

    def test_patch_touches_only_the_gen3_driver(self):
        files = re.findall(r'^diff --git a/(\S+) ', PATCH.read_text(), re.M)
        self.assertTrue(files and all(f.startswith('drivers/misc/mediatek/connectivity/wlan/gen3/') for f in files), files)
        self.assertIn('drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_rx.h', files)

    def test_records_are_debug_level_and_markers_info(self):
        source = (HERE / 'lifecycle/gwref10.c').read_text()
        self.assertEqual(source.count('printk(KERN_DEBUG'), 1)
        self.assertEqual(source.count('printk(KERN_INFO'), 3)  # arm, seal, cap
        self.assertNotIn('pr_info', source)
        self.assertNotIn('MAC2STR', source)
        self.assertNotIn('aucKeyMaterial[', source)
        self.assertNotIn('aucKeyRsc[', source)
        self.assertNotIn('%pM', source)


if __name__ == '__main__':
    unittest.main()
