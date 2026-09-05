# SPDX-License-Identifier: MIT
"""Reuse the reviewed strict block-identity receipt for this candidate only."""
import argparse
import hashlib
from pathlib import Path
import re
import runpy
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PARSER = REPO / 'experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_deployment_receipt.py'


def receipt(raw, candidate, candidate_manifest):
    if not all(re.fullmatch(r'[0-9a-f]{64}', value) for value in (candidate, candidate_manifest)):
        raise ValueError('candidate receipt binding format')
    if PARSER.is_symlink() or hashlib.sha256(PARSER.read_bytes()).hexdigest() != '2ef4fc09a11207e2f43cce9c1d328905b636d618c72f3ab76325ef766201c5b7':
        raise ValueError('reviewed receipt parser changed')
    # Identity substitution is confined to a complete, single experiment field.
    # No V4 observation budget or candidate identity is reused.
    original = 'experiment=a53-authenticated-baseline'
    lines = raw.splitlines()
    if lines.count(original) != 1 or any(line.startswith('experiment=') and line != original for line in lines):
        raise ValueError('wrong or duplicate baseline experiment receipt')
    binding = 'candidate_manifest_sha256=' + candidate_manifest
    if lines.count(binding) != 1 or any(line.startswith('candidate_manifest_sha256=') and line != binding for line in lines):
        raise ValueError('wrong or duplicate candidate manifest receipt binding')
    translated = '\n'.join('experiment=2026-09-04-mt6797-thermal-snapshot' if line == original else line
                           for line in lines if line != binding)
    return runpy.run_path(str(PARSER))['receipt'](translated, candidate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--candidate-sha256', required=True)
    parser.add_argument('--candidate-manifest-sha256', required=True)
    args = parser.parse_args()
    try:
        if args.receipt.is_symlink() or not args.receipt.is_file():
            raise ValueError('unsafe receipt file')
        receipt(args.receipt.read_text(), args.candidate_sha256, args.candidate_manifest_sha256)
    except (OSError, ValueError) as error:
        parser.exit(2, 'deployment receipt refused: ' + str(error) + '\n')
    print('deployment_receipt=pass')


if __name__ == '__main__':
    main()
