#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ROOT-only CCMP session; existing private return/service/baseline remapping.

Use real CCMP receipt/release and retained C32 private64-member guards. All scan,
seal, owned-child quiescence, regression and single-recovery gates are inherited.

Environment: GEMINI_PRIVATE_REPO, GEMINI_RUNTIME_ROOT, GEMINI_JOIN_SCRIPT and the
host-owned Wi-Fi helper's GEMINI_WIFI_SSH_KEYS + fresh verified GEMINI_WIFI_SSH_BOOT.
"""
import importlib.util
import os
from pathlib import Path
import runpy
import types

HERE = Path(__file__).resolve().parent
PHASE_B = HERE.parent / '2026-10-07-mt6797-wifi-phase-b-join'
REPO = PHASE_B.parents[1]
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
SPEC = importlib.util.spec_from_file_location('wifi_ccmp_host', HERE / 'passive-host-ccmp.py')
NH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NH)
DOMAIN = NH.PH.HOST.DOMAIN
NATIVE_RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
NATIVE_CANDIDATE = 'ccmp-stable-monitor-candidate'


def rebind_native_session(result):
    """Bind the namespace prepare()/check_ram_root() actually consume, not only
    a nested module. Preserve inherited C32 supplicant/CLI/private64 guards."""
    import json as _json
    g = result['prepare'].__globals__  # the real passive-session namespace (prepare + check_ram_root)
    g['HERE'] = HERE
    g['RELEASE'] = NATIVE_RELEASE
    g['_CANDIDATE'] = NATIVE_CANDIDATE
    g['_RECEIPT'] = _json.loads((HERE / 'results' / (NATIVE_CANDIDATE + '.json')).read_bytes())
    parent = _json.loads((PHASE_B / 'results' / 'candidate-32.json').read_bytes())
    g['SUPPLICANT_REQUIRED'] = parent.get('supplicant') is not None
    g['CLI_REQUIRED'] = parent.get('wpa_cli') is not None
    # Mirror passive-session's own nested identity bindings (SESSION.HERE/RELEASE and the
    # deeper SESSION.SESSION.RELEASE) with the native release, for the lower module globals.
    nested = result.get('SESSION')
    if nested is not None:
        nested.HERE = HERE
        nested.RELEASE = NATIVE_RELEASE
        if getattr(nested, 'SESSION', None) is not None:
            nested.SESSION.RELEASE = NATIVE_RELEASE


def remap(path):
    path = Path(path)
    if not path.is_relative_to(REPO):
        raise ValueError('path outside this checkout: ' + str(path))
    return PRIVATE_REPO / path.relative_to(REPO)


DOMAIN.RETURN_V2 = remap(DOMAIN.RETURN_V2)
DOMAIN.HOST.SERVICE = remap(DOMAIN.HOST.SERVICE)
DOMAIN.HOST.BASELINE = remap(DOMAIN.HOST.BASELINE)
ORIGINAL_RUN_PATH = runpy.run_path


def rebind(module, seen):
    if id(module) in seen:
        return
    seen.add(id(module))
    for name in ('BASELINE', 'SERVICE'):
        value = getattr(module, name, None)
        if isinstance(value, Path) and value.is_relative_to(REPO):
            setattr(module, name, remap(value))
    for value in vars(module).values():
        if isinstance(value, types.ModuleType) and \
                str(getattr(value, '__file__', '')).startswith(str(REPO)):
            rebind(value, seen)


def reviewed_run_path(path, *args, **kwargs):
    # The SCAN/C2 prepare chain (consys-rails-passive passive-host.py) loads the
    # installer by a fixed basename from the phase-b dir; during a NATIVE session
    # the reviewed installer is install-native.py (the ND1 receipt, the native
    # experiment/release and the native program name) -- every validate/receipt and
    # boot2/readback guard of install-native.py is kept; only the correct native
    # installer is selected in place of the phase-b C33 one. Not a shim or bypass.
    if Path(path).resolve() == PHASE_B / 'install-passive.py':
        return ORIGINAL_RUN_PATH(str(HERE / 'install-ccmp.py'), *args, **kwargs)
    result = ORIGINAL_RUN_PATH(path, *args, **kwargs)
    if Path(path).resolve() == PHASE_B / 'passive-session.py':
        rebind_native_session(result)
        rebind(result['SESSION'], set())
    return result


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    raise SystemExit(NH.main())
