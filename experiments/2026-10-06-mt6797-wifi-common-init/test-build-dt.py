#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the Phase A DT edit on the built board DT made parent-like."""

import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
builder = runpy.run_path(str(HERE / 'build-candidate.py'))
built = Path(sys.argv[1])
with tempfile.TemporaryDirectory() as tmp:
    board = Path(tmp) / 'board.dtb'
    shutil.copyfile(built, board)
    owner, wifi = builder['OWNER'], builder['WIFI']
    # The booted parent has no VCN33-BT pieces; remove what the build carries.
    tree = builder['nodes'](board)
    bt = [path for path in tree if path.endswith('/ldo-vcn33-bt')]
    assert len(bt) == 1
    subprocess.run(['fdtput', '-d', str(board), owner, 'vcn33-bt-supply'], check=True)
    subprocess.run(['fdtput', '-r', str(board), bt[0]], check=True)
    before = builder['nodes'](board)
    bt_path = builder['edit_dt'](board)
    after = builder['nodes'](board)
    assert bt_path == bt[0], (bt_path, bt[0])
    assert 'mediatek,one-shot-wmt-negotiate' in after[owner]
    assert 'mediatek,one-shot-wmt-common-init' in after[owner]
    assert 'mediatek,one-shot-wmt-identity-capture' not in after[owner]
    assert after[owner]['mediatek,coex-antenna-mode'] == '<0x01>'
    assert after[owner]['reg-names'].endswith('btif-dma-rx\\0afe"')
    assert 'status' not in after[wifi]
    assert after[bt_path]['regulator-name'] == '"vcn33-bt"'
    assert after[owner]['vcn33-bt-supply'] == after[bt_path]['phandle']
    unchanged = [p for p in before if p not in (owner, wifi)]
    assert all(after[p] == before[p] for p in unchanged)
    # A second application is refused: the parent contract no longer holds.
    try:
        builder['edit_dt'](board)
        raise AssertionError('second edit accepted')
    except ValueError:
        pass
print('phase-a dt edit: flags, antenna, AFE, VCN33-BT node and supply, WLAN enable pass')
