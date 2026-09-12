#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Buildbox-only complete native controller kernel; never a boot candidate."""
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
PROJECT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('native', HERE / 'check-startup-objects.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
run, digest = native.run, native.digest
ROOT = Path('/workspace/gemini-pda')


def main():
    assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
    commit = run(['git', '-C', str(PROJECT), 'rev-parse', 'HEAD'])
    assert len(sys.argv) == 3 and sys.argv[1] == commit
    jobs = int(sys.argv[2]);assert 1 <= jobs <= 16
    assert not run(['git', '-C', str(PROJECT), 'status', '--porcelain'])
    pins = json.loads((HERE / 'full-kernel-inputs.json').read_text())
    assert pins['source_revision'] == native.REVISION and pins['toolchain_sha256'] == native.TOOLCHAIN
    assert shutil.disk_usage(ROOT).free > 12 * 1024 ** 3
    package = ROOT / 'gemian-artifacts' / ('wifi-controller-kernel-' + commit)
    assert not package.exists(), 'refusing to overwrite a package'
    # Caller holds the shared Buildbox lock; these are only this lane's staging.
    for root, prefix in ((ROOT / 'build', 'wifi-controller-kernel-'),
                         (ROOT / 'gemian-source', 'wifi-controller-prepare-'),
                         (package.parent, 'wifi-controller-package-')):
        for stale in root.glob(prefix + '*'):
            assert stale.is_dir() and not stale.is_symlink(), stale
            shutil.rmtree(stale)
    patches = []
    for item in pins['patches']:
        path = Path(item['path'])
        assert not path.is_absolute() and '..' not in path.parts
        path = PROJECT / path
        assert path.is_file() and not path.is_symlink() and digest(path) == item['sha256']
        patches.append(path)
    assert len(patches) == len(set(patches)) == 47
    identity = digest(HERE / 'full-kernel-inputs.json')
    source = ROOT / 'gemian-source' / ('wifi-controller-' + identity)
    baseline = ROOT / 'gemian-source/gemian-baseline' / native.REVISION
    assert run(['git', '-C', str(baseline), 'rev-parse', 'HEAD']) == native.REVISION
    assert not run(['git', '-C', str(baseline), 'status', '--porcelain'])
    state = json.dumps(pins, sort_keys=True) + '\n'
    integrity = [sys.executable, str(PROJECT / 'scripts/source-tree-integrity')]
    if not source.exists():
        with tempfile.TemporaryDirectory(prefix='wifi-controller-prepare-', dir=source.parent) as tmp:
            staged = Path(tmp) / 'source'
            run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(baseline), str(staged)])
            run(['git', '-C', str(staged), 'checkout', '--quiet', '--detach', native.REVISION])
            for patch in patches:
                run(['git', '-C', str(staged), 'apply', '--check', str(patch)])
                run(['git', '-C', str(staged), 'apply', str(patch)])
            run(['git', '-C', str(staged), 'diff', '--check'])
            (staged / '.gemini-source-state').write_text(state)
            run(integrity + ['write', str(staged)])
            staged.rename(source)
    assert not source.is_symlink()
    assert (source / '.gemini-source-state').read_text() == state
    assert run(['git', '-C', str(source), 'rev-parse', 'HEAD']) == native.REVISION
    source_integrity = run(integrity + ['verify', str(source)])
    # Reuse the prepared source; compilation always owns a separate output tree.
    toolchain = ROOT / 'gemian-toolchains' / native.TOOLCHAIN
    assert (toolchain / 'validated').read_text().strip() == native.TOOLCHAIN
    cross = str(toolchain / 'wrappers/aarch64-linux-gnu-')
    config = PROJECT / 'experiments/2026-07-23-gemian-a72-owner-observer/inputs/active-gemian.config'
    assert digest(config) == pins['baseline_config_sha256']
    environment = dict(os.environ, LD_LIBRARY_PATH=str(toolchain / 'root/usr/lib/x86_64-linux-gnu'),
                       HOST_EXTRACFLAGS='-fcommon', PYTHONDONTWRITEBYTECODE='1', KBUILD_BUILD_USER='gemini',
                       KBUILD_BUILD_HOST='buildbox', KBUILD_BUILD_VERSION='1',
                       KBUILD_BUILD_TIMESTAMP='Thu Jan 1 00:00:00 UTC 1970')
    compiler = run([cross + 'gcc', '--version'], env=environment).splitlines()[0]
    linker = run([cross + 'ld', '--version'], env=environment).splitlines()[0]
    assert compiler == 'aarch64-linux-gnu-gcc-6 (Debian 6.3.0-18) 6.3.0 20170516'
    assert linker == 'GNU ld (GNU Binutils for Debian) 2.28'
    with tempfile.TemporaryDirectory(prefix='wifi-controller-kernel-', dir=ROOT / 'build') as tmp:
        work = Path(tmp);output = work / 'output';output.mkdir()
        shutil.copyfile(config, output / '.config')
        run([str(source / 'scripts/config'), '--file', str(output / '.config'),
             '--enable', 'MTK_A72_RECOVERY_DISCRIMINATOR'])
        command = ['make', '-C', str(source), 'O=' + str(output), 'ARCH=arm64',
                   'CROSS_COMPILE=' + cross, 'python=' + str(toolchain / 'wrappers/python2.7'),
                   'KCFLAGS=-fstack-usage']
        with (work / 'configure.log').open('w') as stream:
            native.compile_logged(command + ['olddefconfig'], stream, env=environment, timeout=120)
        before, after = native.symbols(config), native.symbols(output / '.config')
        delta = {key: [before.get(key), after.get(key)] for key in before.keys() | after.keys()
                 if before.get(key) != after.get(key)}
        assert delta == {'CONFIG_ANBOX': [None, 'n'], 'CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR': [None, 'y']}, delta
        for name in ('CONFIG_PSTORE_PMSG', 'CONFIG_CPU_IDLE', 'CONFIG_CRYPTO_SHA256', 'CONFIG_MTK_COMBO_WIFI'):
            assert after[name] == 'y', name
        assert after['CONFIG_MODULES'] == after['CONFIG_MTK_AEE_MRDUMP'] == 'n'
        dts = output / 'arch/arm64/boot/dts';dts.mkdir(parents=True, exist_ok=True)
        with (work / 'dct.log').open('w') as stream:
            native.compile_logged([str(toolchain / 'wrappers/python2.7'), 'DrvGen.py',
                                   str(source / 'drivers/misc/mediatek/dws/mt6797/aeon6797_6m_n.dws'),
                                   str(dts) + '/', str(dts) + '/', 'cust_dtsi'], stream,
                                  cwd=source / 'tools/dct', env=environment, timeout=120)
        cust = dts / 'cust.dtsi'
        data, count = re.subn(r'(?m)^ \* \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',
                             ' * 1970-01-01 00:00:00', cust.read_text())
        assert count == 1;cust.write_text(data)
        assert digest(cust) == pins['cust_dtsi_sha256']
        with (work / 'build.log').open('w') as stream:
            result = subprocess.run(command + ['-j' + str(jobs), 'V=1', 'Image.gz-dtb'],
                                    stdout=stream, stderr=subprocess.STDOUT,
                                    env=environment, timeout=3600)
        if result.returncode:
            failure = package.with_name(package.name + '-failed')
            assert not failure.exists()
            failure.mkdir()
            for name in ('build.log', 'configure.log', 'dct.log'):
                shutil.copyfile(work / name, failure / name)
            (failure / 'result.json').write_text(json.dumps({
                'project_commit': commit, 'inputs_sha256': identity,
                'build_exit_status': result.returncode, 'boot_candidate': False}) + '\n')
            (failure / 'SHA256SUMS').write_text(''.join(
                digest(p) + '  ' + p.name + '\n' for p in sorted(failure.iterdir())))
            run(['sha256sum', '--check', '--strict', 'SHA256SUMS'], cwd=failure)
            errors = [line for line in (work / 'build.log').read_text().splitlines()
                      if re.search(r'error:|undefined reference|Error [0-9]|No rule to make', line, re.I)]
            print('\n'.join(errors), flush=True)
            print(json.dumps({'failure_package': failure.name,
                              'manifest_sha256': digest(failure / 'SHA256SUMS')}), flush=True)
            result.check_returncode()
        symbol_map = (output / 'System.map').read_text()
        for name in ('mtk_wdt_capture_begin', 'mtk_wdt_recovery_arm', 'mt6797_wfc_request_begin',
                     'mt6797_wfc_request_end', 'ramoops_capture_begin', 'ramoops_capture_append'):
            assert re.search(r' [Tt] ' + re.escape(name) + r'$', symbol_map, re.M), name
        assert 'recovery_discriminator_callback' not in symbol_map
        assert not run([cross + 'nm', '-u', str(output / 'vmlinux')], env=environment)
        assert run(integrity + ['verify', str(source)]) == source_integrity
        with tempfile.TemporaryDirectory(prefix='wifi-controller-package-', dir=package.parent) as tmp_package:
            staged = Path(tmp_package) / 'package';staged.mkdir()
            files = {'config': output / '.config', 'System.map': output / 'System.map',
                     'vmlinux': output / 'vmlinux', 'Image.gz-dtb': output / 'arch/arm64/boot/Image.gz-dtb',
                     'cust.dtsi': cust, 'configure.log': work / 'configure.log',
                     'dct.log': work / 'dct.log', 'build.log': work / 'build.log'}
            for name, path in files.items():
                assert path.is_file() and not path.is_symlink() and path.stat().st_size
                shutil.copyfile(path, staged / name)
            diagnostics = [line for line in (work / 'build.log').read_text().splitlines()
                           if re.search(r'\b(warning|error):', line, re.I)]
            (staged / 'diagnostics.txt').write_text('\n'.join(diagnostics) + '\n')
            result = {'project_commit': commit, 'inputs_sha256': identity, 'inputs': pins,
                      'source_integrity': source_integrity, 'compiler': compiler, 'linker': linker,
                      'config_sha256': digest(output / '.config'), 'configuration_delta': delta,
                      'build_environment': {key: environment[key] for key in
                          ('HOST_EXTRACFLAGS', 'KBUILD_BUILD_USER', 'KBUILD_BUILD_HOST',
                           'KBUILD_BUILD_VERSION', 'KBUILD_BUILD_TIMESTAMP')},
                      'target_cflags': '-fstack-usage', 'undefined_symbols': 0,
                      'diagnostic_lines': len(diagnostics), 'boot_candidate': False,
                      'device_execution': False, 'scope': 'complete native kernel link only'}
            (staged / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            (staged / 'SHA256SUMS').write_text(''.join(digest(p) + '  ' + p.name + '\n' for p in sorted(staged.iterdir())))
            run(['sha256sum', '--check', '--strict', 'SHA256SUMS'], cwd=staged)
            staged.rename(package)
    print(json.dumps({'package': package.name, 'manifest_sha256': digest(package / 'SHA256SUMS')}))


if __name__ == '__main__':
    main()
