#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind only the corrected thermal profile; preserve other selector branches."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PROFILE = 'gemini-thermal-v4-corrected'
IDENTITY = 'f789e69598a86a9f2522b4fc5c408f7c972d88396da10b018156a66bc8337e22'
SOURCE_SHA = '7c10406276beaa58e282f40f0e937a0c1408fa8e495f1f1f003828663716006c'
OLD = '\t0x8fe1675a22f82e9e, 0xfbc38a994a95eaae,\n\t0xb32fbc46b6fad425, 0x61f3e01d3097b3a5,'
NEW = '\t0xf789e69598a86a9f, 0x2522b4fc5c408f7c,\n\t0x972d88396da10b01, 0x8156a66bc8337e22,'


def identity(profile):
    rows = [f'profile={PROFILE}', f'base={profile["base"]}']
    rows += [hashlib.sha256((ROOT / f).read_bytes()).hexdigest() + '  ' + f
             for f in profile['fragments']]
    return hashlib.sha256(('\n'.join(rows) + '\n').encode()).hexdigest()


def selector(source):
    lines = source[source.index('#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)'):].splitlines()
    depth = 0
    for n, line in enumerate(lines):
        if line.startswith(('#if ', '#ifdef ', '#ifndef ')):
            depth += 1
        elif line.startswith('#endif'):
            depth -= 1
            if not depth:
                return '\n'.join(lines[:n+1]) + '\n'
    raise ValueError('unclosed selector')


def selected(source, frequency, thermal):
    prefix = ('#define IS_ENABLED(x) x\n'
              f'#define CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER {frequency}\n'
              f'#define CONFIG_MTK_SOC_THERMAL_OBSERVER {thermal}\n')
    text = subprocess.run(['cpp', '-P'], input=prefix+selector(source), text=True,
                          capture_output=True, check=True).stdout
    values = re.findall(r'0x([0-9a-f]{16})', text)
    if len(values) != 4:
        raise ValueError('selector identity shape')
    return ''.join(values)


def validate(original, output):
    if output.count(NEW) != 1 or output.replace(NEW, OLD) != original:
        raise ValueError('edit escaped exact config-input identity')
    for frequency in (0, 1):
        for thermal in (0, 1):
            expected = IDENTITY if frequency and thermal else selected(original, frequency, thermal)
            if selected(output, frequency, thermal) != expected:
                raise ValueError('selector branch changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path)
    args = parser.parse_args()
    profile = json.loads((ROOT/'kernel/manifest.json').read_text())['config']['profiles'][PROFILE]
    if identity(profile) != IDENTITY:
        raise ValueError('runtime configuration identity changed')
    path = args.source_root/'arch/arm64/kernel/mt6797_psci.c'
    original = path.read_text()
    if path.is_symlink() or hashlib.sha256(original.encode()).hexdigest() != SOURCE_SHA or original.count(OLD) != 1:
        raise ValueError('production source identity changed')
    output = original.replace(OLD, NEW)
    validate(original, output)
    rejected = 0
    mutations = [original, output.replace('0xf789e69598a86a9f', '0xe789e69598a86a9f'),
                 output.replace('0x18ded825be6993a5', '0x08ded825be6993a5'),
                 output.replace('0x2e50cc09d2241006', '0x3e50cc09d2241006')]
    for bad in mutations:
        try:
            validate(original, bad)
        except ValueError:
            rejected += 1
        else:
            raise ValueError('unsafe selector mutation survived')
    reordered = dict(profile, fragments=list(reversed(profile['fragments'])))
    missing = dict(profile, fragments=profile['fragments'][:-1])
    if identity(reordered) == IDENTITY or identity(missing) == IDENTITY:
        raise ValueError('fragment mutation retained identity')
    path.write_text(output)
    print('profile_selector_cases=4\nsource_mutations_rejected='+str(rejected))
    print('profile_mutations_rejected=2\nconfig_input_identity='+IDENTITY)
    print('corrected_psci_sha256='+hashlib.sha256(output.encode()).hexdigest())


if __name__ == '__main__':
    main()
