#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""build-candidate.py inserts exactly the pinned helper into the RAM root.

Loads the composer without running it, builds a synthetic parent RAM root with
the inherited newc encoder, and checks add_helper(): the member lands at
bin/join-connect with iw's ownership and mode and the helper's bytes, every
other member is unchanged, the encoded archive re-parses with one more member,
and a wrong digest, wrong size, missing iw, or an already present helper is
refused. The pinned digest and size must match the staged binary's record.
"""
import hashlib
import importlib.util
import runpy
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('phase_b_composer', HERE / 'build-candidate.py')
composer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composer)
validator = runpy.run_path(str(REPO / 'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))
parse, Member = validator['parse_newc'], validator['Member']  # one load: one Member class
encode = runpy.run_path(str(REPO / 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/build-diagnostic-initramfs.py'))['encode_newc']

assert composer.HELPER_PATH == 'bin/join-connect' and composer.HELPER_BYTES == 665552
assert composer.HELPER_SHA256 == 'bc499f28bc052a24713ead3175e5b6405e2e5f787acf276e4e82c1278241d5ca'
# The script pins the same digest before running the helper.
script = (HERE / 'join-once.sh').read_text()
assert (composer.HELPER_SHA256 + '  bin/join-connect') in script

def member(mode, data):
    return Member(mode=mode, uid=0, gid=0, nlink=1, mtime=0, devmajor=0, devminor=0,
                  rdevmajor=0, rdevminor=0, data=data)

helper = bytes([0x7f, ord('E'), ord('L'), ord('F')]) + bytes(composer.HELPER_BYTES - 4)
# A synthetic helper with the pinned size but another digest must be refused,
# so the positive case patches the pin to the synthetic digest.
synthetic_sha = hashlib.sha256(helper).hexdigest()
old = {'init': member(0o100755, b'#!/bin/sh\n'), 'bin/iw': member(0o100755, b'iw'),
       'lib/libc.so.6': member(0o100644, b'libc')}
try:
    composer.add_helper(old, helper)
except ValueError:
    pass
else:
    raise AssertionError('a helper with another digest was accepted')
composer.HELPER_SHA256 = synthetic_sha
new = composer.add_helper(old, helper)
assert set(new) == set(old) | {'bin/join-connect'} and all(new[k] == old[k] for k in old)
added = new['bin/join-connect']
assert added.mode == 0o100755 and added.uid == 0 and added.gid == 0 and added.nlink == 1 and added.data == helper
encoded = encode(new)
assert parse(encoded) == new and len(parse(encoded)) == len(old) + 1
for bad_root, bad_helper in ((old, helper[:-1]),                                   # wrong size
                             (dict(old, **{'bin/join-connect': added}), helper),   # already present
                             ({k: v for k, v in old.items() if k != 'bin/iw'}, helper)):  # no iw
    try:
        composer.add_helper(bad_root, bad_helper)
    except (ValueError, KeyError):
        continue
    raise AssertionError('invalid helper insertion accepted')
try:
    composer.add_helper(dict(old, **{'bin/iw': replace(old['bin/iw'], mode=0o100644)}), helper)
except ValueError:
    pass
else:
    raise AssertionError('iw ownership change accepted')
# add_cli() inserts the pinned wpa_cli next to iw with the same metadata, round-trips with
# one more member, and refuses a wrong size, an already present leaf or a missing iw.
assert composer.CLI_PATH == 'bin/wpa_cli' and composer.CLI_BYTES == 798352
assert composer.CLI_SHA256 == '04fdf3ae5615f7831461028331bcc6c62d7c6d6974c2676f5b3a93960e5afd22'
cli = bytes([0x7f, ord('E'), ord('L'), ord('F')]) + bytes(composer.CLI_BYTES - 4)
composer.CLI_SHA256 = hashlib.sha256(cli).hexdigest()
with_cli = composer.add_cli(new, cli)
assert set(with_cli) == set(new) | {'bin/wpa_cli'} and all(with_cli[k] == new[k] for k in new)
c = with_cli['bin/wpa_cli']
assert c.mode == 0o100755 and c.uid == 0 and c.gid == 0 and c.nlink == 1 and c.data == cli
assert len(parse(encode(with_cli))) == len(new) + 1
for bad_root, bad_cli in ((new, cli[:-1]), (with_cli, cli), ({k: v for k, v in new.items() if k != 'bin/iw'}, cli)):
    try:
        composer.add_cli(bad_root, bad_cli)
    except (ValueError, KeyError):
        continue
    raise AssertionError('invalid wpa_cli insertion accepted')
print('composer helper: PASS (pinned digest/size, iw ownership copied, one extra member re-parses, invalid cases refused)')
