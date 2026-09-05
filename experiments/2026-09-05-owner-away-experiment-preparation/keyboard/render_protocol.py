#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check or refresh C display strings from the frozen keyboard protocol."""
import argparse
import json
from pathlib import Path

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--write", action="store_true")
args = parser.parse_args()
protocol = json.loads((root / "protocol.json").read_text())
data = ('/* SPDX-License-Identifier: GPL-2.0-only */\n'
        '/* Generated from protocol.json; regenerate with render_protocol.py. */\n'
        'static const char *const instructions[] = {\n' +
        ''.join('\t' + json.dumps(step['instruction']) + ',\n' for step in protocol['steps']) + '};\n')
if args.write:
    (root / 'protocol.h').write_text(data)
elif (root / 'protocol.h').read_text() != data:
    raise SystemExit('protocol.h differs from protocol.json')
print('protocol header exact')
