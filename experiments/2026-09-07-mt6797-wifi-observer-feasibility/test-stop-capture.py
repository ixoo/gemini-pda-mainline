#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute original and captured adapter-stop bodies with injected native effects."""
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
spec = importlib.util.spec_from_file_location('dma_fixture', HERE / 'test-dma-capture.py')
dma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dma)
r = dma.r

SHIM = r'''
#include <assert.h>
typedef uint32_t UINT_32, WLAN_STATUS;
typedef int BOOLEAN;
#define IN
#define OUT
#define TRUE 1
#define FALSE 0
#define ASSERT assert
#define DBGLOG(...) ((void)0)
#define HIF_DBG(...) ((void)0)
#define CFG_SUPPORT_MULTITHREAD 1
#define CFG_FORCE_RESET_UNDER_BUS_ERROR 0
#define ACPI_STATE_D0 0
#define ACPI_STATE_D3 3
#define WLAN_STATUS_SUCCESS 0
#define WLAN_STATUS_NOT_INDICATING 7
#define CFG_IST_LOOP_COUNT 2
#define CFG_RESPONSE_CLEAR_RDY_TIMEOUT 2
#define CFG_RESPONSE_POLLING_TIMEOUT 4
#define MCR_WCIR 0
#define WCIR_WLAN_READY (1U << 21)
#define RST_WAIT_BIT_TIMEOUT 1
#define GLUE_FLAG_HAL_MCR_RD_BIT 0
#define MSEC_TO_JIFFIES(n) (n)
#define WAKE_LOCK_THREAD_WAKEUP_TIMEOUT 100
struct fake_task { char comm[16]; } task = { "remove" };
#define current (&task)
#define kalStrnCmp strncmp
static int mode, fgIsBusAccessFailed, reads_done;
static UINT_32 native_log[512];
static unsigned int native_count;
static void event(UINT_32 n) { assert(native_count < 512); native_log[native_count++] = n; }
typedef struct { struct wfc_dma_trace capture; void *HifRegBaseAddr; } GL_HIF_INFO_T;
typedef struct {
    GL_HIF_INFO_T rHifInfo;
    void *hif_thread;
    UINT_32 u4Register, *prRegValue;
    int rTimeoutWakeLock, waitq_hif, rHalRDMCRComp;
    unsigned long ulFlag;
} GLUE_INFO_T, *P_GLUE_INFO_T;
static GLUE_INFO_T glue;
typedef struct { GLUE_INFO_T *prGlueInfo; int rAcpiState, fgIsFwOwn; } ADAPTER_T, *P_ADAPTER_T;
static UINT_32 sdio_cr_readl(volatile UINT_32 *base, UINT_32 offset) {
    assert(base && offset == MCR_WCIR); event(100); reads_done++;
    return mode == 6 || mode == 7 || mode == 8 || (mode == 13 && reads_done < 5) ? WCIR_WLAN_READY : reads_done < 2 ? WCIR_WLAN_READY : 0;
}
#define HIF_REG_READL(_hif, _addr) sdio_cr_readl((volatile UINT_32 *)((_hif)->HifRegBaseAddr), (_addr));
#define EFFECT(name, n) static void name(void *p) { assert(p); event(n); }
EFFECT(kalClearCommandQueue, 1)
EFFECT(wlanClearTxCommandQueue, 2)
EFFECT(wlanClearTxCommandDoneQueue, 3)
EFFECT(wlanClearDataQueue, 4)
EFFECT(wlanClearRxToOsQueue, 5)
EFFECT(nicDisableInterrupt, 6)
EFFECT(nicRxUninitialize, 11)
EFFECT(nicUninitMGMT, 13)
EFFECT(nicUninitSystemService, 14)
EFFECT(nicReleaseAdapterMemory, 15)
static int wlanIsChipNoAck(void *p) { assert(p); event(20); return mode == 2; }
static int kalIsCardRemoved(void *p) { assert(p); event(21); return mode == 3; }
static WLAN_STATUS wlanSendNicPowerCtrlCmd(void *p, int value) { assert(p && value == 1); event(8); return mode == 5 ? 9 : 0; }
static WLAN_STATUS nicProcessIST(void *p) { assert(p); event(9); return WLAN_STATUS_NOT_INDICATING; }
static WLAN_STATUS wlanPowerOffInt(void *p) { assert(p); event(22); return mode == 6 ? 0 : 9; }
static void nicpmSetFWOwn(void *p, int value) { assert(p && !value); event(10); }
static void nicTxRelease(void *p, int value) { assert(p && !value); event(12); }
static void glGetRstReason(int reason) { assert(reason == 1); event(23); }
static void wlanPollingCpupcr(int a, int b) { assert(a == 4 && b == 5); event(24); }
static void glResetTrigger(void *p) { assert(p); event(25); }
static void kalMsleep(int n) { assert(n == 1); event(26); if (mode == 14) glue.hif_thread = &glue; }
#define ACQUIRE_POWER_CONTROL_FROM_PM(p) event(7)
#define RECLAIM_POWER_CONTROL_TO_PM(p,v) event(16)
#define KAL_WAKE_LOCK_TIMEOUT(...) event(30)
static void set_bit(int bit, unsigned long *p) { assert(!bit); *p |= 1; event(31); }
static void wake_up_interruptible(void *p) { assert(p); event(32); }
'''

WAIT = r'''
static int wait_for_completion_interruptible(void *p) {
    assert(p); event(33);
    if (mode == 9) return -4; /* No accessor supplies the initialized zero. */
    kalDevRegRead(&glue, glue.u4Register, glue.prRegValue);
    return 0;
}
'''

WRAPPER = r'''
void run_case(int selected_mode, int capture) {
    mode = selected_mode; fgIsBusAccessFailed = mode == 8;
    reads_done = native_count = 0;
    memset(memory, 0, sizeof(memory)); memset(&state, 0, sizeof(state));
    reads = writes = barriers = trace_length = cut = drop = fault_read = 0;
    memset(&glue, 0, sizeof(glue));
    wfc_devices.counter = wfc_transactions.counter = wfc_stops.counter = 0;
    if (capture) {
        u8 cycle[16], identity[80];
        for (unsigned int i = 0; i < 16; i++) cycle[i] = i;
        for (unsigned int i = 0; i < 80; i++) identity[i] = i;
        assert(!wfc_writer_begin(&state, memory, sizeof(memory), cycle, identity));
    }
    glue.rHifInfo.HifRegBaseAddr = &glue;
    glue.hif_thread = mode == 9 || mode == 10 || mode == 11 ? &glue : NULL;
    strcpy(task.comm, mode == 11 ? "hif_thread" : "remove");
    wfc_dma_bind(&glue.rHifInfo.capture, &glue, 1);
    if (capture == 2) drop = writes + 1;
    ADAPTER_T adapter = { &glue, mode == 1 ? ACPI_STATE_D3 : ACPI_STATE_D0, mode == 4 };
    int result = CALL_STOP;
    assert(result == WLAN_STATUS_SUCCESS);
    u8 status[4] = { 1, 0, 0, 0 };
    if (ramoops_capture_active()) ramoops_capture_append(255, 0, status, 4);
}
u8 *data(void) { return memory; }
UINT_32 *effects(void) { return native_log; }
unsigned int effect_count(void) { return native_count; }
unsigned int store_count(void) { return writes; }
'''


def build(root, original, patched, dma_sources, hooked):
    tree = patched if hooked else original
    source = dma.writer.SHIM + dma.without_includes((HERE / 'capture-slot-writer.h').read_text()) + dma.EXTRA
    for path in (dma_sources / 'include/hif_capture.h', dma_sources / 'hif_capture.c',
                 patched / 'include/hif_stop_capture.h', patched / 'hif_stop_capture.c'):
        source += dma.without_includes(path.read_text())
    source += SHIM
    ahb = (tree / 'ahb.c').read_text()
    if hooked:
        source += dma.native.fixture.function(ahb, 'kalDevRegReadCapture')
    source += dma.native.fixture.function(ahb, 'kalDevRegRead') + WAIT
    hal = (tree / 'hal.h').read_text()
    start = hal.index('#define HAL_MCR_RD', hal.index('#else /* #if defined(_HIF_SDIO) */'))
    source += hal[start:hal.index('#define HAL_MCR_WR', start)]
    source += dma.native.fixture.function((tree / 'wlan_lib.c').read_text(), 'wlanAdapterStop')
    source += WRAPPER.replace('CALL_STOP', 'wlanAdapterStop(&adapter, mode == 12 ? 2 : 1)' if hooked else 'wlanAdapterStop(&adapter)')
    path = root / ('hooked' if hooked else 'original')
    path.with_suffix('.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                    str(path.with_suffix('.c')), '-o', str(path.with_suffix('.so'))], check=True)
    c = ctypes.CDLL(str(path.with_suffix('.so')))
    c.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    c.effects.restype = ctypes.POINTER(ctypes.c_uint32)
    return c


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('patched', type=Path)
    parser.add_argument('dma_sources', type=Path)
    args = parser.parse_args()
    receipt = json.loads((HERE / 'results/stop-capture-sources.json').read_text())
    for section, directory in (('parents', args.original), ('outputs', args.patched)):
        for path, expected in receipt[section].items():
            relative = ('include/' if section == 'outputs' and path.endswith(('/hif.h', '/hif_stop_capture.h')) else '') + Path(path).name
            assert hashlib.sha256((directory / relative).read_bytes()).hexdigest() == expected, relative
    dma_pins = json.loads((HERE / 'results/dma-capture-sources.json').read_text())
    for path, expected in dma_pins['outputs'].items():
        if Path(path).name in ('hif_capture.h', 'hif_capture.c'):
            relative = ('include/' if path.endswith('.h') else '') + Path(path).name
            assert hashlib.sha256((args.dma_sources / relative).read_bytes()).hexdigest() == expected
    with tempfile.TemporaryDirectory(prefix='wifi-stop-capture-') as td:
        baseline, observed = [build(Path(td), args.original, args.patched, args.dma_sources, enabled)
                              for enabled in (False, True)]
        for mode in range(15):
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
                assert len(rows) == 4
                poll = r.FW_STOP_POLL.unpack(rows[2]['payload'])
                expected_reason = 4 if mode in (1, 2, 3, 4, 5) else 2 if mode == 6 else 3 if mode in (7, 8) else 1
                assert poll[2] == expected_reason, (mode, poll)
                if mode in (9, 10):
                    assert poll[1] == 2 and poll[4] == 0  # Queued completions are not attributed.
                elif mode == 14:
                    assert poll[1] == 3 and poll[3:6] == (2, 1, 1)
                elif expected_reason != 4:
                    assert poll[1] == 1 and poll[3] == poll[4] == poll[5]
                if mode == 13:
                    assert poll[6] == 2
                if mode == 0:
                    r.check_stop(data, dma.writer.CYCLE)
                else:
                    try:
                        r.check_stop(data, dma.writer.CYCLE)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(('ineligible native stop accepted', mode))
        print('native_stop_comparisons=45; actual_stop_dispatch_accessor=true; result=pass; hardware_claim=none')


if __name__ == '__main__':
    main()
