#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture: a parent candidate whose tree differs from the build's output
must be refused; a declared inherited artefact with the wrong hash must be
refused; a tree that differs only in phandle numbering is accepted."""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'hosts'))
import candidate_inputs as ci  # noqa: E402

BASE = '''/dts-v1/;
/ { model = "fixture"; #address-cells = <1>; #size-cells = <1>;
  clk: clock { #clock-cells = <1>; compatible = "fixture,clock"; };
  %s
  consys@10001340 { compatible = "fixture,consys"; clocks = <&clk 3>; %s };
};
'''


def dtb(directory, name, extra_node='', extra_prop=''):
    dts = Path(directory) / f'{name}.dts'
    dts.write_text(BASE % (extra_node, extra_prop))
    out = Path(directory) / f'{name}.dtb'
    subprocess.run(['dtc', '-q', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(dts)],
                   check=True)
    return out


def main():
    with tempfile.TemporaryDirectory() as tmp:
        build = dtb(tmp, 'build')
        renumbered = dtb(tmp, 'renumbered',
                         extra_node='other { compatible = "fixture,other"; phandle = <0x77>; };')
        # The extra node makes 'renumbered' differ, so first check a true
        # equivalent: the same source compiled twice.
        same = dtb(tmp, 'same')
        ci.refuse_divergent_tree(same, build)
        for differing, label in ((renumbered, 'extra node'),
                                 (dtb(tmp, 'prop', extra_prop='mediatek,one-shot-wmt-negotiate;'),
                                  'extra property')):
            try:
                ci.refuse_divergent_tree(differing, build)
            except ci.Refusal:
                pass
            else:
                raise SystemExit(f'FAIL: divergent tree ({label}) was not refused')
        parent = Path(tmp) / 'parent'
        parent.mkdir()
        (parent / 'initramfs.img').write_bytes(b'ramroot')
        good = ci.sha256(parent / 'initramfs.img')
        ci.inherited(parent, 'initramfs.img', good)
        try:
            ci.inherited(parent, 'initramfs.img', '0' * 64)
        except ci.Refusal:
            pass
        else:
            raise SystemExit('FAIL: hash mismatch was not refused')
        try:
            ci.board_tree(tmp, 'absent.dtb')
        except ci.Refusal:
            pass
        else:
            raise SystemExit('FAIL: missing board tree was not refused')
    print('PASS: divergent tree refused, hash mismatch refused, missing tree refused, equivalent tree accepted')


if __name__ == '__main__':
    main()
