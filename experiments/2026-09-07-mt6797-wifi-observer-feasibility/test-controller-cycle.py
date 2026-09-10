#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute controller ioctl cases, request observer and writer with injected workers."""
import ctypes
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('controller_request', HERE / 'test-request-capture.py')
request = importlib.util.module_from_spec(spec)
spec.loader.exec_module(request)
r = request.r
REL = 'drivers/misc/mediatek/connectivity/common/common_main/'
DETECT = 'drivers/misc/mediatek/connectivity/common/common_detect/'

SHIM = r'''
typedef u32 __le32;
#define cpu_to_le32(n) ((u32)(n))
static int atomic_cmpxchg(atomic_t *p, int old, int value) {
    int before=p->counter; if(before==old) p->counter=value; return before;
}
#define CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR 1
#define WMT_IOCTL_SET_STP_MODE 0x4004a005U
#define WMT_IOCTL_FUNC_ONOFF_CTRL 0x4004a006U
#define WMT_OPID_HIF_CONF 7
#define WMT_OP_HIF_BIT 1
#define MTK_WCN_BOOL_FALSE 0
#define WMT_INFO_FUNC(...) ((void)0)
#define WMT_DBG_FUNC(...) ((void)0)
#define osal_memcpy memcpy
typedef int MTK_WCN_BOOL;
typedef struct { u32 data[4]; } WMT_HIF_CONF, *P_WMT_HIF_CONF;
static WMT_HIF_CONF configuration = {{3, 2, 0, 0}};
static int hif_info, hif_calls, on_calls, off_calls;
static unsigned int initializer_calls;
struct file { int unused; };
static long wmt_capture_initialize(unsigned long arg) { assert(!arg);initializer_calls++;return 0; }
#define _IO(type, nr) (((type) << 8) | (nr))
#define _IOW(type, nr, size) (0x40000000U | (sizeof(size) << 16) | _IO(type, nr))
static int set_error, allocation_error, config_error, request_fault;
static int wmt_lib_set_hif(unsigned long arg) { assert(arg==0x23);hif_calls++;return set_error; }
static P_OSAL_OP wmt_lib_get_free_op(void) { return allocation_error ? NULL : &operations[0]; }
static P_WMT_HIF_CONF wmt_lib_get_hif(void) { return &configuration; }
static int wmt_lib_put_act_op(P_OSAL_OP op) {
    assert(op==&operations[0] && op->signal.timeoutValue==4000);
    assert(op->op.opId==WMT_OPID_HIF_CONF && op->op.u4InfoBit==WMT_OP_HIF_BIT);
    assert(!memcmp(op->op.au4OpData,&configuration,sizeof(configuration)));
    return !config_error;
}
static int native_function(bool on) {
    P_OSAL_OP op=&operations[1];
    assert(current==&tasks[0] && hif_info && ramoops_capture_active());
    if(on) on_calls++; else off_calls++;
    op->op.opId=on ? 3 : 4;op->op.au4OpData[0]=3;
    mt6797_wfc_request_bind(op,op->op.opId,3,4000);
    wfc_request_submit(op);current=&tasks[1];wfc_request_worker_begin(op);
    if(on && request_fault!=1) {
        for(unsigned int stage=1;stage<=3;stage++) mt6797_wfc_request_firmware(stage,1,1,0);
    } else if(!on) {
        mt6797_wfc_request_common_begin();mt6797_wfc_request_common_end();
    }
    if(request_fault==2) wfc_request_reset();
    wfc_request_worker_end(op,request_fault==4 ? -EIO : 0);
    current=&tasks[0];
    wfc_request_wait(op,request_fault==3 ? 0 : 10,true,request_fault==4 ? -EIO : 0,request_fault!=4);
    return request_fault!=4;
}
static int mtk_wcn_wmt_func_on(unsigned int type) { assert(type==3);return native_function(true); }
static int mtk_wcn_wmt_func_off(unsigned int type) { assert(type==3);return native_function(false); }
'''
WRAPPER = r'''
void configure_fault(int set, int allocation, int worker) {
    set_error=set;allocation_error=allocation;config_error=worker;
}
void function_fault(int fault) { request_fault=fault; }
void other_task(void) { current=&tasks[2]; }
int native_calls(unsigned int direction) { return direction==0 ? hif_calls : direction==1 ? on_calls : off_calls; }
'''


def build(root, tree):
    base = request.SHIM.replace(
        'typedef struct { struct { unsigned int opId, au4OpData[1]; } op; } OSAL_OP, *P_OSAL_OP;',
        'typedef struct { u32 timeoutValue; } OSAL_SIGNAL, *P_OSAL_SIGNAL;\n'
        'typedef struct { OSAL_SIGNAL signal; struct { u32 opId, au4OpData[4], u4InfoBit; } op; } OSAL_OP, *P_OSAL_OP;')
    source = request.dma.writer.SHIM + base
    writer = (tree / 'fs/pstore/wifi_capture.h').read_text()
    assert writer == (HERE / 'capture-slot-writer.h').read_text()
    source += request.dma.without_includes(writer)
    source += request.dma.EXTRA.replace('return wfc_slot_write(&state, kind, tx, p, n);',
                                       'if(++attempts==loss_site) drop=writes+1;\n'
                                       'return wfc_slot_write(&state, kind, tx, p, n);')
    source += request.dma.without_includes((tree / request.HEADER).read_text())
    source += SHIM
    header = (tree / DETECT / 'wmt_detect.h').read_text()
    source += next(line for line in header.splitlines() if line.startswith('#define WMT_DETECT_IOC_MAGIC')) + '\n'
    start = header.index('struct wmt_capture_identity {')
    source += header[start:header.index('#endif', start)]
    detector = (tree / DETECT / 'wmt_detect.c').read_text()
    start = detector.index('static long wmt_detect_unlocked_ioctl(')
    source += detector[start:detector.index('\n}', start) + 2]
    source += r'''
long detect(unsigned int cmd) {
    assert(sizeof(struct wmt_capture_identity)==96 && COMBO_IOCTL_CAPTURE_INIT==0x40607709);
    return wmt_detect_unlocked_ioctl(NULL,cmd,0);
}
unsigned int init_calls(void) { return initializer_calls; }
'''
    native = (tree / REL / 'linux/wmt_dev.c').read_text()
    helpers = native[native.index('static atomic_t wmt_capture_hif_attempted'):native.index('/* INT32 WMT_ioctl')]
    source += '#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n' + helpers
    cases = native[native.index('\tcase WMT_IOCTL_SET_STP_MODE:'):native.index('\tcase WMT_IOCTL_LPBK_POWER_CTRL:')]
    source += 'int control(unsigned int cmd, unsigned long arg) { int iRet=0;switch(cmd) {\n'
    source += cases + 'default:assert(0); } return iRet; }\n'
    fresh = request.WRAPPER.replace('wfc_request_id=wfc_request_common=attempts=0;',
                                    'wfc_request_firmware_stage=wfc_request_firmware_device=wfc_request_firmware_image=0;\n'
                                    'hif_info=hif_calls=on_calls=off_calls=set_error=allocation_error=config_error=request_fault=0;\n'
                                    'wmt_capture_hif_attempted.counter=0;initializer_calls=0;current=&tasks[0];\n'
                                    'wfc_request_id=wfc_request_common=attempts=0;')
    source += fresh + WRAPPER
    (root / 'controller.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-Wno-unused-parameter', '-shared', '-fPIC', str(root / 'controller.c'), '-o', str(root / 'controller.so')], check=True)
    lib = ctypes.CDLL(str(root / 'controller.so'))
    lib.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    lib.control.argtypes = [ctypes.c_uint, ctypes.c_ulong]
    return lib


def tests(lib):
    mode, function, on = 0x4004a005, 0x4004a006, 0x80000003
    lib.fresh(0, 0)
    assert lib.detect(0x770a) == 0x57464301 and lib.init_calls() == lib.store_count() == 0
    assert lib.detect(0x80047704) < 0 and lib.init_calls() == 0
    assert lib.detect(0x40607709) == 0 and lib.init_calls() == 1
    lib.fresh(1, 0)
    assert lib.control(mode, 0x23) == lib.control(function, on) == lib.control(function, 3) == 0
    decoded = r.decode_pmsg(bytes(lib.data()[:r.ZONE_PAYLOAD_BYTES]), request.CYCLE, bytes(range(80)))
    assert decoded['producer_status'] == 1 and lib.pins() == 0
    assert [r.TRANSPORT.unpack(row['payload']) for row in decoded['records'][1:3]] == [(1, 0x23, 0), (2, 0x23, 0)]
    count = len(decoded['records']) - 1
    assert [lib.native_calls(i) for i in range(3)] == [1, 1, 1]
    assert lib.control(function, 3) < 0 and lib.native_calls(2) == 1
    for arg in (3, 0x100000023):
        lib.fresh(1, 0)
        assert lib.control(mode, arg) < 0 and lib.native_calls(0) == 0
    lib.fresh(0, 0)
    assert lib.control(mode, 0x23) < 0 and lib.native_calls(0) == 0
    lib.fresh(1, 0)
    assert lib.control(function, on) < 0 and lib.native_calls(1) == 0
    lib.fresh(1, 0)
    assert lib.control(mode, 0x23) == 0 and lib.control(mode, 0x23) < 0
    assert lib.control(function, on) < 0 and lib.native_calls(1) == 0
    for fault in ((-5, 0, 0), (0, 1, 0), (0, 0, 1)):
        lib.fresh(1, 0);lib.configure_fault(*fault)
        assert lib.control(mode, 0x23) < 0
        assert lib.control(function, on) < 0 and lib.native_calls(1) == 0
    for fault in range(1, 5):
        lib.fresh(1, 0);lib.function_fault(fault)
        assert lib.control(mode, 0x23) == 0 and lib.control(function, on) < 0
        assert lib.control(function, 3) < 0 and lib.native_calls(2) == 0
    for arg in (3, 0x180000003):
        lib.fresh(1, 0);assert lib.control(mode, 0x23) == 0
        assert lib.control(function, arg) < 0 and lib.native_calls(1) == lib.native_calls(2) == 0
    for changed_task in (False, True):
        lib.fresh(1, 0)
        assert lib.control(mode, 0x23) == lib.control(function, on) == 0
        if changed_task: lib.other_task()
        assert lib.control(function, 3 if changed_task else on) < 0
        assert lib.native_calls(1) == 1 and lib.native_calls(2) == 0
    for lost in range(1, count + 1):
        lib.fresh(1, lost)
        result = lib.control(mode, 0x23)
        if result == 0: result = lib.control(function, on)
        if result == 0: result = lib.control(function, 3)
        assert result < 0, lost
        assert lib.native_calls(0) <= 1 and lib.native_calls(1) <= 1 and lib.native_calls(2) <= 1
    print(f'PASS: native controller cases, request/firmware gates, task/argument/order refusals and {count} lost records')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='wifi-controller-test-') as directory:
        tests(build(Path(directory), Path(sys.argv[1])))
