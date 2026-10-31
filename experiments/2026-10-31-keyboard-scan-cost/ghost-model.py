#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Model which key combinations ghost on the Gemini matrix, and whether
# matrix_keypad_has_ghosting() (patch 0365) drops the scan.
# Usage: ghost-model.py FILE  (any file holding the MATRIX_KEY() map)
import re, itertools, sys
m = {}
for r, c, k in re.findall(r'MATRIX_KEY\((\d), (\d), KEY_(\w+)\)', open(sys.argv[1]).read()):
    m[(int(r), int(c))] = k
pos = {k: rc for rc, k in m.items()}
def scan(keys):
    # electrical closure: pressed set plus every point reachable through row/col links
    s = {pos[k] for k in keys}
    while True:
        add = {(r1, c2) for (r1, c1) in s for (r2, c2) in s if (r2, c1) in s} - s
        if not add: return s
        s |= add
def ghost(s):  # mirror of matrix_keypad_has_ghosting
    cols = {}
    for (r, c) in s:
        if (r, c) in m: cols.setdefault(c, set()).add(r)
    return any(len(cols[a] & cols[b]) > 1 for a, b in itertools.combinations(cols, 2))
for combo in [['LEFTCTRL','LEFTSHIFT','N'], ['LEFTCTRL','LEFTSHIFT','X'], ['LEFTCTRL','LEFTSHIFT','C'],
              ['LEFTCTRL','LEFTSHIFT','V'], ['LEFTCTRL','LEFTSHIFT','Z'], ['LEFTCTRL','LEFTALT','7'],
              ['LEFTCTRL','LEFTALT','K'], ['LEFTSHIFT','LEFTMETA','1'], ['LEFTCTRL','A'], ['LEFTALT','A'],
              ['LEFTMETA','B'], ['LEFTMETA','N'], ['RIGHTSHIFT','LEFTMETA','5'], ['LEFTCTRL','RIGHTSHIFT','T']]:
    s = scan(combo)
    phantom = sorted(m.get(p, 'none@%d,%d' % p) for p in s - {pos[k] for k in combo})
    print('%-32s phantom=%-28s filtered=%s' % ('+'.join(combo), ','.join(phantom) or '-', ghost(s)))
