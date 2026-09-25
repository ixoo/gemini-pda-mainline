#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the selected native WLAN probe/remove bodies with injected results."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('capture_fixture', HERE / 'test-capture-integration.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

STUBS = r'''
#include <stdbool.h>
#ifndef EUCLEAN
#define EUCLEAN 117
#endif
#define MT6797 1
#define CONFIG_OF 1
#define CONF_HIF_DEV_MISC 0
#define VOID void
#define PVOID void *
#define WLAN_STATUS_SUCCESS 0
#define DBGLOG(...) ((void)0)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, v) ((x) = (v))
struct platform_device { struct { int unused; } dev; };
static struct platform_device platform;
static struct platform_device *HifAhbPDev = &platform;
static bool hif_probe_retained;
static int probe_result, remove_result, power_on, power_off, probes, removes;
static int native_probe(void *device) { (void)device; probes++; return probe_result; }
static int native_remove(void) { removes++; return remove_result; }
static int (*pfWlanProbe)(void *) = native_probe;
static int (*pfWlanRemove)(void) = native_remove;
static int mtk_wcn_consys_hw_wifi_paldo_ctrl(int enable)
{
    if (enable) power_on++; else power_off++;
    return 0;
}
static int HifAhbRemove(VOID);
'''

WRAPPER = r'''
int run(int probe, int remove, int call_remove)
{
    hif_probe_retained = false;
    power_on = power_off = probes = removes = 0;
    probe_result = probe;
    remove_result = remove;
    int result = HifAhbProbe();
    if (call_remove && result == 0)
        result = HifAhbRemove();
    return result;
}
int retry(void) { return HifAhbProbe(); }
int get_on(void) { return power_on; }
int get_off(void) { return power_off; }
int get_probes(void) { return probes; }
int get_removes(void) { return removes; }
int get_retained(void) { return hif_probe_retained; }
'''


def build(path, mode, work, label):
    source = path.read_text()
    code = STUBS + fixture.function(source, 'HifAhbProbe')
    code += fixture.function(source, 'HifAhbRemove') + WRAPPER
    output = work / (label + '-' + mode)
    output.with_suffix('.c').write_text(code)
    command = ['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
               '-shared', '-fPIC']
    if mode == 'capture':
        command += ['-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR=1']
    command += [str(output.with_suffix('.c')), '-o', str(output.with_suffix('.so'))]
    subprocess.run(command, check=True, capture_output=True, text=True)
    library = ctypes.CDLL(str(output.with_suffix('.so')))
    for name in ('run', 'retry', 'get_on', 'get_off', 'get_probes', 'get_removes', 'get_retained'):
        getattr(library, name).restype = ctypes.c_int
    return library


def state(library):
    return tuple(getattr(library, 'get_' + key)() for key in
                 ('on', 'off', 'probes', 'removes', 'retained'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('child', type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/paldo-failure-balance-sources.json').read_text())
    for name, path in (('parent_sha256', args.parent), ('output_sha256', args.child)):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pins[name], name
    cases = 0
    with tempfile.TemporaryDirectory(prefix='wifi-paldo-fixture-') as directory:
        work = Path(directory)
        old = build(args.parent, 'capture', work, 'parent')
        new = build(args.child, 'capture', work, 'child')
        ordinary = build(args.child, 'ordinary', work, 'child')
        assert old.run(-5, 0, 0) == new.run(-5, 0, 0) == -1
        assert state(old) == (1, 0, 1, 1, 0)
        assert state(new) == (1, 1, 1, 1, 0)
        cases += 1
        assert old.run(-5, -7, 0) == -1
        assert state(old) == (1, 0, 1, 1, 0)
        assert new.run(-5, -7, 0) == -117
        assert state(new) == (1, 0, 1, 1, 1)
        assert new.retry() == -117 and state(new) == (1, 0, 1, 1, 1)
        cases += 1
        for library in (old, new):
            assert library.run(-117, 0, 0) == -117
            assert state(library) == (1, 0, 1, 0, 1)
        cases += 1
        for library in (old, new):
            assert library.run(0, 0, 1) == 0
            assert state(library) == (1, 1, 1, 1, 0)
        cases += 1
        assert ordinary.run(-5, 0, 0) == -1
        assert state(ordinary) == (1, 0, 1, 1, 0)
        cases += 1
    print(f'paldo-failure-balance=pass cases={cases}')
    print('scope=native probe/remove bodies with injected callbacks; no PMIC or device operation')


if __name__ == '__main__':
    main()
