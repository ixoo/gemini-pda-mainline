#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run native removal, AHB and WMT OFF functions with injected worker waits."""
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

common = module('retain_common', 'test-common-off-errors.py')
extract = module('retain_extract', 'test-capture-integration.py').function
BASE = Path('drivers/misc/mediatek/connectivity')
WLAN = BASE / 'wlan/gen3'
CORE = BASE / 'common/common_main/core'

SHIM = r'''
#include <errno.h>
#include <stdint.h>
#define VOID void
#define INT_32 int
#define TRUE 1
#define FALSE 0
#define CFG_MAX_WLAN_DEVICES 1
#define CFG_SUPPORT_MULTITHREAD 1
#define CONFIG_OF 1
#define MSEC_TO_JIFFIES(n) (n)
#define WLAN_STATUS_NOT_ACCEPTED 9
#define GLUE_FLAG_HALT_BIT 2
#define DBGLOG(...) ((void)0)
/* Baseline ASSERT diagnoses nulls before its explicit return branches. */
#define ASSERT(x) ((void)(x))
#define kalMemSet memset
struct adapter { int rWlanInfo; };
typedef int WLAN_INFO_T;
typedef struct adapter *P_ADAPTER_T;
struct glue {
    struct { int capture; } rHifInfo;
    P_ADAPTER_T prAdapter;
    int waitq_hif, waitq_rx, waitq, rHifHaltComp, rRxHaltComp, rHaltComp;
    void *hif_thread, *rx_thread, *main_thread;
    unsigned int u4TxThreadPid, u4HifThreadPid;
    unsigned long ulFlag;
};
typedef struct glue *P_GLUE_INFO_T;
struct wireless { void *netdev; } wireless, *gprWdev = &wireless;
struct net_device { struct wireless *ieee80211_ptr; P_GLUE_INFO_T glue; } netdev;
struct dev_info { struct net_device *prDev; } arWlanDevInfo[1];
typedef struct dev_info *P_WLANDEV_INFO_T;
static struct adapter adapter;
static struct glue glue;
static unsigned int u4WlanDevNum, mask, wait_calls, frees, unlock_without_lock;
static int workq, sched_workq, halt_result, held, capture, aborts, summaries;
static void *netdev_priv(struct net_device *p) { return &p->glue; }
static void free_netdev(struct net_device *p) { assert(p); frees++; effect(40); }
static void kalPerMonDestroy(void *p) { assert(p); effect(41); }
static void flush_delayed_work(void *p) { assert(p); effect(42); }
static int kalHaltLock(int n) { assert(n == 3000); effect(43); held = !halt_result; return halt_result; }
static void kalHaltUnlock(void) { unlock_without_lock += !held; held = 0; effect(44); }
static void kalOidComplete(void *p, int a, int b, int c) { assert(p && !a && !b && c == 9); effect(45); }
static void kalSetHalted(int n) { assert(n); effect(46); }
static void set_bit(int n, unsigned long *p) { assert(n == 2); *p |= 1UL << n; effect(47); }
static void wake_up_interruptible(int *p) { effect(50 + *p); }
static unsigned long wait_for_completion_timeout(int *p, int n) {
    assert(n == 3000); wait_calls++; effect(60 + *p);
    return mask & (1U << *p) ? 100UL : 0;
}
static void show_stack(void *p, void *unused) { assert(p && !unused); effect(70); }
static void wfc_dma_abort(void) { aborts += !!capture; }
static void wfc_stop_workers(void *p, int mt, int halt, const unsigned long waits[3]) {
    assert(p && mt == 1 && halt == halt_result);
    for (unsigned int i = 0; i < 3; i++) assert(!!waits[i] == !!(mask & (1U << i)));
    summaries += !!capture;
}
static void wlanWakeLockUninit(void *p) { assert(p); effect(71); }
static void wlanAdapterStop(void *p, int caller) { assert(p && caller == 1); frees++; effect(72); }
static void glBusFreeIrq(void *dev, void *info) { assert(dev && info); effect(73); }
static void glBusRelease(void *p) { assert(p); effect(74); }
static void wlanNetUnregister(void *p) { assert(p); effect(75); }
static void wlanNetDestroy(void *p) { assert(p); frees++; effect(76); }
static void wlanUnregisterNotifier(void) { effect(77); }
static void mtk_wcn_consys_hw_wifi_paldo_ctrl(int on) { assert(!on); effect(78); }
typedef void *P_WMT_IC_OPS, *P_WMT_GEN_CONF;
#define WMT_CHIP_TYPE_COMBO 1
#define FUNC_OFF 0
#define WMT_WIFI_ON 0
#define WMT_BT_ON 1
#define WMT_GPS_ON 2
#define WMT_CTRL_BGW_DESENSE_CTRL 99
static unsigned long gBtWifiGpsState;
static int wmt_detect_get_chip_type(void) { return 0; }
static int wmt_func_wifi_ctrl(int n) { assert(!n); effect(79); return 0; }
static void osal_clear_bit(int bit, unsigned long *p) { *p &= ~(1UL << bit); effect(80); }
static int osal_test_bit(int bit, unsigned long *p) { return !!(*p & (1UL << bit)); }
static void mt6797_wfc_common_off_begin(unsigned int type, int status) { (void)type; (void)status; }
static void mt6797_wfc_common_off_end(int first, int last) { (void)first; (void)last; }
'''

WRAPPER = r'''
int run(int selected_mask, int halt, int selected_mode, int selected_capture) {
    memset(&gMtkWmtCtx, 0, sizeof(gMtkWmtCtx)); memset(gpWmtFuncOps, 0, sizeof(gpWmtFuncOps));
    memset(&glue, 0, sizeof(glue));
    count = wait_calls = frees = unlock_without_lock = held = aborts = summaries = 0;
    callback_result = selected_mode == 7 || selected_mode == 8 ? 9 : 0;
    stp_result = hardware_result = 0;
    mask = selected_mask; halt_result = halt; capture = selected_capture;
    adapter.rWlanInfo = 123; glue.prAdapter = &adapter;
    glue.hif_thread = glue.rx_thread = glue.main_thread = &glue;
    glue.waitq_hif = glue.rHifHaltComp = 0; glue.waitq_rx = glue.rRxHaltComp = 1;
    glue.waitq = glue.rHaltComp = 2;
    netdev.ieee80211_ptr = &wireless; netdev.glue = &glue; wireless.netdev = &netdev;
    arWlanDevInfo[0].prDev = &netdev; u4WlanDevNum = selected_mode == 3 ? 0 : 1;
    if (selected_mode == 4) arWlanDevInfo[0].prDev = NULL;
    if (selected_mode == 5) netdev.glue = NULL;
    gBtWifiGpsState = 1UL << WMT_WIFI_ON;
    pfWlanRemove = wlanRemove; mtk_wcn_wlan_remove = HifAhbRemove;
    static struct func_ops ops = {.func_off = off_callback};
    gpWmtFuncOps[WMTDRV_TYPE_WIFI] = selected_mode == 2 ? NULL : &ops;
    if (selected_mode == 6) mtk_wcn_wlan_remove = NULL;
    gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WIFI] = DRV_STS_FUNC_ON;
    gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WMT] = DRV_STS_FUNC_ON;
    gMtkWmtCtx.wmtHifConf.hifType = selected_mode == 1 ? WMT_HIF_UART : WMT_HIF_BTIF;
    gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_SDIO1] = selected_mode == 1 ? DRV_STS_FUNC_ON : DRV_STS_POWER_OFF;
    g_pwr_off_flag = true;
    OP op = {.au4OpData = {WMTDRV_TYPE_WIFI}};
    if (selected_mode == 8) {
        gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WIFI] = DRV_STS_POWER_OFF;
        gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_BT] = DRV_STS_FUNC_ON;
        gpWmtFuncOps[WMTDRV_TYPE_BT] = &ops; op.au4OpData[0] = WMTDRV_TYPE_BT;
    }
    return opfunc_func_off(&op);
}
int *get_effects(void) { return effects; }
int effect_count(void) { return count; }
int *get_status(void) { return gMtkWmtCtx.eDrvStatus; }
unsigned int get_frees(void) { return frees; }
unsigned int get_waits(void) { return wait_calls; }
unsigned int get_bad_unlock(void) { return unlock_without_lock; }
int get_held(void) { return held; }
int get_aborts(void) { return aborts; }
int get_summaries(void) { return summaries; }
int get_retained(void) { return glue.main_thread == &glue && glue.hif_thread == &glue &&
    glue.rx_thread == &glue && adapter.rWlanInfo == 123 && wireless.netdev == &netdev; }
'''


def build(work, tree, baseline, label):
    text = re.sub(r'static int off_callback\([^\n]+\n.*?\n}\n', '', common.SHIM, flags=re.S)
    text = text.replace('effects[100]', 'effects[256]').replace('count+4 <= 100', 'count+4 <= 256')
    text += SHIM
    text += extract((tree / WLAN / 'os/linux/gl_init.c').read_text(), 'wlanRemove')
    header = (tree / WLAN / 'os/linux/include/gl_typedef.h').read_text()
    text += re.search(r'^typedef .*\(\*remove_card\).*;', header, re.M).group() + '\n'
    text += 'static remove_card pfWlanRemove;\n'
    text += extract((tree / WLAN / 'os/linux/hif/ahb_sdioLike/ahb.c').read_text(), 'HifAhbRemove')
    text += 'static int (*mtk_wcn_wlan_remove)(void);\n'
    text += extract((baseline / CORE / 'wmt_func.c').read_text(), 'wmt_func_wifi_off')
    text += 'static int off_callback(void *a, void *b) { effect(1); return callback_result ? callback_result : wmt_func_wifi_off(a,b); }\n'
    source = (tree / CORE / 'wmt_core.c').read_text()
    text += common.function(source, 'opfunc_pwr_off') + common.function(source, 'opfunc_func_off') + WRAPPER
    path = work / label
    path.with_suffix('.c').write_text(text)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                    '-Wno-unused-function', '-Wno-unused-but-set-variable', '-shared', '-fPIC',
                    str(path.with_suffix('.c')), '-o', str(path.with_suffix('.so'))], check=True)
    lib = ctypes.CDLL(str(path.with_suffix('.so')))
    lib.get_effects.restype = ctypes.POINTER(ctypes.c_int)
    lib.get_status.restype = ctypes.POINTER(ctypes.c_int)
    return lib



def check_worker_tails(work, baseline):
    header = (baseline / WLAN / 'os/linux/include/gl_kal.h').read_text()
    source = (baseline / WLAN / 'os/linux/gl_kal.c').read_text()
    code = """
#include <assert.h>
struct wake_lock { int unused; };
static int destroyed;
static int wake_lock_active(struct wake_lock *p) { assert(p); return 1; }
static void wake_unlock(struct wake_lock *p) { assert(p); }
static void wake_lock_destroy(struct wake_lock *p) { assert(p); destroyed++; }
"""
    for name in ('KAL_WAKE_LOCK_ACTIVE', 'KAL_WAKE_UNLOCK', 'KAL_WAKE_LOCK_DESTROY'):
        code += re.search(r'^#define ' + name + r'[^\n]*\\\n[^\n]*', header, re.M).group() + '\n'
    for name, completion, lock in (('hif_thread', 'rHifHaltComp', 'rHifThreadWakeLock'),
                                   ('rx_thread', 'rRxHaltComp', 'rRxThreadWakeLock'),
                                   ('tx_thread', 'rHaltComp', 'rTxThreadWakeLock')):
        body = extract(source, name)
        marker = 'complete(&prGlueInfo->' + completion + ');'
        assert body.count(marker) == 1
        tail = body[body.index(marker) + len(marker):]
        # Deliberately provide no prGlueInfo: a surviving adapter expression fails compilation.
        code += f'int tail_{name}(void) {{ struct wake_lock {lock};\n' + tail
    code += 'int main(void) { tail_hif_thread(); tail_rx_thread(); tail_tx_thread(); assert(destroyed == 3); }\n'
    path = work / 'worker-tails'
    path.with_suffix('.c').write_text(code)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    str(path.with_suffix('.c')), '-o', str(path)], check=True)
    subprocess.run([str(path)], check=True)


def calls(lib):
    return list(lib.get_effects()[:lib.effect_count()])[::4]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('child', type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/remove-retain-sources.json').read_text())
    for section, tree in (('parents', args.parent), ('outputs', args.child),
                          ('baseline_support', args.parent)):
        for path, expected in pins[section].items():
            assert hashlib.sha256((tree / path).read_bytes()).hexdigest() == expected, path
    compared = retained = 0
    with tempfile.TemporaryDirectory(prefix='wifi-remove-retain-') as directory:
        work = Path(directory)
        check_worker_tails(work, args.parent)
        old = build(work, args.parent, args.parent, 'parent')
        new = build(work, args.child, args.parent, 'child')
        for mode in range(9):
            for mask in range(8):
                for halt in (0, -62, -4):
                    for capture in (0, 1):
                        params = (mask, halt, mode, capture)
                        before, after = old.run(*params), new.run(*params)
                        failed = mode not in (0, 1, 8) or (mode != 8 and (mask != 7 or halt))
                        if not failed:
                            assert before == after and calls(old) == calls(new), params
                            assert list(old.get_status()[:11]) == list(new.get_status()[:11]), params
                            assert old.get_frees() == new.get_frees(), params
                        else:
                            assert after != 0, params
                            assert new.get_frees() == 0 and new.get_retained(), params
                            assert new.get_status()[3] == 2 and new.get_status()[4] == 2, params
                            assert not any(n in calls(new) for n in (3, 4, 5, 72, 73, 74, 75, 76, 78)), params
                            assert new.get_held() == 0 and new.get_bad_unlock() == 0, params
                            if mode in (0, 1):
                                assert new.get_waits() == (0 if halt else 3), params
                                assert new.get_aborts() == capture, params
                                assert new.get_summaries() == (capture if not halt else 0), params
                                assert old.get_frees() > 0, params
                            retained += 1
                        compared += 1
    print(f'native_remove_ahb_wmt_comparisons={compared} retained_failure_cases={retained} result=pass')
    print('scope=injected native OFF call chain; no live workers, hardware, reset or recovery')


if __name__ == '__main__':
    main()
