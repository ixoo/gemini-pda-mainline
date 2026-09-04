#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the thermal-snapshot profile without changing prior accepted identities."""
from pathlib import Path
import hashlib
import json
import sys
import re
import subprocess

repo = Path(__file__).resolve().parents[3]
name = 'gemini-thermal-snapshot-candidate'
profile = json.loads((repo/'kernel/manifest.json').read_text())['config']['profiles'][name]
identity_input = [f'profile={name}', f'base={profile["base"]}']
identity_input += [hashlib.sha256((repo/f).read_bytes()).hexdigest()+'  '+f
                   for f in profile['fragments']]
identity = hashlib.sha256(('\n'.join(identity_input)+'\n').encode()).hexdigest()
assert identity == '8fe1675a22f82e9efbc38a994a95eaaeb32fbc46b6fad42561f3e01d3097b3a5'
p = Path(sys.argv[1])/'arch/arm64/kernel/mt6797_psci.c'
s = p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest() == '4ffbcc572455ed45711643505c5073016c5742892efadc652843ed12bb48daaa'
old = '''#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {
\t0x18ded825be6993a5, 0xa403f8cd526e3682,
\t0x199cc55afce876f3, 0x6b7f194faced0b25,
};'''
new = '''#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
#if IS_ENABLED(CONFIG_MTK_SOC_THERMAL_OBSERVER)
static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {
\t0x8fe1675a22f82e9e, 0xfbc38a994a95eaae,
\t0xb32fbc46b6fad425, 0x61f3e01d3097b3a5,
};
#else
''' + old.split('\n',1)[1] + '\n#endif'
assert s.count(old)==1
s=s.replace(old,new)
# Preprocess the actual selector block; check both preserved and new branches.
block = new.split('\n', 1)[1]
for enabled, expected in ((0, '18ded825be6993a5a403f8cd526e3682199cc55afce876f36b7f194faced0b25'),
                          (1, identity)):
    prefix = '#define IS_ENABLED(x) x\n#define CONFIG_MTK_SOC_THERMAL_OBSERVER ' + str(enabled) + '\n'
    output = subprocess.run(['cpp', '-P'], input=prefix+block, text=True,
                            capture_output=True, check=True).stdout
    observed = ''.join(re.findall(r'0x([0-9a-f]{16})', output))
    assert observed == expected
print('profile_selector_cases=2')
p.write_text(s)
print('config_input_identity='+identity)
