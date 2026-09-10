#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the native removal wait block and observer with injected completions."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('worker_dma', HERE / 'test-dma-capture.py')
dma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dma)
r = dma.r
BASE = Path('drivers/misc/mediatek/connectivity/wlan/gen3')
HIF = BASE / 'os/linux/hif/ahb_sdioLike'
CYCLE = bytes(range(16))

SHIM = r'''
#include <assert.h>
struct wfc_dma_trace { atomic_t retired; u32 device; };
static void wfc_dma_abort(void) {
    const u8 status[4] = {2};
    if (ramoops_capture_active()) ramoops_capture_append(255, 0, status, 4);
}
struct glue {
    struct { struct wfc_dma_trace capture; } rHifInfo;
    int waitq_hif, waitq_rx, waitq, rHifHaltComp, rRxHaltComp, rHaltComp;
    void *hif_thread, *rx_thread, *main_thread;
    unsigned long ulFlag;
};
static unsigned int mask, events[32], event_count;
static int halt_result;
static void event(unsigned int n) { assert(event_count < 32); events[event_count++] = n; }
#define KAL_WLAN_REMOVE_TIMEOUT_MSEC 3000
#define MSEC_TO_JIFFIES(n) (n)
#define WLAN_STATUS_NOT_ACCEPTED 9
#define FALSE 0
#define TRUE 1
#define GLUE_FLAG_HALT_BIT 2
#define DBGLOG(...) ((void)0)
static int kalHaltLock(int n) { assert(n == 3000); event(1); return halt_result; }
static void kalOidComplete(struct glue *p, int a, int b, int c) {
    assert(p && !a && !b && c == 9); event(2);
}
static void kalSetHalted(int n) { assert(n); event(3); }
static void set_bit(int bit, unsigned long *p) { assert(bit == 2); *p |= 1UL << bit; event(4); }
static void wake_up_interruptible(int *p) { event(10 + *p); }
static unsigned long wait_for_completion_timeout(int *p, int n) {
    assert(n == 3000); event(20 + *p);
    return mask & (1U << *p) ? 100UL + *p : 0;
}
static void show_stack(void *p, void *unused) { assert(!unused); event(30 + (uintptr_t)p); }
'''

WRAPPER = r'''
void run(unsigned int selected_mask, int halt, int capture, int binding) {
    struct glue glue = {0}, *prGlueInfo = &glue;
    mask = selected_mask; halt_result = halt; event_count = 0;
    memset(memory, 0, sizeof(memory)); memset(&state, 0, sizeof(state));
    reads = writes = barriers = trace_length = cut = drop = fault_read = 0;
    glue.waitq_hif = glue.rHifHaltComp = 0;
    glue.waitq_rx = glue.rRxHaltComp = 1;
    glue.waitq = glue.rHaltComp = 2;
    glue.hif_thread = (void *)1; glue.rx_thread = (void *)2; glue.main_thread = (void *)3;
    glue.rHifInfo.capture.device = binding == 1 ? 0 : 9;
    glue.rHifInfo.capture.retired.counter = binding == 2;
    if (capture) {
        u8 cycle[16], identity[80];
        for (unsigned int i = 0; i < 16; i++) cycle[i] = i;
        for (unsigned int i = 0; i < 80; i++) identity[i] = i;
        assert(!wfc_writer_begin(&state, memory, sizeof(memory), cycle, identity));
        if (capture == 2) drop = writes + 1;
    }
    DECLARATIONS
    BLOCK
    if (ramoops_capture_active()) {
        const u8 status[4] = {1};
        ramoops_capture_append(255, 0, status, 4);
    }
}
u8 *data(void) { return memory; }
unsigned int *effects(void) { return events; }
unsigned int count(void) { return event_count; }
unsigned int stores(void) { return writes; }
'''


def build(work, parent, child, hooked, multithread):
    tree = child if hooked else parent
    source = (tree / BASE / 'os/linux/gl_init.c').read_text()
    remove = dma.native.fixture.function(source, 'wlanRemove')
    begin = '\twfc_halt = kalHaltLock' if hooked else '\tif (-ETIME == kalHaltLock'
    start = remove.index(begin)
    end = remove.index('\tDBGLOG(INIT, TRACE, "mtk_sdiod stopped\\n");', start)
    block = remove[start:end]
    helper = dma.native.fixture.function((child / HIF / 'hif_stop_capture.c').read_text(), 'wfc_stop_workers')
    text = dma.writer.SHIM + dma.without_includes((HERE / 'capture-slot-writer.h').read_text())
    text += dma.EXTRA + SHIM + helper
    text += f'\n#define CFG_SUPPORT_MULTITHREAD {multithread}\n'
    declarations = 'unsigned long wfc_wait[3] = {0}; int wfc_halt;' if hooked else ''
    text += WRAPPER.replace('DECLARATIONS', declarations).replace('BLOCK', block)
    path = work / f'workers-{hooked}-{multithread}'
    path.with_suffix('.c').write_text(text)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                    str(path.with_suffix('.c')), '-o', str(path.with_suffix('.so'))], check=True)
    c = ctypes.CDLL(str(path.with_suffix('.so')))
    c.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    c.effects.restype = ctypes.POINTER(ctypes.c_uint)
    return c


def stream(rows):
    return b''.join(r.encode(row['kind'], i, CYCLE, row['transaction'], row['payload'])
                    for i, row in enumerate(rows))


def with_stop(rows):
    # Synthetic ordinary-stop suffix tests the independent record join only.
    suffix = [(1, r.FW_STOP_ENTRY.pack(1, 9, 1, 0, 1, 0, 0)),
              (1, r.FW_STOP_COMMAND.pack(2, 0, 1, 0)),
              (1, r.FW_STOP_POLL.pack(3, 1, 1, 1, 1, 1, 0, 0, 0, 0)),
              (1, r.FW_STOP_RETURN.pack(4, 0))]
    return rows[:-1] + [dict(kind=7, transaction=tx, payload=p) for tx, p in suffix] + rows[-1:]


def refuse(rows):
    try:
        r.check_stop_workers(stream(rows), CYCLE)
    except ValueError:
        return
    raise AssertionError('invalid worker-wait evidence accepted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('child', type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/stop-workers-sources.json').read_text())
    for section, tree in (('parents', args.parent), ('outputs', args.child)):
        for path, expected in pins[section].items():
            assert hashlib.sha256((tree / path).read_bytes()).hexdigest() == expected, path
    comparisons = 0
    with tempfile.TemporaryDirectory(prefix='wifi-stop-workers-') as directory:
        work = Path(directory)
        for multithread in (0, 1):
            old = build(work, args.parent, args.child, False, multithread)
            new = build(work, args.parent, args.child, True, multithread)
            for mask in range(8):
                for halt in (0, -62, -4):
                    old.run(mask, halt, 0, 0)
                    expected = list(old.effects()[:old.count()])
                    for capture in (0, 1, 2):
                        new.run(mask, halt, capture, 0)
                        assert list(new.effects()[:new.count()]) == expected
                        comparisons += 1
                        if not capture:
                            assert not new.stores()
                            continue
                        raw = bytes(new.data()[:r.ZONE_PAYLOAD_BYTES])
                        decoded = r.decode_pmsg(raw, CYCLE, bytes(range(80)))
                        if capture == 2:
                            assert decoded['framing'] == 'incomplete'
                            continue
                        rows = decoded['records']
                        values = r.FW_STOP_WORKERS.unpack(rows[1]['payload'])
                        expected_waits = tuple(100 + i if mask & (1 << i) and (multithread or i == 2) else 0 for i in range(3))
                        assert values == (15, 9, multithread, halt, *expected_waits)
                        joined = with_stop(rows)
                        if multithread and mask == 7 and halt == 0:
                            assert r.check_stop_workers(stream(joined), CYCLE)['checked_device'] == 9
                            good = joined
                        else:
                            refuse(joined)
            for binding in (1, 2):
                new.run(7, 0, 1, binding)
                rows = r.decode_pmsg(bytes(new.data()[:r.ZONE_PAYLOAD_BYTES]), CYCLE, bytes(range(80)))['records']
                assert [row['kind'] for row in rows] == [1, 255]
                assert rows[-1]['payload'] == b'\x02\0\0\0'
        refuse(good[:1] + good[2:])
        refuse(good[:2] + good[1:])
        moved = good[:1] + good[2:-1] + good[1:2] + good[-1:]
        refuse(moved)
        for field, value in ((1, 8), (2, 0), (3, -62), (4, 0), (5, 0), (6, 0)):
            values = list(r.FW_STOP_WORKERS.unpack(good[1]['payload']))
            values[field] = value
            changed = [dict(row) for row in good]
            changed[1]['payload'] = r.FW_STOP_WORKERS.pack(*values)
            refuse(changed)
    print(f'native_wait_comparisons={comparisons} worker_wait_join=pass')
    print('scope=injected wait block and producer; no complete removal, scheduler, task exit or hardware')


if __name__ == '__main__':
    main()
