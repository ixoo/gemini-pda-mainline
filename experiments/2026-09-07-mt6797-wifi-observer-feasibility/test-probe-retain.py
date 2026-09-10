#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise pinned startup cleanup and ON callers with injected kernel effects."""
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
BASE = Path('drivers/misc/mediatek/connectivity')
GL = BASE / 'wlan/gen3/os/linux/gl_init.c'
AHB = BASE / 'wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c'
LIB = BASE / 'wlan/gen3/common/wlan_lib.c'
CORE = BASE / 'common/common_main/core/wmt_core.c'
FUNC = BASE / 'common/common_main/core/wmt_func.c'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


common = module('probe_common', 'test-common-off-errors.py')
def extract(source, name):
    # Native functions end in column zero; alternatives may have unequal braces.
    match = re.search(r'^[^\n;]*\b' + re.escape(name) + r'\([^;]*?\)\n\{', source, re.M)
    assert match, name
    end = source.index('\n}', match.end()) + 2
    return source[match.start():end] + '\n'


SHIM = r'''
#include <errno.h>
#include <stdint.h>
#ifndef EUCLEAN
#define EUCLEAN 117
#endif
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define VOID void
#define PVOID void *
#define INT_32 int
#define TRUE 1
#define FALSE 0
#define WLAN_STATUS_SUCCESS 0
#define CONFIG_OF 1
#define WMT_HIF_SDIO 1
#define MTK_WCN_BOOL_TRUE true
#define WMT_DBG_FUNC(...) ((void)0)
#define DBGLOG(...) ((void)0)
#define WMT_CHIP_TYPE_COMBO 1
#define FUNC_ON 1
#define WMT_WIFI_ON 0
#define WMT_GPS_ON 2
#define WMT_CTRL_BGW_DESENSE_CTRL 99
#define WMT_OPID_MAX 4
static bool hif_probe_retained, wmt_probe_retained;
static int probe_result, removes, paldo, resets, gWifiProbed;
static unsigned long gBtWifiGpsState;
struct platform { int dev; } platform, *HifAhbPDev = &platform;
typedef void *P_WMT_IC_OPS, *P_WMT_GEN_CONF;
static int probe(void *dev) { assert(dev == &platform.dev); effect(10); return probe_result; }
static int remove_card(void) { removes++; effect(11); return 0; }
static int (*pfWlanProbe)(void *) = probe;
static int (*pfWlanRemove)(void) = remove_card;
static void mtk_wcn_consys_hw_wifi_paldo_ctrl(int on) { paldo += on ? 1 : -1; effect(12+on); }
static int wmt_detect_get_chip_type(void) { return 0; }
static int wmt_func_wifi_ctrl(int on) { assert(on); return 0; }
static void osal_set_bit(int bit, unsigned long *p) { *p |= 1UL << bit; }
static int osal_test_bit(int bit, unsigned long *p) { return !!(*p & (1UL << bit)); }
static void mtk_wcn_set_connsys_power_off_flag(bool value) { g_pwr_off_flag=value; }
static void mtk_wcn_wmt_system_state_reset(void) { resets++; }
static int opfunc_pwr_on(P_WMT_OP op) { (void)op; assert(0); return -1; }
static int (*wmt_core_opfunc[WMT_OPID_MAX])(P_WMT_OP);
'''

WRAPPER = r'''
int run(int result, int uart, int bt) {
    memset(&gMtkWmtCtx,0,sizeof(gMtkWmtCtx)); memset(gpWmtFuncOps,0,sizeof(gpWmtFuncOps));
    hif_probe_retained=wmt_probe_retained=false;
    gBtWifiGpsState=0; removes=paldo=resets=count=0;
    stp_result=hardware_result=0; probe_result=result;
    gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WMT]=DRV_STS_FUNC_ON;
    if(bt) gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_BT]=DRV_STS_FUNC_ON;
    gMtkWmtCtx.wmtHifConf.hifType=uart ? WMT_HIF_UART : WMT_HIF_BTIF;
    static struct func_ops ops={.func_on=wmt_func_wifi_on};
    gpWmtFuncOps[WMTDRV_TYPE_WIFI]=&ops;
    wmt_core_opfunc[0]=opfunc_func_on;
    wmt_core_opfunc[1]=opfunc_pwr_off;
    OP op={.opId=0,.au4OpData={WMTDRV_TYPE_WIFI}};
    return wmt_core_opid(&op);
}
int retry_dispatch(int opid) { OP op={.opId=opid,.au4OpData={WMTDRV_TYPE_WIFI}}; return wmt_core_opid(&op); }
int retry_hif(int off) { return off ? HifAhbRemove() : HifAhbProbe(); }
int get_removes(void) { return removes; }
int get_paldo(void) { return paldo; }
int get_resets(void) { return resets; }
int get_count(void) { return count; }
int get_wifi(void) { return gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WIFI]; }
int get_common(void) { return gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_WMT]; }
int get_sdio(void) { return gMtkWmtCtx.eDrvStatus[WMTDRV_TYPE_SDIO1]; }
int get_wifi_bit(void) { return !!(gBtWifiGpsState & 1); }
int *get_effects(void) { return effects; }
'''

LOCAL = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#define EUCLEAN 117
#define INT_32 int
#define TRUE 1
#define FALSE 0
#define CFG_SUPPORT_MULTITHREAD 1
#define WLAN_STATUS_SUCCESS 0
#define DBGLOG(...) ((void)0)
#define GLUE_FLAG_HALT_BIT 2
#define IS_ERR(p) ((intptr_t)(p) < 0 && (intptr_t)(p) >= -4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
struct glue { unsigned int u4ReadyFlag; unsigned long ulFlag; void *prDevHandler;
    void *main_thread, *hif_thread, *rx_thread; int waitq,waitq_hif,waitq_rx,rHaltComp; } glue;
typedef struct glue *P_GLUE_INFO_T;
struct wireless { void *netdev; } wireless;
static int created, fail_at, scheduled, wakes, cleanup, halted, aborted;
static int tx_thread, hif_thread, rx_thread;
static void *kthread_run(int fn,void *dev,const char *name) {
    (void)fn;(void)dev;(void)name; int n=created++; return n==fail_at ? (void *)(intptr_t)-12 : (void *)(intptr_t)(n+1);
}
static void wfc_dma_abort(void) { aborted++; }
static void kalSetHalted(int value) { halted=value; }
static void set_bit(int bit,unsigned long *p) { *p |= 1UL<<bit; }
static void wake_up_interruptible(int *p) { (void)p; wakes++; }
static int wait_for_completion_interruptible(int *p) { (void)p; return -4; }
static void kalMetRemoveProcfs(void) { cleanup++; }
static void wlanNetUnregister(void *p) { (void)p;cleanup++; }
static void wlanAdapterStop(void *p,int caller) { (void)p;assert(caller==2);cleanup++; }
static void *private_glue=&glue;
static void *netdev_priv(void *p) { (void)p; return &private_glue; }
static void glBusFreeIrq(void *a,void *b) { (void)a;(void)b;cleanup++; }
static void wlanWakeLockUninit(void *p) { (void)p;cleanup++; }
static void wlanNetDestroy(void *p) { (void)p;cleanup++; }
static void nicRxUninitialize(void *p) { (void)p;cleanup++; }
static void nicTxRelease(void *p,int n) { (void)p;(void)n;cleanup++; }
static void nicUninitSystemService(void *p) { (void)p;cleanup++; }
static void nicReleaseAdapterMemory(void *p) { (void)p;cleanup++; }
static void wlanPollingCpupcr(int n,int delay) { (void)n;(void)delay;cleanup++; }
#define HAL_SET_INTR_STATUS_READ_CLEAR(p) ((void)(p))
#define HAL_SET_MAILBOX_READ_CLEAR(p,v) ((void)(p),(void)(v))
static void nicEnableInterrupt(void *p) { (void)p;scheduled++; }
'''


def compile_library(code, work, name):
    path=work/name
    path.with_suffix('.c').write_text(code)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',
                    '-Wno-unused-parameter','-Wno-unused-function','-Wno-unused-variable',
                    '-Wno-unused-but-set-variable','-shared','-fPIC',
                    str(path.with_suffix('.c')),'-o',str(path.with_suffix('.so'))],check=True)
    return ctypes.CDLL(str(path.with_suffix('.so')))


def callers(tree, work, name):
    shim=common.SHIM.replace('ULONG au4OpData[1];','UINT32 opId; ULONG au4OpData[1];')
    shim=shim.replace('int (*func_off)(void *, void *);','int (*func_off)(void *, void *); int (*func_on)(void *, void *);')
    shim=shim.replace('assert(!*two);','if (*two) { assert(op==WMT_CTRL_SDIO_HW && *two==1); effect(14); return 0; }')
    code=shim+SHIM
    ahb=(tree/AHB).read_text(); core=(tree/CORE).read_text(); func=(tree/FUNC).read_text()
    code+=extract(ahb,'HifAhbProbe')+extract(ahb,'HifAhbRemove')
    code+='static int (*mtk_wcn_wlan_probe)(void)=HifAhbProbe;\n'
    code+=extract(func,'wmt_func_wifi_on')
    for fn in ('opfunc_pwr_off','opfunc_func_on','wmt_core_opid_handler','wmt_core_opid'):
        code+=extract(core,fn)
    lib=compile_library(code+WRAPPER,work,name)
    lib.get_effects.restype=ctypes.POINTER(ctypes.c_int)
    return lib


def local(tree, work, name):
    gl=(tree/GL).read_text(); probe=extract(gl,'wlanProbe'); adapter=extract((tree/LIB).read_text(),'wlanAdapterStart')
    enum=re.search(r'enum ENUM_PROBE_FAIL_REASON \{.*?\} eFailReason;',probe,re.S).group()
    start=probe.index('\t\tprGlueInfo->main_thread = kthread_run(')
    end=probe.index('\t\t/* TODO the change schedule API',start)
    creation=probe[start:end]
    start=probe.index('\t\tDBGLOG(INIT, ERROR, "wlanProbe: probe failed')
    tail=probe[start:]
    code=LOCAL+(extract(gl,'wlanProbeRetain') if 'static INT_32 wlanProbeRetain(' in gl else '')
    code+='''int run_workers(int fail, int late, int attempted) {
    memset(&glue,0,sizeof(glue)); glue.u4ReadyFlag=1;
    created=scheduled=wakes=cleanup=halted=aborted=0; fail_at=fail;
    P_GLUE_INFO_T prGlueInfo=&glue; void *prAdapter=&glue; struct wireless *prWdev=&wireless;
    int i4Status=0; bool retain_failure=attempted;
'''+enum+'''
    eFailReason=late ? PROC_INIT_FAIL : NET_REGISTER_FAIL;
    if(attempted==1) { do {
'''+creation+'''
    scheduled++;
    } while(false); }
    if(late || !attempted) i4Status=-5;
    if(!attempted) eFailReason=BUS_SET_IRQ_FAIL;
    if(i4Status) {
'''+tail+'\n'
    enum=re.search(r'enum ENUM_ADAPTER_START_FAIL_REASON \{.*?\} eFailReason;',adapter,re.S).group()
    start=adapter.rindex('\tif (u4Status == WLAN_STATUS_SUCCESS) {')
    code+='''int run_adapter(int status,int reason) {
    cleanup=scheduled=0; void *prAdapter=&glue; int u4Status=status;
'''+enum+'\n eFailReason=reason;\n'+adapter[start:]+'\n'
    for var in ('created','scheduled','wakes','cleanup','halted','aborted'):
        code+=f'int get_{var}(void) {{ return {var}; }}\n'
    return compile_library(code,work,name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent',type=Path);parser.add_argument('child',type=Path)
    args=parser.parse_args()
    pins=json.loads((HERE/'results/probe-retain-sources.json').read_text())
    for group,tree in (('parents',args.parent),('outputs',args.child)):
        for path,digest in pins[group].items():
            assert hashlib.sha256((tree/path).read_bytes()).hexdigest()==digest,path
    count=0
    with tempfile.TemporaryDirectory(prefix='wifi-probe-retain-') as directory:
        work=Path(directory)
        old,new=[callers(tree,work,name) for tree,name in ((args.parent,'old'),(args.child,'new'))]
        for status in (0,-5,-117):
            for uart in (0,1):
                for bt in (0,1):
                    before,after=old.run(status,uart,bt),new.run(status,uart,bt)
                    if status != -117:
                        assert before==after
                        assert list(old.get_effects()[:old.get_count()])==list(new.get_effects()[:new.get_count()])
                    else:
                        assert before==-1 and after==-117
                        assert old.get_removes()==1 and new.get_removes()==0
                        assert new.get_paldo()==1 and new.get_resets()==0
                        assert new.get_wifi()==new.get_common()==2 and new.get_sdio()==(2 if uart else 0)
                        assert new.get_wifi_bit()==0
                        effects=new.get_count()
                        for op in range(4): assert new.retry_dispatch(op)==-117
                        for off in (0,1): assert new.retry_hif(off)==-117
                        assert new.get_count()==effects and new.get_removes()==0 and new.get_paldo()==1
                    count+=1
        old,new=[local(tree,work,name) for tree,name in ((args.parent,'local-old'),(args.child,'local-new'))]
        for fail in (-1,0,1,2):
            result=new.run_workers(fail,0,1)
            assert result==(0 if fail==-1 else -117)
            assert new.get_created()==(3 if fail==-1 else fail+1)
            assert new.get_scheduled()==(1 if fail==-1 else 0)
            assert new.get_cleanup()==0
            assert new.get_wakes()==(0 if fail==-1 else 3)
            assert new.get_halted()==new.get_aborted()==(0 if fail==-1 else 1)
            count+=1
        assert old.run_workers(-1,1,1)==-5 and old.get_cleanup()>0
        assert new.run_workers(-1,1,1)==-117 and new.get_cleanup()==0 and new.get_wakes()==3
        assert new.run_workers(-1,0,0)==old.run_workers(-1,0,0)==-5
        assert new.get_cleanup()==old.get_cleanup()==2
        assert new.run_workers(-1,1,2)==-117 and new.get_created()==0 and new.get_cleanup()==0
        assert new.get_wakes()==3 and new.get_halted()==1
        count+=3
        for status in (0,1):
            for stage in range(5):
                assert old.run_adapter(status,stage)==new.run_adapter(status,stage)==status
                assert new.get_cleanup()==0
                if status and stage: assert old.get_cleanup()>0
                if not status: assert old.get_scheduled()==new.get_scheduled()==1
                count+=1
    print(f'probe-retain=pass cases={count}; injected startup fragments and native AHB/WMT ON chain')
    print('not_tested=complete probe execution, lower DMA cleanup, scheduler, concurrent reset, hardware or recovery')


if __name__=='__main__':
    main()
