#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise complete native size/read/mapping functions with injected file I/O."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('read_fixture', HERE / 'test-firmware-read-capture.py')
fw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw)
dma = fw.dma


def build(root, path, dma_sources, label):
    text = path.read_text()
    source = dma.writer.SHIM + dma.without_includes((HERE / 'capture-slot-writer.h').read_text()) + dma.EXTRA
    for relative in ('include/hif_capture.h', 'hif_capture.c'):
        source += dma.without_includes((dma_sources / relative).read_text())
    shim = fw.SHIM.replace(
        'struct fake_file { struct fake_ops *f_op; int64_t f_pos; } file, *filp;',
        '''typedef int64_t loff_t;
struct fake_inode { loff_t i_size; } inode;
struct fake_dentry { struct fake_inode *d_inode; } entry;
struct fake_file { struct fake_ops *f_op; int64_t f_pos;
    struct { struct fake_dentry *dentry; } f_path; } file, *filp;''')
    start = shim.index('static WLAN_STATUS kalFirmwareSize(')
    end = shim.index('static void *vmalloc(', start)
    shim = shim[:start] + shim[end:]
    shim = shim.replace('mode == 3 ? NULL : buffer', '(mode == 3 || mode == 19) ? NULL : buffer')
    source += shim
    start = text.index('/* The selected MT6797 observer')
    source += text[start:text.index('static WLAN_STATUS\nkalFirmwareLoadCapture', start)]
    source += 'static WLAN_STATUS\n' + dma.native.fixture.function(text, 'kalFirmwareLoadCapture')
    for name in ('kalFirmwareLoad', 'kalFirmwareSize', 'kalFirmwareImageMapping'):
        source += dma.native.fixture.function(text, name)
    wrapper = fw.WRAPPER.replace('RESET_FW_COUNTER', 'wfc_fw_reads.counter = 0;')
    wrapper = wrapper.replace('file.f_pos = 99;', '''file.f_pos = 99;
    entry.d_inode = &inode; file.f_path.dentry = &entry;
    inode.i_size = mode == 2 ? 0 : mode == 9 ? UINT32_MAX : mode == 15 ? 100 :
        mode == 16 ? -1 : mode == 17 ? (1LL << 32) + 101 :
        mode == 18 ? UINT32_MAX - 2LL : mode == 19 ? UINT32_MAX - 3LL : 101;''')
    source += wrapper
    source += '''
int size_case(int64_t size, uint32_t *out) {
    entry.d_inode = &inode; file.f_path.dentry = &entry; filp = &file;
    inode.i_size = size; log_count = 0;
    return kalFirmwareSize(&glue, out);
}
int invalid_read_case(int which) {
    UINT_32 size = which == 3 ? 0 : 101;
    log_count = 0; file.f_pos = 99;
    return kalFirmwareLoad(which == 0 ? NULL : &glue,
                           which == 1 ? NULL : buffer, 0,
                           which == 2 ? NULL : &size);
}
'''
    target = root / label
    target.with_suffix('.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                    str(target.with_suffix('.c')), '-o', str(target.with_suffix('.so'))], check=True)
    library = ctypes.CDLL(str(target.with_suffix('.so')))
    library.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    library.effects.restype = ctypes.POINTER(ctypes.c_uint64)
    library.size_case.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_uint32)]
    return library


def effects(library):
    return list(library.effects()[:library.effect_count()])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('safe', type=Path)
    parser.add_argument('dma_sources', type=Path)
    args = parser.parse_args()
    receipt = json.loads((HERE / 'results/firmware-read-safety-sources.json').read_text())
    for path, expected in ((args.parent, receipt['parent']['sha256']),
                           (args.safe, receipt['output_sha256'])):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    pins = json.loads((HERE / 'results/dma-capture-sources.json').read_text())['outputs']
    for path, expected in pins.items():
        if Path(path).name in ('hif_capture.h', 'hif_capture.c'):
            relative = ('include/' if path.endswith('.h') else '') + Path(path).name
            assert hashlib.sha256((args.dma_sources / relative).read_bytes()).hexdigest() == expected
    with tempfile.TemporaryDirectory(prefix='wifi-fw-read-safety-') as tmp:
        parent = build(Path(tmp), args.parent, args.dma_sources, 'parent')
        safe = build(Path(tmp), args.safe, args.dma_sources, 'safe')
        # Reproduce publication after negative/short/zero/oversized reads in the parent.
        for mode in (4, 5, 6, 7, 8):
            parent.run_case(mode, 0)
            assert effects(parent)[-8:-6] == [30, 1], mode
        for mode in range(20):
            for enabled in (0, 1, 2):
                safe.run_case(mode, enabled)
                observed = effects(safe)
                if mode in (0, 14, 15):
                    parent.run_case(mode, enabled)
                    assert observed == effects(parent), (mode, enabled)
                else:
                    # Failed mapping never publishes the buffer or the unsigned length.
                    assert observed[-8:-1] == [30, 0, 1, 0, 0, 1, 0x7777], (mode, enabled)
                    assert observed.count(5) == (0 if mode == 1 else 1), (mode, enabled)
                    if mode in (1, 2, 3, 9, 10, 11, 12, 13, 16, 17, 18, 19):
                        assert 20 not in observed, (mode, enabled)  # No file-read call.
                    if mode in (1, 2, 9, 10, 11, 16, 17, 18):
                        assert 3 not in observed, (mode, enabled)  # No allocation call.
                    assert observed.count(4) == (1 if mode in (4, 5, 6, 7, 8, 12, 13) else 0)
                if not enabled:
                    assert safe.store_count() == 0
                elif enabled == 1 and mode in (4, 5, 6, 7, 8):
                    data, result = dma.stream(safe)
                    rows = [r for r in result['records'] if r['kind'] == 7]
                    assert fw.r.FW_READ_RETURN.unpack(rows[-1]['payload']) == (11, 1, 0, 0, 0)
                    actual = fw.r.FW_READ_RESULT.unpack(rows[-2]['payload'])[-1]
                    assert actual == {4: -5, 5: 100, 6: 0, 7: 102, 8: (1 << 32) + 101}[mode]
        for size in (-1, 0, 1, 101, 0xfffffffc, 0xfffffffd, 0xffffffff,
                     1 << 32, (1 << 32) + 101, (1 << 63) - 1):
            out = ctypes.c_uint32(0x7777)
            status = safe.size_case(size, ctypes.byref(out))
            valid = 0 < size <= 0xfffffffc
            assert status == (0 if valid else 1), size
            assert out.value == (size if valid else 0x7777), size
        for which in range(4):
            assert safe.invalid_read_case(which) == 1
            assert effects(safe) == []  # Refuse before native assertions or file I/O.
    print('firmware-read-safety=pass mapping_cases=60 size_boundaries=10 invalid_arguments=4')
    print('native_bad_publication_reproduced=5 valid_native_effect_sequences_preserved=9')
    print('no_real_file_io_or_device_execution')


if __name__ == '__main__':
    main()
