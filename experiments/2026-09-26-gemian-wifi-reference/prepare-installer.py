#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed guarded boot2 installer to this exact Gemian candidate."""

import argparse
import hashlib
from pathlib import Path
import runpy
import subprocess


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = REPO / 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh'
DERIVER = REPO / 'experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_installer_guard.py'
GUARD = REPO / 'scripts/boot2-device-guard.sh'
BASE_SHA = 'deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8'
DERIVER_SHA = '9c72675e3043dcf735c8a368800ce9297ca6c343d81283505e7030de82253211'
GUARD_SHA = '0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf'
TRUST_SHA = 'd43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f'
INSTALLS = {
    'v1': {
        'candidate': '138e35e41fa12a3a0cdeca3660e42e291b5268814167c2857a7ad67cffe594b2',
        'manifest': 'eb2443d00e6351290d171cef40550f773fddd31aec294476a36874ee308f1984',
        'predecessor': '991144187d3aaed6cdccef8fe890fafa52b80cfb635fe95adc4dcf04025f5333',
        'deployment': 'gemian-wifi-reference-deployment-1',
    },
    'v2': {
        'candidate': '4ec72c2012387a3f3f89b9272b357920507767ebbd76f4b66133293b12470f8e',
        'manifest': '153724f726465273ef3aec836315014ee1e0e39da6c0a052e37ed79b94ba18ee',
        'predecessor': '138e35e41fa12a3a0cdeca3660e42e291b5268814167c2857a7ad67cffe594b2',
        'deployment': 'gemian-wifi-reference-deployment-2',
    },
}


def digest(path):
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(source, old, new, count=1):
    assert source.count(old) == count, old
    return source.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', choices=INSTALLS, default='v1')
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    selected = INSTALLS[args.revision]
    assert digest(BASE) == BASE_SHA and digest(DERIVER) == DERIVER_SHA
    assert digest(GUARD) == GUARD_SHA
    candidate = args.candidate.resolve(strict=True)
    assert candidate.is_dir() and not args.candidate.is_symlink()
    assert candidate.name == 'candidate-' + selected['candidate']
    assert {p.name for p in candidate.iterdir()} == {
        'boot.img', 'boot2-padded.img', 'candidate.json', 'SHA256SUMS'}
    assert digest(candidate / 'boot2-padded.img') == selected['candidate']
    assert digest(candidate / 'SHA256SUMS') == selected['manifest']
    subprocess.run(['sha256sum', '--check', '--strict', 'SHA256SUMS'], cwd=candidate,
                   check=True, stdout=subprocess.DEVNULL)
    guard = runpy.run_path(str(DERIVER))
    source = guard['derive'](BASE.read_text(), GUARD.read_bytes())
    source = replace(source,
                     'ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02',
                     selected['candidate'])
    source = replace(source,
                     'ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a',
                     selected['manifest'])
    source = replace(source, 'gemian-runtime-provenance-observer-rndis-1d303dda10b4',
                     candidate.name)
    source = replace(source, '2026-08-14-mt6797-runtime-provenance-observer',
                     '2026-09-26-gemian-wifi-reference')
    source = replace(source, 'provenance-observer', 'gemian-wifi-reference', 7)
    source = replace(source, 'gemian-wifi-reference-deployment-*',
                     selected['deployment'], 2)
    source = replace(source, 'gemian-wifi-reference-deployment-N',
                     selected['deployment'])
    source = replace(source, 'ssh_command=(\n\tssh ',
                     'known_trust="$repo_root/artifacts/credentials/a53-recovery-known_hosts"\n'
                     '[[ -f "$known_trust" && ! -L "$known_trust" &&\n'
                     '   "$(sha256sum "$known_trust" | awk \'{print $1}\')" == ' + TRUST_SHA +
                     ' ]] || die \'Gemian host trust changed\'\n'
                     'ssh_command=(\n\tssh -o UserKnownHostsFile="$known_trust" ')
    anchor = '[[ "$predecessor_sha256" =~ ^[0-9a-f]{64}$ && "$live_target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ ]] ||\n\tdie \'unsafe probe result\'\n'
    source = replace(source, anchor, anchor +
                     '[[ "$predecessor_sha256" == ' + selected['predecessor'] +
                     ' || "$predecessor_sha256" == "$CANDIDATE_SHA256" ]] ||\n' +
                     '\tdie \'unexpected boot2 predecessor\'\n')
    output = args.output
    assert output.parent.resolve(strict=True) == REPO / 'artifacts/gemian-wifi-reference/scripts'
    assert not output.exists() and not output.is_symlink()
    output.write_text(source)
    output.chmod(0o700)
    subprocess.run(['bash', '-n', str(output)], check=True)
    subprocess.run(['shellcheck', str(output)], check=True)
    print('installer=' + str(output.resolve(strict=True)))
    print('installer_sha256=' + hashlib.sha256(source.encode()).hexdigest())


if __name__ == '__main__':
    main()
