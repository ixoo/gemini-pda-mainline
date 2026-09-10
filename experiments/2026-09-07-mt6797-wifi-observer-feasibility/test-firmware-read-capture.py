#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare native firmware mapping/read bodies with injected file operations."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dma_fixture', HERE / 'test-dma-capture.py')
dma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dma)
r = dma.r

SHIM = r'''
#include <assert.h>
#include <sys/types.h>
typedef int64_t s64;
typedef uint32_t UINT_32, WLAN_STATUS, *PUINT_32;
typedef void *PVOID, **PPVOID;
typedef struct { struct { struct wfc_dma_trace capture; } rHifInfo; } GLUE_INFO_T, *P_GLUE_INFO_T;
#define IN
#define OUT
#define FALSE 0
#define DEBUGFUNC(...) ((void)0)
#define WLAN_STATUS_SUCCESS 0
#define WLAN_STATUS_FAILURE 1
#define ALIGN_4(n) (((n) + 3U) & ~3U)
#define IS_ERR(p) ((uintptr_t)(p) == (uintptr_t)-1)
static int mode;
static GLUE_INFO_T glue;
static unsigned char buffer[256];
static uint64_t log_values[128];
static unsigned int log_count;
static void event(uint64_t value) { assert(log_count < 128); log_values[log_count++] = value; }
/* Native assertions are recorded without dereferencing a failed allocation. */
#define ASSERT(p) event((p) ? 10 : 11)
struct fake_file;
struct fake_ops { ssize_t (*read)(struct fake_file *, void *, size_t, int64_t *); } operations;
struct fake_file { struct fake_ops *f_op; int64_t f_pos; } file, *filp;
static ssize_t read_file(struct fake_file *p, void *out, size_t size, int64_t *pos) {
    assert(p == &file && pos == &file.f_pos);
    event(20); event(out == buffer); event(size); event(*pos);
    *pos += 7;
    if (mode == 14) glue.rHifInfo.capture.retired.counter = 1;
    if (mode == 3) return -ENOMEM;
    if (mode == 4 || mode == 9) return -EIO;
    if (mode == 5) return size - 1;
    if (mode == 6) return 0;
    if (mode == 7) return size + 1;
    if (mode == 8) return (1ULL << 32) + size;
    return size;
}
static WLAN_STATUS kalFirmwareOpen(P_GLUE_INFO_T p) {
    assert(p == &glue); event(1);
    return mode == 1 ? WLAN_STATUS_FAILURE : WLAN_STATUS_SUCCESS;
}
static WLAN_STATUS kalFirmwareSize(P_GLUE_INFO_T p, PUINT_32 size) {
    assert(p == &glue); event(2);
    *size = mode == 2 ? 0 : mode == 9 ? UINT32_MAX : mode == 15 ? 100 : 101;
    return WLAN_STATUS_SUCCESS;
}
static void *vmalloc(size_t size) { event(3); event(size); return mode == 3 ? NULL : buffer; }
static void vfree(void *p) { event(4); event(p == buffer); }
static void kalFirmwareClose(P_GLUE_INFO_T p) { assert(p == &glue); event(5); }
'''

WRAPPER = r'''
void run_case(int selected_mode, int capture) {
    mode = selected_mode; log_count = 0;
    memset(memory, 0, sizeof(memory)); memset(&state, 0, sizeof(state));
    reads = writes = barriers = trace_length = cut = drop = fault_read = 0;
    memset(&glue, 0, sizeof(glue));
    wfc_devices.counter = wfc_transactions.counter = 0;
    RESET_FW_COUNTER
    if (capture) {
        u8 cycle[16], identity[80];
        for (unsigned int i = 0; i < 16; i++) cycle[i] = i;
        for (unsigned int i = 0; i < 80; i++) identity[i] = i;
        assert(!wfc_writer_begin(&state, memory, sizeof(memory), cycle, identity));
    }
    wfc_dma_bind(&glue.rHifInfo.capture, &glue, 1);
    if (capture == 2) drop = writes + 1;
    operations.read = mode == 13 ? NULL : read_file;
    file.f_op = mode == 12 ? NULL : &operations;
    file.f_pos = 99;
    filp = mode == 10 ? NULL : mode == 11 ? (void *)-1 : &file;
    void *output = &glue;
    UINT_32 length = 0x7777;
    void *returned = kalFirmwareImageMapping(&glue, &output, &length);
    event(30); event(returned == buffer); event(returned == NULL);
    event(output == buffer); event(output == NULL); event(output == &glue);
    event(length); event(file.f_pos);
    u8 status[4] = {1, 0, 0, 0};
    if (ramoops_capture_active()) ramoops_capture_append(255, 0, status, 4);
}
u8 *data(void) { return memory; }
uint64_t *effects(void) { return log_values; }
unsigned int effect_count(void) { return log_count; }
unsigned int store_count(void) { return writes; }
'''


def build(root, tree, dma_sources, hooked):
    source = dma.writer.SHIM + dma.without_includes((HERE / 'capture-slot-writer.h').read_text()) + dma.EXTRA
    for path in (dma_sources / 'include/hif_capture.h', dma_sources / 'hif_capture.c'):
        source += dma.without_includes(path.read_text())
    source += SHIM
    text = tree.read_text()
    if hooked:
        start = text.index('/* The selected MT6797 observer')
        source += text[start:text.index('static WLAN_STATUS\nkalFirmwareLoadCapture', start)]
        source += 'static WLAN_STATUS\n' + dma.native.fixture.function(text, 'kalFirmwareLoadCapture')
    source += dma.native.fixture.function(text, 'kalFirmwareLoad')
    source += dma.native.fixture.function(text, 'kalFirmwareImageMapping')
    source += WRAPPER.replace('RESET_FW_COUNTER', 'wfc_fw_reads.counter = 0;' if hooked else '')
    path = root / ('hooked' if hooked else 'original')
    path.with_suffix('.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                    str(path.with_suffix('.c')), '-o', str(path.with_suffix('.so'))], check=True)
    c = ctypes.CDLL(str(path.with_suffix('.so')))
    c.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    c.effects.restype = ctypes.POINTER(ctypes.c_uint64)
    return c


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('patched', type=Path)
    parser.add_argument('dma_sources', type=Path)
    args = parser.parse_args()
    receipt = json.loads((HERE / 'results/firmware-read-capture-sources.json').read_text())
    for section, path in (('parents', args.original), ('outputs', args.patched)):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == next(iter(receipt[section].values()))
    pins = json.loads((HERE / 'results/dma-capture-sources.json').read_text())
    for path, expected in pins['outputs'].items():
        if Path(path).name in ('hif_capture.h', 'hif_capture.c'):
            relative = ('include/' if path.endswith('.h') else '') + Path(path).name
            assert hashlib.sha256((args.dma_sources / relative).read_bytes()).hexdigest() == expected
    with tempfile.TemporaryDirectory(prefix='wifi-fw-read-capture-') as td:
        baseline = build(Path(td), args.original, args.dma_sources, False)
        observed = build(Path(td), args.patched, args.dma_sources, True)
        for mode in range(16):
            baseline.run_case(mode, 0)
            expected = list(baseline.effects()[:baseline.effect_count()])
            for enabled in (0, 1, 2):
                observed.run_case(mode, enabled)
                assert list(observed.effects()[:observed.effect_count()]) == expected, (mode, enabled)
                if not enabled:
                    assert observed.store_count() == 0
                    continue
                data, result = dma.stream(observed)
                if enabled == 2:
                    assert result['framing'] == 'incomplete'
                    continue
                rows = [row for row in result['records'] if row['kind'] == 7]
                subtypes = [int.from_bytes(row['payload'][:4], 'little') for row in rows]
                assert subtypes == ([8, 11] if mode == 1 else [8, 9] if mode == 14 else [8, 9, 10, 11])
                if mode == 14:
                    assert result['producer_status'] == 2
                if mode in (0, 15):
                    assert r.check_firmware_read(data, dma.writer.CYCLE)['checked_reads'] == [1]
                else:
                    try:
                        r.check_firmware_read(data, dma.writer.CYCLE)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(('invalid firmware read accepted', mode))
                if mode == 4:
                    assert r.FW_READ_RESULT.unpack(rows[2]['payload'])[-1] == -5
                    assert r.FW_READ_RETURN.unpack(rows[3]['payload'])[3] == (1 << 32) - 5
                if mode == 8:
                    assert r.FW_READ_RESULT.unpack(rows[2]['payload'])[-1] == (1 << 32) + 101
                    assert r.FW_READ_RETURN.unpack(rows[3]['payload'])[3] == 101
        print('native_firmware_read_comparisons=48; actual_mapping_and_read_bodies=true; result=pass; hardware_claim=none')


if __name__ == '__main__':
    main()
