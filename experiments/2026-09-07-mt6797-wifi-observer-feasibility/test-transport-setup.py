#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the native HIF ioctl case with injected allocation/worker results."""
from pathlib import Path
import subprocess
import sys
import tempfile


source = (Path(sys.argv[1]) / "drivers/misc/mediatek/connectivity/common/common_main/linux/wmt_dev.c").read_text()
case = source.split("\tcase WMT_IOCTL_SET_STP_MODE:", 1)[1].split("\tcase WMT_IOCTL_FUNC_ONOFF_CTRL:", 1)[0]
harness = r'''
#include <assert.h>
#include <errno.h>
#include <string.h>
typedef int MTK_WCN_BOOL;
typedef struct { unsigned int timeoutValue; } OSAL_SIGNAL, *P_OSAL_SIGNAL;
typedef struct { unsigned int data[4]; } WMT_HIF_CONF, *P_WMT_HIF_CONF;
typedef struct { OSAL_SIGNAL signal; struct { int opId; unsigned int au4OpData[4]; unsigned int u4InfoBit; } op; } OSAL_OP, *P_OSAL_OP;
#define WMT_INFO_FUNC(...) ((void)0)
#define WMT_DBG_FUNC(...) ((void)0)
#define WMT_OPID_HIF_CONF 7
#define WMT_OP_HIF_BIT 1
#define MTK_WCN_BOOL_FALSE 0
#define osal_memcpy memcpy
static OSAL_OP operation;
static WMT_HIF_CONF configuration = {{3, 2, 0, 0}};
static int set_result, no_operation, worker_result, submitted, hif_info;
static int wmt_lib_set_hif(unsigned long arg) { assert(arg == 0x23); return set_result; }
static P_OSAL_OP wmt_lib_get_free_op(void) { return no_operation ? 0 : &operation; }
static P_WMT_HIF_CONF wmt_lib_get_hif(void) { return &configuration; }
static int wmt_lib_put_act_op(P_OSAL_OP op) {
    assert(op == &operation && op->op.opId == WMT_OPID_HIF_CONF);
    assert(op->op.u4InfoBit == WMT_OP_HIF_BIT);
    assert(!memcmp(op->op.au4OpData, &configuration, sizeof(configuration)));
#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR
    assert(op->signal.timeoutValue == 4000);
#else
    assert(op->signal.timeoutValue == 0);
#endif
    submitted++;
    return worker_result;
}
static int configure(void) {
    int iRet = 0;
    unsigned long arg = 0x23;
    switch (0) {
    case 0:
''' + case + r'''
    }
    return iRet;
}
int main(void) {
    set_result = -EINVAL;
    assert(configure() == -EINVAL && !submitted && !hif_info);
    set_result = 0; no_operation = 1;
    assert(configure() == -ENOMEM && !submitted && !hif_info);
    no_operation = 0; worker_result = 0;
    assert(configure() == -EFAULT && submitted == 1 && !hif_info);
    worker_result = 1;
    assert(configure() == 0 && submitted == 2 && hif_info == 1);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="wmt-transport-test-") as directory:
    work = Path(directory)
    (work / "test.c").write_text(harness)
    for experimental in (False, True):
        flags = ["-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR"] if experimental else []
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", *flags,
                        str(work / "test.c"), "-o", str(work / "test")], check=True)
        subprocess.run([str(work / "test")], check=True)
print("PASS: ordinary/experimental HIF case, four outcomes each; wait value and copied operation checked")
