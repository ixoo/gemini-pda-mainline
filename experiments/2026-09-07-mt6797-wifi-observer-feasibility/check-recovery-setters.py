#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Buildbox-only full watchdog object comparison; no image or hardware action."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('native_compile', HERE / 'check-startup-objects.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
run, digest = native.run, native.digest
SOURCE = 'drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c'
HEADER = 'drivers/watchdog/mediatek/include/ext_wd_drv.h'
DETECT = 'drivers/misc/mediatek/connectivity/common/common_detect/'


def main():
    assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
    project = HERE.parents[1]
    commit = run(['git', '-C', str(project), 'rev-parse', 'HEAD'])
    reset = sys.argv[1:] == [commit, '--reset']
    controller = sys.argv[1:] == [commit, '--controller']
    gate = controller or sys.argv[1:] == [commit, '--gate']
    assert reset or gate or sys.argv[1:] == [commit]
    assert not run(['git', '-C', str(project), 'status', '--porcelain'])
    root = Path('/workspace/gemini-pda')
    source = root / 'gemian-source/gemian-baseline' / native.REVISION
    assert run(['git', '-C', str(source), 'rev-parse', 'HEAD']) == native.REVISION
    assert not run(['git', '-C', str(source), 'status', '--porcelain'])
    assert shutil.disk_usage(root).free > 2 * 1024 ** 3
    toolchain = root / 'gemian-toolchains' / native.TOOLCHAIN
    assert (toolchain / 'validated').read_text().strip() == native.TOOLCHAIN
    compiler = toolchain / 'wrappers/aarch64-linux-gnu-gcc'
    version = run([str(compiler), '--version']).splitlines()[0]
    assert version == 'aarch64-linux-gnu-gcc-6 (Debian 6.3.0-18) 6.3.0 20170516'
    config = project / 'experiments/2026-07-23-gemian-a72-owner-observer/inputs/active-gemian.config'
    assert digest(config) == '231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4'
    recorded = root / 'gemian-artifacts/gemian-observer-a98ffc90f979/outputs/build.log'
    assert digest(recorded) == 'cc43a28e3856325f3087dbc0c6b0a32e5cc0d8034074d851a0e0e33dd9da1a39'
    old_source = str(root / 'gemian-source/gemian-observer/a98ffc90f979eabe4e927b0d478199673b62781c')
    pins = json.loads((HERE / 'results/recovery-setters-sources.json').read_text())
    parent_patch = project / pins['parent_patch']
    patch = HERE / 'patches/recovery-setters' / pins['patch']
    assert digest(parent_patch) == pins['parent_patch_sha256']
    assert digest(patch) == pins['patch_sha256']
    topic = 'recovery-reset' if reset else 'controller-init' if controller else 'recovery-gate'
    gate_pins = json.loads((HERE / ('results/' + topic + '-sources.json')).read_text()) if gate or reset else None
    gate_patch = HERE / 'patches' / topic / gate_pins['patch'] if gate or reset else None
    if gate or reset:
        assert digest(gate_patch) == gate_pins['patch_sha256']
    label = ('wifi-recovery-reset-objects-' if reset else 'wifi-controller-init-objects-' if controller else
             'wifi-recovery-gate-objects-' if gate else 'wifi-recovery-setters-objects-')
    package = root / 'gemian-artifacts' / (label + commit)
    assert not package.exists()
    env = dict(os.environ, HOST_EXTRACFLAGS='-fcommon',
               LD_LIBRARY_PATH=str(toolchain / 'root/usr/lib/x86_64-linux-gnu'))
    with tempfile.TemporaryDirectory(prefix='wifi-recovery-setters-', dir=root / 'build') as directory:
        work = Path(directory)
        output, exported = work / 'output', work / 'package'
        output.mkdir()
        exported.mkdir()
        shutil.copyfile(config, output / '.config')
        command = ['make', '-C', str(source), 'O=' + str(output), 'ARCH=arm64',
                   'CROSS_COMPILE=' + str(toolchain / 'wrappers/aarch64-linux-gnu-'),
                   'python=' + str(toolchain / 'wrappers/python2.7'), 'KCFLAGS=-fstack-usage']
        with (exported / 'prepare.log').open('w') as stream:
            native.compile_logged(command + ['olddefconfig'], stream, env=env, timeout=120)
            before, after = native.symbols(config), native.symbols(output / '.config')
            delta = {key: [before.get(key), after.get(key)] for key in before.keys() | after.keys()
                     if before.get(key) != after.get(key)}
            assert delta == {'CONFIG_ANBOX': [None, 'n']}, delta
            native.compile_logged(command + ['-j2', 'V=1', 'prepare'], stream, env=env, timeout=300)
        parent, child = work / 'parent', work / 'child'
        prerequisites = [parent_patch]
        if reset:
            prerequisites.append(patch)
        inputs = set(pins['parents'])
        if gate:
            prerequisites += [patch] + sorted((HERE / 'patches/pstore').glob('*.patch'))
            assert len(prerequisites) == 12
            if controller:
                recovery_pins = json.loads((HERE / 'results/recovery-gate-sources.json').read_text())
                recovery_patch = HERE / 'patches/recovery-gate' / recovery_pins['patch']
                assert digest(recovery_patch) == recovery_pins['patch_sha256']
                prerequisites.append(recovery_patch)
            inputs.update(gate_pins['parents'])
            for item in prerequisites:
                inputs.update(re.findall(r'^--- a/(.+)$', item.read_text(), re.M))
            inputs.discard('fs/pstore/wifi_capture.h')  # Created by pstore patch 0007.
            inputs.update(str(path.relative_to(source)) for path in (source / 'fs/pstore').glob('*.h'))
            if controller:
                inputs.update(str(path.relative_to(source)) for path in (source / DETECT).glob('*.h'))
        for path in inputs:
            dest = parent / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / path, dest)
        for item in prerequisites:
            run(['git', 'apply', '--unsafe-paths', '--directory=' + str(parent), str(item)])
        shutil.copytree(parent, child)
        run(['git', 'apply', '--unsafe-paths', '--directory=' + str(child), str(gate_patch if gate or reset else patch)])
        for key, tree in [('parents', parent), ('outputs', child)]:
            for path, expected in (gate_pins if gate or reset else pins)[key].items():
                assert digest(tree / path) == expected
        support = work / 'support'
        support.mkdir()
        shutil.copyfile(source / Path(SOURCE).with_name('mt_wdt.h'), support / 'mt_wdt.h')
        shutil.copyfile(source / 'drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/wd_api.h',
                        support / 'wd_api.h')
        with (exported / 'fixture.log').open('w') as stream:
            fixture = ([sys.executable, str(HERE / 'test-recovery-reset.py'),
                        str(parent), str(child), str(support)] if reset else
                       [sys.executable, str(HERE / 'test-controller-init.py'), str(child)] if controller else
                       [sys.executable, str(HERE / 'test-recovery-gate.py'), str(child)] if gate else
                       [sys.executable, str(HERE / 'test-recovery-setters.py'),
                        str(parent), str(child), str(support)])
            native.compile_logged(fixture, stream, timeout=60)
        units = [SOURCE]
        if gate:
            units += ['drivers/watchdog/mediatek/wdk/wd_common_drv.c', 'fs/pstore/ram.c']
        if controller:
            units = [DETECT + path for path in ['wmt_detect.c', 'drv_init/conn_drv_init.c',
                     'drv_init/common_drv_init.c', 'drv_init/wlan_drv_init.c']] + ['fs/pstore/ram.c']
        records = []
        for unit in units:
            lines = [line for line in recorded.read_text().splitlines()
                       if ' -c ' in line and line.endswith('/' + unit)]
            assert len(lines) == 1, unit
            original = shlex.split(lines[0])
            assert original[0] == str(compiler) and original[-1] == old_source + '/' + unit
            for version_label, tree in [('parent', parent), ('child', child)]:
                label = version_label + ('-' + Path(unit).stem if gate else '')
                result, dep = exported / (label + '.o'), exported / (label + '.d')
                args = [a.replace(old_source, str(source)) for a in original]
                args[args.index('-o') + 1] = str(result)
                args[-1] = str(tree / unit)
                args[1:1] = ['-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR',
                             '-I' + str((tree / HEADER).parent), '-I' + str((source / SOURCE).parent)]
                if gate:
                    args[1:1] = ['-I' + str(tree / 'include'), '-I' + str(tree / 'fs/pstore')]
                if controller:
                    args[1:1] = ['-I' + str(tree / DETECT)]
                args = ['-Wp,-MD,' + str(dep) if a.startswith('-Wp,-MD,') else a for a in args]
                with (exported / (label + '.log')).open('w') as stream:
                    native.compile_logged(args, stream, cwd=output, env=env, timeout=120)
                deps = dep.read_text().replace('\\\n', ' ').split()
                if unit == SOURCE or unit.endswith('wd_common_drv.c') or (controller and
                        version_label == 'child' and unit.endswith('wmt_detect.c')):
                    assert str(tree / HEADER) in deps and str(source / HEADER) not in deps
                if unit == SOURCE:
                    assert str((source / SOURCE).with_name('mt_wdt.h')) in deps
                if unit == 'fs/pstore/ram.c' or (gate and version_label == 'child' and unit != SOURCE):
                    assert str(tree / 'include/linux/pstore_ram.h') in deps
                if unit == 'fs/pstore/ram.c':
                    assert str(tree / 'fs/pstore/wifi_capture.h') in deps
                if gate and version_label == 'child' and unit.endswith('wd_common_drv.c'):
                    assert str(tree / 'include/linux/cpuidle.h') in deps
                if controller and unit.startswith(DETECT):
                    assert str(tree / DETECT / 'wmt_detect.h') in deps
                    if version_label == 'child':
                        assert str(tree / DETECT / 'wmt_capture_init.h') in deps
                macros = list(args)
                macros.remove('-c')
                index = macros.index('-o')
                del macros[index:index + 2]
                macros = [a for a in macros if not a.startswith('-Wp,-MD,')]
                macros[1:1] = ['-dM', '-E']
                definitions = run(macros, cwd=output, env=env)
                assert '#define CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR 1' in definitions
                assert '#define CONFIG_KICK_SPM_WDT' not in definitions
                assert '#define __USING_DUMMY_WDT_DRV__' not in definitions
                if controller and unit.startswith(DETECT):
                    assert '#define MTK_WCN_REMOVE_KO 1' in definitions
                    assert '#define CONFIG_MTK_COMBO_WIFI 1' in definitions
                    if unit.endswith('wlan_drv_init.c'):
                        assert '#define MTK_WCN_WLAN_GEN3 1' in definitions
                emitted = run([str(toolchain / 'wrappers/aarch64-linux-gnu-nm'), str(result)], env=env)
                names = (['mtk_wdt_recovery_arm', 'mtk_wdt_set_time_out_value',
                          'mtk_wdt_mode_config', 'mtk_wdt_enable', 'mtk_wdt_restart'] if unit == SOURCE else
                         ['ramoops_capture_begin', 'ramoops_capture_append'] if unit == 'fs/pstore/ram.c' else
                         ['mtk_wdt_capture_begin'] if version_label == 'child' else [])
                if controller and unit.startswith(DETECT):
                    names = {'wmt_detect.c': ['wmt_detect_unlocked_ioctl'],
                             'conn_drv_init.c': ['do_connectivity_driver_init'],
                             'common_drv_init.c': ['do_common_drv_init'],
                             'wlan_drv_init.c': ['do_wlan_drv_init']}[Path(unit).name]
                for name in names:
                    assert any(line.endswith((' T ' + name, ' t ' + name)) for line in emitted.splitlines()), name
                if controller and unit.endswith('wmt_detect.c'):
                    assert (' U mtk_wdt_capture_begin' in emitted) == (version_label == 'child')
                if gate and version_label == 'parent' and unit.endswith('wd_common_drv.c'):
                    assert 'mtk_wdt_capture_begin' not in emitted
                records.append({'label': label, 'source': unit, 'source_sha256': digest(tree / unit),
                                'object_sha256': digest(result), 'header_sha256': digest(tree / HEADER)})
        receipt = {'commit': commit, 'source_revision': native.REVISION, 'compiler': version,
                   'toolchain_sha256': native.TOOLCHAIN, 'config_sha256': digest(output / '.config'),
                   'configuration_delta': delta,
                   'compile_only_define': 'CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR=1',
                   'selected_hardware_path': 'TOPRGU; SPM and dummy watchdog branches excluded',
                   'patch_sha256': digest(patch), 'parent_patch_sha256': digest(parent_patch),
                   'objects': records, 'fixture': '12 parent/child ordering comparisons passed',
                   'warning_policy': 'Recorded native -w retained; not warning-clean evidence',
                   'boot_candidate': False, 'device_access': False}
        if gate or reset:
            receipt['patch_sha256'] = digest(gate_patch)
            receipt['prerequisites'] = {str(item.relative_to(project)): digest(item) for item in prerequisites}
            receipt['fixture'] = '15 capture/arm boundary cases, one-shot and invalid argument refusal passed'
        if reset:
            receipt['fixture'] = 'parent/child direct-reset and no-lock reload takeover orderings, plus held-lock contention'
        if controller:
            receipt['fixture'] = ('native startup; 20 initializer failures; 26 lost records; '
                                  '4 preflight refusals; duplicate refusal; 52 decoder mutations passed')
        (exported / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
        shutil.copyfile(output / '.config', exported / 'config')
        files = sorted(exported.iterdir())
        assert all(path.is_file() and not path.is_symlink() for path in files)
        (exported / 'SHA256SUMS').write_text(''.join(digest(path) + '  ' + path.name + '\n' for path in files))
        run(['sha256sum', '--check', 'SHA256SUMS'], cwd=exported)
        shutil.copytree(exported, package)
    print(json.dumps({'package': package.name, 'manifest_sha256': digest(package / 'SHA256SUMS'),
                      'files': len(list(package.iterdir()))}))


if __name__ == '__main__':
    main()
