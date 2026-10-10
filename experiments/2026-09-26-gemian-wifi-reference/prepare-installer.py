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
    'v3': {
        'candidate': '3e4663373b8b0519a06642ac5ddef4223f2a31b28aca8446bfbe2a59b6a456ea',
        'manifest': '1499b7a3b5c83dd2d57203df77c3cdefd0dc871c2545965bb91b0500eab5b817',
        'predecessor': '4ec72c2012387a3f3f89b9272b357920507767ebbd76f4b66133293b12470f8e',
        'deployment': 'gemian-wifi-reference-deployment-3',
        'boot_id': '7d372eb9-23ca-48af-91b3-8b5e9112c943',
        'release': '3.18.41-gemini-wifi-ref2+',
    },
    'v4': {
        'candidate': 'b1916ae329cdd6a7672a138d3d9673749279678d975255496fa411283ea9a886',
        'manifest': 'ee2ba185ba1b1c800e3c26eddccf181689121225daa1870ff59b3474cf8d13c5',
        'predecessor': '3e4663373b8b0519a06642ac5ddef4223f2a31b28aca8446bfbe2a59b6a456ea',
        'deployment': 'gemian-wifi-reference-deployment-4',
        'boot_id': 'b3c9ecab-08ae-4c08-9c6a-17ef92972c77',
        'release': '3.18.41-gemini-wifi-ref3+',
    },
    'v5': {
        'candidate': 'cf9707c7b4259140f575568ddeec658065eae45bae2e4bd6811d5849a5df70ff',
        'manifest': '0fd1f55580d760c6408f42f78fe5577414c07c1aeec77c709f33766905532c19',
        'predecessor': 'b1916ae329cdd6a7672a138d3d9673749279678d975255496fa411283ea9a886',
        'deployment': 'gemian-wifi-reference-deployment-5',
        'boot_id': 'd298cdbb-7d1f-450f-930a-d40068bde3fa',
        'release': '3.18.41-gemini-wifi-ref4+',
    },
    'v6': {
        'candidate': 'f6218df7bc55b00218d2b9ac3e2cac61a1903486b753ff90bf51dcd1687eee7b',
        'manifest': '109cf4365427459a40765b61625e0cc3f5da45c6853c625effc0f9e9ce53fc90',
        'predecessor': 'cf9707c7b4259140f575568ddeec658065eae45bae2e4bd6811d5849a5df70ff',
        'deployment': 'gemian-wifi-reference-deployment-6',
        'boot_id': '767b1414-855e-4060-ba19-a3458cad1268',
        'release': '3.18.41-gemini-wifi-ref5+',
    },
    'v7': {
        'candidate': '893a938ca1052310be0f91e0040eb45918b07c0e54919aafb6186922e774247d',
        'manifest': 'f69e40a409de87a135395c0b5cb1114172d3f671ae0695710db96170f5fae8de',
        'predecessor': 'f6218df7bc55b00218d2b9ac3e2cac61a1903486b753ff90bf51dcd1687eee7b',
        'deployment': 'gemian-wifi-reference-deployment-7',
        'boot_id': 'b1fd6865-042c-4fc1-9b03-0477bf4f0670',
        'release': '3.18.41-gemini-wifi-ref6+',
    },
    'v8': {
        'candidate': 'f106361945822b3d9093c10de8503901a51c310cfaa7beb87cc56c2152cae6b2',
        'manifest': '77815100b174f16b9bd848852c1b6897388da89adee02db8f11fbf6e80109c0e',
        'predecessor': '893a938ca1052310be0f91e0040eb45918b07c0e54919aafb6186922e774247d',
        'deployment': 'gemian-wifi-reference-deployment-8',
        'boot_id': '678aad0e-34f5-4134-8ac1-92ee9feed207',
        'release': '3.18.41-gemini-wifi-ref7+',
    },
    'v9': {
        'candidate': 'cad42c1fe0bfb2d099edbaf26322ef00da6452e3fdf4a41258e75d3b44b1803a',
        'manifest': '990139e768e27f92135662a3e57444038a7215652c05391bcaafdf3b23534fa2',
        'predecessor': '8e6d80e9c22b658ee8e79c7e4813d0ad80365d26907f2c374a69a2193c1c9049',
        'deployment': 'gemian-wifi-reference-deployment-9',
        'boot_id': '77d578c4-b0bf-458e-ae16-d002c86e784e',
        'release': '3.18.41+',
    },
    'v10': {
        # The installed Phase B candidate 19 is the boot2 predecessor; the current
        # stock Gemian boot is the verified installing boot.
        'candidate': '8d3289a10b7956d7fb55f4d74f0b1902f507cbadfdf6b20ebac654030df2d55f',
        'manifest': '7e9a9e3642c98d0eb8c5f904c394538b2586654e63b9dbd88bd38a51a2fe6e17',
        'predecessor': '5d9aa34b72cf3d8c86a53e7e000ec91f4478d52449c617c9e006f618232c560a',
        'deployment': 'gemian-wifi-reference-deployment-10',
        'boot_id': 'cf68b54a-7a3d-4949-8e1e-db1784cdc7df',
        'release': '3.18.41+',
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
    if args.revision in ('v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10'):
        source = replace(source,
                         '[[ "$initial_boot_id" =~ ^[0-9a-f-]{36}$ ]] || die \'malformed initial boot ID\'\n',
                         '[[ "$initial_boot_id" == ' + selected['boot_id'] + ' ]] ||\n'
                         '\tdie \'not the verified predecessor Gemian boot\'\n')
        source = replace(source,
                         '[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||\n'
                         "\tfail 'remote is not exact known-good Gemian'\n",
                         '[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 &&\n'
                         '   "$(uname -r)" == ' + selected['release'] + ' ]] ||\n'
                         "\tfail 'remote is not the verified predecessor Gemian release'\n")
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
