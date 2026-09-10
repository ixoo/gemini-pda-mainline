#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute pinned native port functions with fake DMA, MMIO, clock and locks."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('capture_fixture', HERE / 'test-capture-integration.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

SHIM = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t UINT_8, *PUINT_8;
typedef uint16_t UINT_16;
typedef uint32_t UINT_32, UINT32;
typedef unsigned long ULONG;
typedef int BOOLEAN, MTK_WCN_BOOL;
#define VOID void
#define IN
#define OUT
#define TRUE 1
#define FALSE 0
#define ASSERT assert
#define DBGLOG(...) ((void)0)
#define HIF_DBG(...) ((void)0)
#define HIF_DBG_TX(...) ((void)0)
#define ALIGN_4(n) (((n) + 3) & ~3U)
#define HZ 100
#define MTK_WCN_SINGLE_MODULE 1
/* These distinct port tokens select branches; no real bus is accessed. */
#define MCR_WHISR 1
#define MCR_WRDR0 2
#define MCR_WRDR1 3
#define MCR_WTDR1 4
#define DMA_TO_DEVICE 1
#define DMA_FROM_DEVICE 2
static unsigned long ticks, tick_step;
static unsigned long next_tick(void) { unsigned long v = ticks; ticks += tick_step; return v; }
#define jiffies next_tick()
#define time_before(a, b) ((long)((a) - (b)) < 0)
static int HifLock, mapped, irq_masked, clocks, WlanDmaFatalErr, fgIsResetting;
static unsigned int maps, unmaps, configs, starts, acks, stops, dumps, intr_reads, idle_reads;
static unsigned int intr_ready_at, idle_ready_at;
static size_t mapped_length;
static int mapped_direction;
static uint64_t mapped_address = 0x123456780ULL;
static UINT_8 registers[8192], *register_base = registers, **g_pHifRegBaseAddr = &register_base;
static void spin_lock_bh(int *p) { assert(!*p); *p = 1; }
static void spin_unlock_bh(int *p) { assert(*p); *p = 0; }
static void writel(UINT_32 value, volatile UINT_32 *p) {
    assert(HifLock);
    uintptr_t offset = (uintptr_t)p - (uintptr_t)registers;
    assert(offset == 0 || offset == 0x200 || offset == 0x1000);
    if (offset == 0x200) { assert(value <= 1); irq_masked = value; }
}
static UINT_32 readl(volatile UINT_32 *p) { (void)p; assert(HifLock); return 0; }
static void wmb(void) { assert(HifLock); }
static int HifIsFwOwn(void *p) { (void)p; return FALSE; }
struct sdio_func { unsigned int num, cur_blksize, use_dma; };
static struct sdio_func g_sdio_func = { 1, 512, 1 };
struct operations {
    void (*DmaClockCtrl)(int);
    void (*DmaConfig)(void *, void *);
    void (*DmaStart)(void *);
    int (*DmaPollIntr)(void *);
    void (*DmaAckIntr)(void *);
    void (*DmaStop)(void *);
    int (*DmaPollStart)(void *);
    void (*DmaRegDump)(void *);
};
typedef struct { void *Dev; int fgDmaEnable; struct operations *DmaOps; void *HifRegBaseAddr; } GL_HIF_INFO_T;
typedef struct { GL_HIF_INFO_T rHifInfo; void *prAdapter; } GLUE_INFO_T, *P_GLUE_INFO_T;
static struct operations *pfWlanDmaOps;
static ULONG dma_map_single(void *dev, void *buffer, size_t length, int direction) {
    assert(dev && buffer && HifLock && irq_masked && !mapped);
    mapped = 1; maps++; mapped_length = length; mapped_direction = direction;
    return mapped_address;
}
static void dma_unmap_single(void *dev, ULONG address, size_t length, int direction) {
    assert(dev && mapped && HifLock && irq_masked && address == mapped_address);
    assert(length == mapped_length && direction == mapped_direction);
    mapped = 0; unmaps++;
}
'''

CALLBACKS = r'''
static void clock_control(int on) { assert(!HifLock); clocks += on ? 1 : -1; }
static void configure(void *hif, void *data) {
    MTK_WCN_HIF_DMA_CONF *c = data;
    assert(hif && HifLock && irq_masked && mapped && c->Count == mapped_length);
    assert((c->Dir == HIF_DMA_DIR_RX ? c->Dst : c->Src) == mapped_address);
    configs++;
}
static void start(void *hif) { assert(hif && HifLock && mapped); starts++; }
static int poll_intr(void *hif) { assert(hif && HifLock); return ++intr_reads >= intr_ready_at; }
static int poll_idle(void *hif) { assert(hif && HifLock); return ++idle_reads < idle_ready_at; }
static void ack(void *hif) { assert(hif && HifLock); acks++; }
static void stop(void *hif) { assert(hif && HifLock); stops++; }
static void dump(void *hif) { assert(hif && HifLock); dumps++; }
static struct operations ops = { clock_control, configure, start, poll_intr, ack, stop, poll_idle, dump };
'''

TEST = r'''
int main(void) {
    for (int tx = 0; tx < 2; tx++) {
        for (int mode = 0; mode < 4; mode++) {
            HifLock = mapped = irq_masked = clocks = WlanDmaFatalErr = fgIsResetting = 0;
            maps = unmaps = configs = starts = acks = stops = dumps = intr_reads = idle_reads = 0;
            ticks = 0; tick_step = mode == 3 ? 600 : 1;
            intr_ready_at = (mode == 1 || mode == 3) ? UINT32_MAX : 2;
            idle_ready_at = mode == 2 ? UINT32_MAX : 2;
            GLUE_INFO_T glue = { { &ops, TRUE, &ops, registers }, NULL };
            UINT_8 buffer[512] = { 0 };
            pfWlanDmaOps = &ops;
            int result = tx ? kalDevPortWrite(&glue, MCR_WTDR1, 32, buffer, sizeof(buffer)) :
                              kalDevPortRead(&glue, MCR_WRDR0, 32, buffer, sizeof(buffer));
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
            printf("direction=%s case=%s returned_true=%d intr_calls=%u idle_calls=%u lock_held=%d mapping_live=%d hif_irq_mask_request=%d clock_balance=%d unmaps=%u\n",
                   tx ? "TX" : "RX", (const char *[]){ "condition", "deadline", "idle-count", "deadline-before-read" }[mode],
                   result, intr_reads, idle_reads, HifLock, mapped, irq_masked, clocks, unmaps);
        }
    }
    puts("native_port_lifetime_cases=8; result=pass; hardware_claim=none");
    return 0;
}
'''


def native_definitions(hif, sdio, ahb):
    # Use actual selected constants, native macros, wire bitfields and DMA config types.
    native = ''
    for name, value in (('CONF_MTK_AHB_DMA', 1), ('CONF_HIF_DMA_INT', 0),
                        ('CONF_HIF_CONNSYS_DBG', 1), ('CONF_HIF_DMA_DBG', 0)):
        line = re.search(r'^#define\s+' + name + r'\s+[^\n]+', hif, re.M).group()
        assert re.search(r'\s' + str(value) + r'\b', line)
        native += line + '\n'
    assert not re.search(r'^\s*#define\s+MTK_DMA_BUF_MEMCPY_SUP\b', ahb, re.M)
    native += re.search(r'^#define HIF_DRV_BASE[^\n]+', hif, re.M).group() + '\n'
    for name in ('AP_DMA_HIF_LOCK', 'AP_DMA_HIF_UNLOCK'):
        native += re.search(r'^#define ' + name + r'[^\n]+', hif, re.M).group() + '\n'
    for text, names in ((hif, ('my_sdio_disable', 'my_sdio_enable')),
                        (sdio, ('__disable_irq', '__enable_irq'))):
        for name in names:
            native += re.search(r'^#define ' + name + r'[^\n]*\\\n(?:[^\n]*\\\n)*[^\n]*', text, re.M).group() + '\n'
    native += '\n'.join(re.findall(r'^#define SDIO_GEN3_[^\n]+', sdio, re.M)) + '\n'
    native += sdio[sdio.index('enum SDIO_GEN3_RW_TYPE'):sdio.index('enum SDIO_GEN3_FUNCTION')]
    native += re.search(r'typedef union _sdio_gen3_cmd53_info\b.*?} sdio_gen3_cmd53_info;', sdio, re.S).group() + '\n'
    native += re.search(r'typedef enum _MTK_WCN_HIF_DMA_DIR\b.*?} MTK_WCN_HIF_DMA_DIR;', hif, re.S).group() + '\n'
    native += re.search(r'typedef struct _MTK_WCN_HIF_DMA_CONF\b.*?} MTK_WCN_HIF_DMA_CONF;', hif, re.S).group() + '\n'
    return native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='directory containing the five pinned source basenames')
    args = parser.parse_args()
    receipt = json.loads((HERE / 'results/dma-hook-sources.json').read_text())
    source = {}
    for entry in receipt['sources']:
        p = args.source / Path(entry['path']).name
        raw = p.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry['sha256'], p.name
        source[p.name] = raw.decode()
    hif, sdio, ahb = (source[n] for n in ('hif.h', 'sdio.h', 'ahb.c'))
    native = native_definitions(hif, sdio, ahb)
    functions = ''.join('BOOLEAN\n' + fixture.function(ahb, name) for name in ('kalDevPortRead', 'kalDevPortWrite'))
    with tempfile.TemporaryDirectory(prefix='wifi-native-lifetime-') as td:
        root = Path(td)
        (root / 'test.c').write_text(SHIM + native + CALLBACKS + functions + TEST)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        str(root / 'test.c'), '-o', str(root / 'test')], check=True)
        subprocess.run([str(root / 'test')], timeout=10, check=True)


if __name__ == '__main__':
    main()
