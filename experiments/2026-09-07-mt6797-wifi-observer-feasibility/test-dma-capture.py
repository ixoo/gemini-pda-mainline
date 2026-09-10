#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare actual native DMA functions before/after hooks using injected I/O."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


native = module('native_lifetime', 'test-dma-native-lifetime.py')
writer = module('slot_writer', 'test-capture-writer.py')
r = writer.r

EXTRA = r'''
typedef uint64_t u64;
typedef struct { int counter; } atomic_t;
#define ATOMIC_INIT(n) { n }
#define atomic_read(p) __atomic_load_n(&(p)->counter, __ATOMIC_SEQ_CST)
#define atomic_inc_return(p) __atomic_add_fetch(&(p)->counter, 1, __ATOMIC_SEQ_CST)
#define atomic_xchg(p, n) __atomic_exchange_n(&(p)->counter, n, __ATOMIC_SEQ_CST)
#define READ_ONCE(n) __atomic_load_n(&(n), __ATOMIC_SEQ_CST)
#define CONFIG_PSTORE_RAM 1
#define MT6797 1
#define CONFIG_OF 1
#define BIT(n) (1U << (n))
#define BITS(a,b) ((~0U >> (31 - (b))) & (~0U << (a)))
#define PDMA_DBG(...) ((void)0)
static void put_unaligned_le64(u64 n, u8 *p)
{ for (unsigned int i = 0; i < 8; i++) p[i] = n >> (8 * i); }
static struct wfc_writer state;
static bool ramoops_capture_active(void) { return state.attempted && !state.stopped; }
static int ramoops_capture_append(u32 kind, u32 tx, const u8 *p, size_t n)
{ return wfc_slot_write(&state, kind, tx, p, n); }
'''

MMIO = r'''
static UINT_32 pdma[32], io_log[400100];
static unsigned int io_count;
static int poll_kind;
static void record_io(unsigned int space, unsigned int offset, UINT_32 value) {
    assert(io_count + 3 <= sizeof(io_log) / sizeof(io_log[0]));
    io_log[io_count++] = space; io_log[io_count++] = offset; io_log[io_count++] = value;
}
static void writel(UINT_32 value, volatile UINT_32 *p) {
    assert(HifLock);
    uintptr_t offset = (uintptr_t)p - (uintptr_t)pdma;
    if (offset < sizeof(pdma)) {
        assert(!(offset % 4)); pdma[offset / 4] = value;
        record_io(3, offset, value); return;
    }
    offset = (uintptr_t)p - (uintptr_t)registers;
    assert(offset == 0 || offset == 0x200 || offset == 0x1000);
    if (offset == 0x200) { assert(value <= 1); irq_masked = value; }
    record_io(1, offset, value);
}
static UINT_32 readl(volatile UINT_32 *p) {
    assert(HifLock);
    uintptr_t offset = (uintptr_t)p - (uintptr_t)pdma;
    if (offset < sizeof(pdma)) {
        assert(!(offset % 4));
        UINT_32 value = pdma[offset / 4];
        if (poll_kind == 1) { assert(offset == 0); value = ++intr_reads >= intr_ready_at; }
        if (poll_kind == 2) { assert(offset == 8); value = ++idle_reads < idle_ready_at; }
        record_io(2, offset, value); return value;
    }
    offset = (uintptr_t)p - (uintptr_t)registers;
    assert(offset < sizeof(registers)); record_io(0, offset, 0); return 0;
}
'''

CALLBACKS = r'''
static void clock_control(int on) { assert(!HifLock); clocks += on ? 1 : -1; }
static void configure(void *hif, void *data) {
    assert(hif && HifLock && irq_masked && mapped); configs++;
    HifPdmaConfig(hif, data);
}
static void start(void *hif) { starts++; HifPdmaStart(hif); }
static int poll_intr(void *hif) { poll_kind = 1; int v = HifPdmaPollIntr(hif); poll_kind = 0; return v; }
static int poll_idle(void *hif) { poll_kind = 2; int v = HifPdmaPollStart(hif); poll_kind = 0; return v; }
static void ack(void *hif) { acks++; HifPdmaAckIntr(hif); }
static void stop(void *hif) { stops++; HifPdmaStop(hif); }
static void dump(void *hif) { assert(hif && HifLock); dumps++; }
static struct operations ops = { clock_control, configure, start, poll_intr, ack, stop, poll_idle, dump };
'''

WRAPPER = r'''
static GLUE_INFO_T glue;
void run_case(int tx, int mode, int capture, unsigned int lose) {
    HifLock = mapped = irq_masked = clocks = WlanDmaFatalErr = fgIsResetting = 0;
    maps = unmaps = configs = starts = acks = stops = dumps = intr_reads = idle_reads = 0;
    io_count = poll_kind = 0;
    ticks = 0; tick_step = mode == 3 ? 600 : 1;
    intr_ready_at = (mode == 1 || mode == 3) ? UINT32_MAX : 2;
    idle_ready_at = mode == 2 ? UINT32_MAX : 2;
    memset(pdma, 0, sizeof(pdma));
    pdma[6] = 0x65432; pdma[21] = 0x12; pdma[22] = 0x34;
    memset(memory, 0, sizeof(memory)); memset(&state, 0, sizeof(state));
    reads = writes = barriers = trace_length = cut = drop = fault_read = 0;
    /* Each run models a new boot, never a runtime reset of the observer. */
    wfc_devices.counter = wfc_transactions.counter = 0;
    if (capture) {
        u8 cycle[16], identity[80];
        for (unsigned int i = 0; i < 16; i++) cycle[i] = i;
        for (unsigned int i = 0; i < 80; i++) identity[i] = i;
        assert(!wfc_writer_begin(&state, memory, sizeof(memory), cycle, identity));
    }
    memset(&glue, 0, sizeof(glue));
    glue.rHifInfo.Dev = &ops; glue.rHifInfo.fgDmaEnable = TRUE;
    glue.rHifInfo.DmaOps = &ops; glue.rHifInfo.HifRegBaseAddr = registers;
    glue.rHifInfo.DmaRegBaseAddr = pdma;
    wfc_dma_bind(&glue.rHifInfo.capture, &ops, 1);
    drop = lose ? writes + lose : 0;
    UINT_8 buffer[512] = { 0 }; pfWlanDmaOps = &ops;
    int result = tx ? kalDevPortWrite(&glue, MCR_WTDR1, 31, buffer, sizeof(buffer)) :
                      kalDevPortRead(&glue, MCR_WRDR0, 31, buffer, sizeof(buffer));
    assert(result == TRUE && maps == 1 && configs == 1 && starts == 1);
    if (mode == 1 || mode == 3) {
        assert(WlanDmaFatalErr == 1 && dumps == 1);
        assert(intr_reads == (mode == 1 ? 499U : 0U));
        assert(HifLock && mapped && irq_masked && clocks == 1);
        assert(!acks && !stops && !idle_reads && !unmaps);
    } else {
        assert(!WlanDmaFatalErr && !dumps && intr_reads == 2);
        assert(!HifLock && !mapped && !irq_masked && !clocks);
        assert(acks == 1 && stops == 1 && unmaps == 1);
        assert(idle_reads == (mode == 2 ? 100001U : 2U));
    }
    wfc_dma_unbind(&glue.rHifInfo.capture);
    u8 status[4] = { 1, 0, 0, 0 };
    if (ramoops_capture_active()) ramoops_capture_append(255, 0, status, sizeof(status));
}

void helper_fault(int mode) {
    /* Reuse a completed case only to initialize simulated storage/new boot. */
    run_case(0, 0, 0, 0);
    u8 cycle[16], identity[80];
    for (unsigned int i = 0; i < 16; i++) cycle[i] = i;
    for (unsigned int i = 0; i < 80; i++) identity[i] = i;
    assert(!wfc_writer_begin(&state, memory, sizeof(memory), cycle, identity));
    struct wfc_dma_trace *t = &glue.rHifInfo.capture;
    wfc_dma_bind(t, &ops, 1);
    if (mode == 0) { wfc_dma_map(t, &glue, 0, 31, 32, mapped_address, 2, 1); return; }
    wfc_dma_map(t, &ops, 0, 31, 32, mapped_address, 2, 1);
    if (mode == 1) { wfc_dma_map(t, &ops, 0, 31, 32, mapped_address, 2, 1); return; }
    if (mode == 2) { wfc_dma_program(t, 1); return; }
    if (mode == 3) {
        for (unsigned int i = 0; i < 13; i++) wfc_dma_sample(t, 1, i, 0);
        wfc_dma_sample(t, 1, 0, 0); wfc_dma_program(t, 1); return;
    }
    if (mode == 4) { wfc_dma_unbind(t); return; }
    if (mode == 5) { wfc_dma_abort(); return; }
    wfc_dma_poll_begin(t, 1);
    if (mode == 6) {
        t->reads = UINT64_MAX; wfc_dma_poll_sample(t, 1, 1);
        wfc_dma_poll_end(t, 1, 1);
    } else if (mode == 7) {
        wfc_dma_poll_sample(t, 2, 1); wfc_dma_poll_end(t, 1, 1);
    } else if (mode == 8) {
        wfc_dma_poll_end(t, 1, 2);
    } else if (mode == 9) {
        atomic_xchg(&t->retired, 1); wfc_dma_poll_end(t, 1, 2);
    } else if (mode == 10) {
        t->reads = (1ULL << 32); wfc_dma_poll_sample(t, 1, 1);
        wfc_dma_poll_end(t, 1, 1);
    }
}
u8 *data(void) { return memory; }
UINT_32 *accesses(void) { return io_log; }
unsigned int access_count(void) { return io_count; }
unsigned int store_count(void) { return writes; }
'''


def without_includes(text):
    return '\n'.join(line for line in text.splitlines() if not line.startswith('#include ')) + '\n'


def build(root, original, patched, hooked):
    tree = patched if hooked else original
    hif = (tree / ('include/hif.h' if hooked else 'hif.h')).read_text()
    ahb = (tree / 'ahb.c').read_text()
    dma = (tree / 'ahb_pdma.c').read_text()
    source = writer.SHIM + without_includes((HERE / 'capture-slot-writer.h').read_text()) + EXTRA
    source += without_includes((patched / 'include/hif_capture.h').read_text())
    source += without_includes((patched / 'hif_capture.c').read_text())
    shim = native.SHIM
    start = shim.index('static void writel(')
    end = shim.index('static void wmb(', start)
    shim = shim[:start] + MMIO + shim[end:]
    shim = shim.replace('void *HifRegBaseAddr; }',
                        'void *HifRegBaseAddr; void *DmaRegBaseAddr; struct wfc_dma_trace capture; }')
    source += shim + native.native_definitions(hif, (original / 'sdio.h').read_text(), ahb)
    source += without_includes((original / 'hif_pdma.h').read_text())
    for name in ('HIF_DMAR_READL', 'HIF_DMAR_WRITEL'):
        source += re.search(r'^#define ' + name + r'[^\n]*\\\n[^\n]*', hif, re.M).group() + '\n'
    for name in ('Config', 'Start', 'Stop', 'PollIntr', 'PollStart', 'AckIntr'):
        source += native.fixture.function(dma, 'HifPdma' + name)
    source += CALLBACKS
    source += ''.join('BOOLEAN\n' + native.fixture.function(ahb, name)
                      for name in ('kalDevPortRead', 'kalDevPortWrite'))
    source += WRAPPER
    path = root / ('hooked' if hooked else 'original')
    path.with_suffix('.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                    str(path.with_suffix('.c')), '-o', str(path.with_suffix('.so'))], check=True)
    c = ctypes.CDLL(str(path.with_suffix('.so')))
    c.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    c.accesses.restype = ctypes.POINTER(ctypes.c_uint32)
    return c


def stream(c):
    result = r.decode_pmsg(bytes(c.data()[:r.ZONE_PAYLOAD_BYTES]), writer.CYCLE, writer.IDENTITY)
    return b''.join(r.encode(row['kind'], row['sequence'], writer.CYCLE,
                            row['transaction'], row['payload']) for row in result['records']), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path, help='pinned source basenames')
    parser.add_argument('patched', type=Path, help='patched HIF directory with include/')
    args = parser.parse_args()
    receipt = json.loads((HERE / 'results/dma-capture-sources.json').read_text())
    for section, directory in (('parents', args.original), ('outputs', args.patched)):
        for path, digest in receipt[section].items():
            relative = ('include/' if section == 'outputs' and '/include/' in path else '') + Path(path).name
            assert hashlib.sha256((directory / relative).read_bytes()).hexdigest() == digest, relative
    for entry in json.loads((HERE / 'results/dma-hook-sources.json').read_text())['sources']:
        assert hashlib.sha256((args.original / Path(entry['path']).name).read_bytes()).hexdigest() == entry['sha256']
    with tempfile.TemporaryDirectory(prefix='wifi-dma-hooks-') as td:
        root = Path(td)
        baseline, observed = [build(root, args.original, args.patched, enabled) for enabled in (False, True)]
        for tx in range(2):
            for mode in range(4):
                baseline.run_case(tx, mode, 0, 0)
                expected = list(baseline.accesses()[:baseline.access_count()])
                for capture, lose in ((0, 0), (1, 0), (1, 1)):
                    observed.run_case(tx, mode, capture, lose)
                    assert list(observed.accesses()[:observed.access_count()]) == expected
                    if not capture:
                        assert observed.store_count() == 0
                        continue
                    data, result = stream(observed)
                    if lose:
                        assert result['framing'] == 'incomplete'
                        continue
                    summaries = [r.DMA_POLL.unpack(row['payload']) for row in result['records']
                                 if row['kind'] == 5 and r.DMA_POLL.unpack(row['payload'])[1] == 2]
                    assert summaries[0][2] == (2 if mode in (1, 3) else 1)
                    assert summaries[0][4] == (499 if mode == 1 else 0 if mode == 3 else 2)
                    if mode in (0, 2):
                        assert summaries[1][2] == (3 if mode == 2 else 1)
                        assert summaries[1][4] == (100001 if mode == 2 else 2)
                        r.check_dma_bindings(data, writer.CYCLE)
                    if mode == 0:
                        r.check_dma(data, writer.CYCLE)
                    else:
                        try:
                            r.check_dma(data, writer.CYCLE)
                        except ValueError:
                            pass
                        else:
                            raise AssertionError('native failure accepted as complete DMA')
                    if mode in (1, 3):
                        assert result['producer_status'] == 2
        for mode in range(11):
            observed.helper_fault(mode)
            _, result = stream(observed)
            if mode in (6, 8, 10):
                summary = r.DMA_POLL.unpack(result['records'][-1]['payload'])
                assert summary[2] == (5 if mode == 6 else 2 if mode == 8 else 1)
                assert summary[4] == ((1 << 64) - 1 if mode == 6 else 0 if mode == 8 else (1 << 32) + 1)
            else:
                assert result['producer_status'] == 2
        observed.run_case(0, 0, 1, 0)
        _, valid = stream(observed)
        rows = valid['records']
        # Re-encode mutations with fresh CRC/sequence: these test semantics.
        mutations = [rows[:1] + rows[2:], rows[:-2] + rows[-1:],
                     rows[:2] + [rows[-2]] + rows[2:-2] + rows[-1:],
                     rows[:2] + [rows[1]] + rows[2:]]
        for index, payload in ((1, r.HIF_BIND.pack(1, 1, 2, 1)),
                               (1, r.HIF_BIND.pack(1, 1, 1, 0)),
                               (len(rows) - 2, r.HIF_UNBIND.pack(2, 1, 1)),
                               (2, r.DMA_MAP.pack(2, 0, 31, 32, 0x123456780, 2, 1))):
            mutated = [dict(row) for row in rows]
            mutated[index]['payload'] = payload
            mutations.append(mutated)
        for mutated in mutations:
            encoded = b''.join(r.encode(row['kind'], i, writer.CYCLE, row['transaction'], row['payload'])
                               for i, row in enumerate(mutated))
            try:
                r.check_dma_bindings(encoded, writer.CYCLE)
            except ValueError:
                pass
            else:
                raise AssertionError('invalid HIF binding accepted')
        print('helper_fault_cases=11; binding_mutations=8; result=pass')
        print('native_dma_hook_comparisons=24; actual_port_and_pdma_functions=true; result=pass; hardware_claim=none')


if __name__ == '__main__':
    main()
