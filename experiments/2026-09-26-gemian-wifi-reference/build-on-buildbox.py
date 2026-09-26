#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the pinned Gemian Wi-Fi reference kernel on Buildbox."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path('/workspace/gemini-pda')
SOURCE_REVISION = '59e00a9144d782e148332009a835b99c43382467'
TOOLCHAIN = 'a45d945f092461a611d276ad7d0a0fea1ea8a7f93db413908bcb892c12817d14'
CONFIG_SHA256 = '231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4'
CUST_SHA256 = '7a7eb416499346afff30c15f967ccb9cf79323c076204b6a953515db74811632'
PATCH = HERE / 'patches/0001-diagnostic-record-Gemian-Wi-Fi-setup-decisions.patch'
CONFIG = REPO / 'experiments/2026-07-23-gemian-a72-owner-observer/inputs/active-gemian.config'

spec = importlib.util.spec_from_file_location(
    'native', REPO / 'experiments/2026-09-07-mt6797-wifi-observer-feasibility/check-startup-objects.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
run, digest = native.run, native.digest


def main():
    assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
    commit = run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'])
    assert len(sys.argv) == 3 and sys.argv[1] == commit
    jobs = int(sys.argv[2])
    assert 1 <= jobs <= 16
    assert not run(['git', '-C', str(REPO), 'status', '--porcelain'])
    assert shutil.disk_usage(ROOT).free > 8 * 1024 ** 3
    assert digest(CONFIG) == CONFIG_SHA256
    assert PATCH.is_file() and not PATCH.is_symlink()
    patch_sha = digest(PATCH)
    package = ROOT / 'gemian-artifacts' / ('gemian-wifi-reference-' + commit)
    if package.exists():
        result = json.loads((package / 'result.json').read_text())
        assert result['repository_commit'] == commit and result['patch_sha256'] == patch_sha
        run(['sha256sum', '--check', '--strict', 'SHA256SUMS'], cwd=package)
        print('package=' + str(package))
        return

    baseline = ROOT / 'gemian-source/gemian-baseline' / SOURCE_REVISION
    assert run(['git', '-C', str(baseline), 'rev-parse', 'HEAD']) == SOURCE_REVISION
    assert not run(['git', '-C', str(baseline), 'status', '--porcelain'])
    source = ROOT / 'gemian-source/gemian-wifi-reference' / patch_sha
    source.parent.mkdir(parents=True, exist_ok=True)
    integrity = [sys.executable, str(REPO / 'scripts/source-tree-integrity')]
    if not source.exists():
        with tempfile.TemporaryDirectory(prefix='gemian-wifi-source-', dir=source.parent) as tmp:
            staged = Path(tmp) / 'source'
            run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(baseline), str(staged)])
            run(['git', '-C', str(staged), 'checkout', '--quiet', '--detach', SOURCE_REVISION])
            run(['git', '-C', str(staged), 'apply', '--check', str(PATCH)])
            run(['git', '-C', str(staged), 'apply', str(PATCH)])
            run(['git', '-C', str(staged), 'diff', '--check'])
            (staged / '.gemini-source-state').write_text(patch_sha + '\n')
            run(integrity + ['write', str(staged)])
            staged.rename(source)
    assert not source.is_symlink()
    assert (source / '.gemini-source-state').read_text() == patch_sha + '\n'
    assert run(['git', '-C', str(source), 'rev-parse', 'HEAD']) == SOURCE_REVISION
    source_integrity = run(integrity + ['verify', str(source)])

    toolchain = ROOT / 'gemian-toolchains' / TOOLCHAIN
    assert (toolchain / 'validated').read_text().strip() == TOOLCHAIN
    cross = str(toolchain / 'wrappers/aarch64-linux-gnu-')
    environment = dict(os.environ, LD_LIBRARY_PATH=str(toolchain / 'root/usr/lib/x86_64-linux-gnu'),
                       HOST_EXTRACFLAGS='-fcommon', PYTHONDONTWRITEBYTECODE='1',
                       KBUILD_BUILD_USER='gemini', KBUILD_BUILD_HOST='buildbox',
                       KBUILD_BUILD_VERSION='1',
                       KBUILD_BUILD_TIMESTAMP='Thu Jan 1 00:00:00 UTC 1970')
    assert run([cross + 'gcc', '--version'], env=environment).splitlines()[0] == (
        'aarch64-linux-gnu-gcc-6 (Debian 6.3.0-18) 6.3.0 20170516')
    assert run([cross + 'ld', '--version'], env=environment).splitlines()[0] == (
        'GNU ld (GNU Binutils for Debian) 2.28')

    with tempfile.TemporaryDirectory(prefix='gemian-wifi-reference-', dir=ROOT / 'build') as tmp:
        work = Path(tmp)
        output = work / 'output'
        output.mkdir()
        shutil.copyfile(CONFIG, output / '.config')
        script_config = source / 'scripts/config'
        for symbol in ('FUNCTION_TRACER', 'FUNCTION_GRAPH_TRACER', 'DYNAMIC_FTRACE'):
            run([str(script_config), '--file', str(output / '.config'), '--enable', symbol])
        run([str(script_config), '--file', str(output / '.config'), '--set-str',
             'LOCALVERSION', '-gemini-wifi-ref'])
        command = ['make', '-C', str(source), 'O=' + str(output), 'ARCH=arm64',
                   'CROSS_COMPILE=' + cross, 'python=' + str(toolchain / 'wrappers/python2.7'),
                   'KCFLAGS=-fstack-usage']
        with (work / 'configure.log').open('w') as stream:
            native.compile_logged(command + ['olddefconfig'], stream,
                                  env=environment, timeout=120)
        before, after = native.symbols(CONFIG), native.symbols(output / '.config')
        delta = {name: [before.get(name), after.get(name)]
                 for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
        assert set(delta) <= {'CONFIG_LOCALVERSION', 'CONFIG_ANBOX',
                              'CONFIG_FUNCTION_TRACER', 'CONFIG_FUNCTION_GRAPH_TRACER',
                              'CONFIG_DYNAMIC_FTRACE', 'CONFIG_GENERIC_TRACER',
                              'CONFIG_CONTEXT_SWITCH_TRACER'}, delta
        assert after['CONFIG_LOCALVERSION'] == '"-gemini-wifi-ref"'
        for symbol in ('FUNCTION_TRACER', 'FUNCTION_GRAPH_TRACER', 'DYNAMIC_FTRACE'):
            assert after['CONFIG_' + symbol] == 'y'
        assert after['CONFIG_MTK_FTRACE_DEFAULT_ENABLE'] == 'n'
        assert after['CONFIG_MTK_COMBO_WIFI'] == 'y'
        assert after['CONFIG_DEBUG_FS'] == 'y'

        dts = output / 'arch/arm64/boot/dts'
        dts.mkdir(parents=True, exist_ok=True)
        with (work / 'dct.log').open('w') as stream:
            native.compile_logged([str(toolchain / 'wrappers/python2.7'), 'DrvGen.py',
                                   str(source / 'drivers/misc/mediatek/dws/mt6797/aeon6797_6m_n.dws'),
                                   str(dts) + '/', str(dts) + '/', 'cust_dtsi'], stream,
                                  cwd=source / 'tools/dct', env=environment, timeout=120)
        cust = dts / 'cust.dtsi'
        normalized, count = re.subn(r'(?m)^ \* \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',
                                    ' * 1970-01-01 00:00:00', cust.read_text())
        assert count == 1
        cust.write_text(normalized)
        assert digest(cust) == CUST_SHA256
        with (work / 'build.log').open('w') as stream:
            native.compile_logged(command + ['-j' + str(jobs), 'V=1', 'Image.gz-dtb'],
                                  stream, env=environment, timeout=3600)
        symbol_map = (output / 'System.map').read_text()
        for symbol in ('wmt_plat_soc_init', 'mtk_wcn_consys_hw_reg_ctrl',
                       'emi_mpu_set_region_protection'):
            assert re.search(r' [Tt] ' + symbol + r'$', symbol_map, re.M), symbol
        assert not run([cross + 'nm', '-u', str(output / 'vmlinux')], env=environment)
        assert run(integrity + ['verify', str(source)]) == source_integrity
        diagnostics = [line for line in (work / 'build.log').read_text().splitlines()
                       if re.search(r'\b(warning|error):', line, re.I)]
        package.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='gemian-wifi-package-', dir=package.parent) as tmp_package:
            staged = Path(tmp_package) / 'package'
            staged.mkdir()
            files = {'config': output / '.config', 'System.map': output / 'System.map',
                     'vmlinux': output / 'vmlinux',
                     'Image.gz-dtb': output / 'arch/arm64/boot/Image.gz-dtb',
                     'cust.dtsi': cust, 'configure.log': work / 'configure.log',
                     'dct.log': work / 'dct.log', 'build.log': work / 'build.log'}
            for name, path in files.items():
                assert path.is_file() and not path.is_symlink() and path.stat().st_size
                shutil.copyfile(path, staged / name)
            (staged / 'diagnostics.txt').write_text('\n'.join(diagnostics) + '\n')
            result = {'repository_commit': commit, 'source_commit': SOURCE_REVISION,
                      'toolchain_sha256': TOOLCHAIN, 'baseline_config_sha256': CONFIG_SHA256,
                      'patch_sha256': patch_sha, 'source_integrity': source_integrity,
                      'config_delta': delta, 'cust_dtsi_sha256': CUST_SHA256,
                      'diagnostic_lines': len(diagnostics), 'full_kernel_link': True,
                      'boot_candidate': False, 'device_execution': False}
            (staged / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            (staged / 'SHA256SUMS').write_text(''.join(
                digest(path) + '  ' + path.name + '\n'
                for path in sorted(staged.iterdir()) if path.name != 'SHA256SUMS'))
            run(['sha256sum', '--check', '--strict', 'SHA256SUMS'], cwd=staged)
            staged.rename(package)
    print('package=' + str(package))


if __name__ == '__main__':
    main()
