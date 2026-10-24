#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Candidate inputs: the kernel and the board tree come from the build
package; anything a candidate inherits from a parent candidate is declared
with its hash, and composition refuses when a declaration does not match
or when an inherited tree diverges from the build's own output.

Background: from 2026-10-17 to 2026-10-24 every Wi-Fi candidate composer
copied `board.dtb` and `initramfs.img` from its parent candidate, so a
device tree no build produced drifted for a week unnoticed. The RAM root is
still inherited (no kernel build produces it); it is declared here.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

DTDIFF = Path(__file__).resolve().parent.parent / 'tests' / 'dtdiff.py'


class Refusal(Exception):
    """Composition must not proceed."""


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def board_tree(package, name):
    """The board tree the build produced for this candidate."""
    path = Path(package) / 'dtbs' / 'mediatek' / name
    if not path.is_file():
        raise Refusal(f'board tree {name} is not in the package {package}')
    return path


def inherited(parent, name, declared_sha256):
    """An artefact taken from a parent candidate, declared with its hash."""
    path = Path(parent) / name
    if not path.is_file():
        raise Refusal(f'inherited artefact {name} is missing from {parent}')
    actual = sha256(path)
    if actual != declared_sha256:
        raise Refusal(f'inherited artefact {name}: {actual[:12]} does not match '
                      f'its declaration {declared_sha256[:12]}')
    return {'name': name, 'from': str(parent), 'sha256': actual,
            'reason': 'no kernel build produces it'}


def refuse_divergent_tree(inherited_dtb, package_dtb):
    """Refuse when a parent's tree and the build's tree differ beyond
    phandle numbering (nodes or properties)."""
    out = subprocess.run([sys.executable, '-I', str(DTDIFF), str(inherited_dtb),
                          str(package_dtb)], check=True, capture_output=True,
                         text=True).stdout
    if ('nodes only in A (0)' not in out or 'nodes only in B (0)' not in out
            or ' :: ' in out):
        raise Refusal('the inherited tree differs from the build output:\n' + out)
    return out
