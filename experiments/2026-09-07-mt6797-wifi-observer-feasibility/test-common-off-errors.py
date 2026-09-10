#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check native shutdown error propagation without changing cleanup effects."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = 'drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c'
SHIM = r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
typedef int INT32;
typedef unsigned int UINT32;
typedef unsigned long ULONG;
enum { WMTDRV_TYPE_BT, WMTDRV_TYPE_FM, WMTDRV_TYPE_GPS, WMTDRV_TYPE_WIFI,
       WMTDRV_TYPE_WMT, WMTDRV_TYPE_ANT, WMTDRV_TYPE_STP, WMTDRV_TYPE_SDIO1,
       WMTDRV_TYPE_SDIO2, WMTDRV_TYPE_LPBK, WMTDRV_TYPE_COREDUMP, WMTDRV_TYPE_MAX };
enum { DRV_STS_POWER_OFF, DRV_STS_POWER_ON, DRV_STS_FUNC_ON, DRV_STS_MAX };
#define WMT_HIF_UART 0
#define WMT_HIF_BTIF 2
#define WMT_SDIO_SLOT_SDIO1 1
#define WMT_CTRL_HW_PWR_OFF 0
#define WMT_CTRL_SDIO_HW 10
#define MTK_WCN_BOOL_FALSE false
#define WMT_WARN_FUNC(...) ((void)0)
#define WMT_ERR_FUNC(...) ((void)0)
#define WMT_INFO_FUNC(...) ((void)0)
/* The native assertion reports these errors and returns to cleanup. */
#define osal_assert(x) ((void)(x))
typedef struct { ULONG au4OpData[1]; } OP, *P_WMT_OP;
static struct {
    int eDrvStatus[WMTDRV_TYPE_MAX];
    void *p_ic_ops;
    struct { int hifType; } wmtHifConf;
} gMtkWmtCtx;
static bool g_pwr_off_flag;
static struct func_ops { int (*func_off)(void *, void *); } *gpWmtFuncOps[WMTDRV_TYPE_MAX];
static int callback_result, stp_result, hardware_result;
static int effects[100], count;
static void effect(int kind) {
    assert(count+4 <= 100);
    effects[count++]=kind;
    effects[count++]=gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WIFI];
    effects[count++]=gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WMT];
    effects[count++]=gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_SDIO1];
}
static int off_callback(void *ops, void *cfg) {
    assert(!ops && !cfg); effect(1); return callback_result;
}
static void *wmt_conf_get_cfg(void) { effect(2); return NULL; }
static int wmt_core_stp_deinit(void) { effect(3); return stp_result; }
static int wmt_core_ctrl(int op, ULONG *one, ULONG *two) {
    assert(!*two);
    if (op==WMT_CTRL_SDIO_HW) { assert(*one==WMT_SDIO_SLOT_SDIO1); effect(4); return 0; }
    assert(op==WMT_CTRL_HW_PWR_OFF && !*one); effect(5); return hardware_result;
}
static void wmt_core_dump_func_state(const char *label) { (void)label; effect(6); }
'''
WRAPPER = r'''
int run_case(int mode, int callback, int stp, int hardware) {
    memset(&gMtkWmtCtx,0,sizeof(gMtkWmtCtx));
    memset(gpWmtFuncOps,0,sizeof(gpWmtFuncOps));
    callback_result=callback;stp_result=stp;hardware_result=hardware;count=0;
    static struct func_ops ops={.func_off=off_callback};
    gpWmtFuncOps[WMTDRV_TYPE_WIFI]=mode==2 ? NULL : &ops;
    gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WIFI]=DRV_STS_FUNC_ON;
    gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WMT]=DRV_STS_FUNC_ON;
    gMtkWmtCtx.wmtHifConf.hifType=mode==9 ? WMT_HIF_UART : WMT_HIF_BTIF;
    g_pwr_off_flag=mode!=5;
    OP op={.au4OpData={WMTDRV_TYPE_WIFI}};
    if(mode==1) gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_BT]=DRV_STS_FUNC_ON;
    if(mode==3) gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WIFI]=DRV_STS_POWER_OFF;
    if(mode==4) gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WMT]=DRV_STS_POWER_OFF;
    if(mode==6) gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WMT]=DRV_STS_POWER_ON;
    if(mode==7) op.au4OpData[0]=WMTDRV_TYPE_MAX;
    if(mode==8) gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WIFI]=DRV_STS_MAX;
    if(mode==9) gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_SDIO1]=DRV_STS_FUNC_ON;
    if(mode==10) {
        gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WIFI]=DRV_STS_POWER_OFF;
        gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_LPBK]=DRV_STS_FUNC_ON;
        op.au4OpData[0]=WMTDRV_TYPE_LPBK;
    }
    int result=opfunc_func_off(&op);
    effect(7);
    return result;
}
int *get_effects(void) { return effects; }
int effect_count(void) { return count; }
int *get_status(void) { return gMtkWmtCtx.eDrvStatus; }
'''


def function(source, name):
    start = source.index('static INT32 ' + name + '(P_WMT_OP pWmtOp)\n{')
    end = source.index('\n}', start) + 2
    return source[start:end] + '\n'


def build(source, root, name):
    path = root / name
    code = SHIM + function(source, 'opfunc_pwr_off') + function(source, 'opfunc_func_off') + WRAPPER
    path.with_suffix('.c').write_text(code)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                    '-shared', '-fPIC', str(path.with_suffix('.c')), '-o', str(path.with_suffix('.so'))], check=True)
    lib = ctypes.CDLL(str(path.with_suffix('.so')))
    lib.get_effects.restype = ctypes.POINTER(ctypes.c_int)
    lib.get_status.restype = ctypes.POINTER(ctypes.c_int)
    return lib


def expected(mode, callback, stp, hardware, fixed):
    if mode in (3, 7, 8):
        return {3: 0, 7: -1, 8: -2}[mode]
    callback = -3 if mode == 2 else 0 if mode == 10 else callback
    if mode == 1:
        return callback
    power = -1 if mode == 4 else -2 if mode == 5 else hardware
    if fixed and mode not in (4, 5, 6):
        power = stp or hardware
    return (callback or power) if fixed else power


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('changed', type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/common-off-errors-sources.json').read_text())
    sources = []
    for key, tree in (('parents', args.parent), ('outputs', args.changed)):
        path = tree / SOURCE
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pins[key][SOURCE]
        sources.append(path.read_text())
    cases = changed = masked = 0
    with tempfile.TemporaryDirectory(prefix='wifi-common-off-errors-') as tmp:
        parent, child = [build(source, Path(tmp), name) for source, name in zip(sources, ('parent', 'child'))]
        for mode in range(11):
            for callback in (0, -5, 7):
                for stp in (0, -6, 8):
                    for hardware in (0, -7, 9):
                        args = (mode, callback, stp, hardware)
                        before, after = parent.run_case(*args), child.run_case(*args)
                        assert before == expected(*args, False), args
                        assert after == expected(*args, True), args
                        assert list(parent.get_effects()[:parent.effect_count()]) == list(child.get_effects()[:child.effect_count()]), args
                        assert list(parent.get_status()[:11]) == list(child.get_status()[:11]), args
                        cases += 1
                        changed += before != after
                        masked += before == 0 and after != 0
    assert masked > 0 and changed > masked
    print(f'common-off-errors=pass cases={cases} changed_error_results={changed} false_successes_reproduced={masked}')
    print('native_cleanup_callback_control_order_and_final_state=preserved; hardware_execution=none')


if __name__ == '__main__':
    main()
