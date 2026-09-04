#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute actual late-probe/remove bodies with injected devres and faults."""
import argparse
import hashlib
from pathlib import Path
import resource
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
source = args.source.resolve()
assert str(source) == '/workspace/gemini-pda/src/linux-7.1.3-series-source'
text = (source / 'drivers/thermal/mediatek/auxadc_thermal.c').read_text()
start = text.index('\t/* Drain all public readers before closing the V4 transaction. */')
end = text.index('\nfail_transaction:', start)
finish = text[start:end]
start = text.index('static void mtk_thermal_remove(')
remove = text[start:text.index('\n}', start) + 2]
assert finish.index('devres_open_group(') < finish.index('devm_thermal_of_zone_register(')
assert finish.index('devres_close_group(') > finish.index('devm_device_add_group(')
assert remove.index('devres_release_group(') < remove.index('mtk_thermal_transaction_close(')
preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define ENOMEM 12
#define EIO 5
#define GFP_KERNEL 0
#define MTK_THERMAL_V4 4
#define IS_ENABLED(x) 1
#define IS_ERR(x) ((intptr_t)(x) < 0)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define GEMINI_MT6797_THERMAL_ZONE_REGISTER 1
#define GEMINI_MT6797_THERMAL_PROBE_COMPLETE 2
#define GEMINI_MT6797_THERMAL_LEDGER_BEFORE 1
#define GEMINI_MT6797_THERMAL_LEDGER_AFTER 2
#define GEMINI_MT6797_THERMAL_LEDGER_TERMINAL 3
#define GEMINI_MT6797_THERMAL_LEDGER_SUCCESS 1
#define GEMINI_MT6797_THERMAL_LEDGER_FAILURE 2
struct config { int version; };
static const struct config mt6797_thermal_data = {4};
struct mtk_thermal { const struct config *conf; int transaction; };
struct device { struct mtk_thermal *mt; };
struct platform_device { struct device dev; };
struct thermal_zone_device { int unused; };
struct mtk_thermal_transaction_ops { int unused; };
static const struct mtk_thermal_transaction_ops mt6797_thermal_transaction_ops = {};
static const int mtk_thermal_ops, mt6797_observer_group;
static struct thermal_zone_device zone;
static int fault, resources, opened, sealed, closes, releases, last_resource;
static struct mtk_thermal *platform_get_drvdata(struct platform_device *p) { return p->dev.mt; }
static void dev_warn(struct device *d, const char *s, ...) { (void)d; (void)s; }
static void *devres_open_group(struct device *d, void *id, int flags) {
    (void)d; (void)flags; assert(!opened && !resources);
    if (fault==1) return NULL;
    opened=1; return id;
}
static void devres_close_group(struct device *d, void *id) {
    (void)d; (void)id; assert(opened && !sealed); sealed=1;
}
static int devres_release_group(struct device *d, void *id) {
    (void)d; (void)id; assert(opened);
    /* Adapter follows the kernel's independently audited reverse release. */
    for (int bit=4;bit;bit>>=1) if (resources & bit) {
        assert(bit<last_resource); last_resource=bit; resources &= ~bit;
    }
    opened=sealed=0; releases++; return 0;
}
static void mtk_thermal_transaction_close(struct mtk_thermal *mt,
                const struct mtk_thermal_transaction_ops *ops, int *state) {
    (void)mt; (void)ops; (void)state;
    assert(!resources && !opened); closes++;
}
static int mt6797_thermal_probe_trace(int stage,int phase,int ret,int flags) {
    (void)flags;
    if ((fault==2 && stage==1 && phase==1) || (fault==4 && stage==1 && phase==2) ||
        (fault==6 && stage==2 && phase==3)) return -EIO;
    return ret;
}
static struct thermal_zone_device *devm_thermal_of_zone_register(struct device *d,
                int id, struct mtk_thermal *mt, const int *ops) {
    (void)d; (void)id; (void)mt; (void)ops;
    if (fault==3) return (void *)(intptr_t)-EIO;
    resources |= 1; return &zone;
}
static int devm_thermal_add_hwmon_sysfs(struct device *d, struct thermal_zone_device *tz) {
    (void)d; (void)tz; if (fault==5) return -EIO; resources |= 2; return 0;
}
static int devm_device_add_group(struct device *d,const int *group) {
    (void)d; (void)group; if (fault==7) return -EIO; resources |= 4; return 0;
}
static int probe_finish(struct platform_device *pdev, struct mtk_thermal *mt, bool traced) {
    const struct mtk_thermal_transaction_ops *ops=&mt6797_thermal_transaction_ops;
    bool is_v4=mt->conf->version==MTK_THERMAL_V4, readers_group=false;
    struct thermal_zone_device *tzdev;
    int ret;
'''
main = r'''
int main(void) {
    struct mtk_thermal mt={.conf=&mt6797_thermal_data};
    struct platform_device p={.dev={.mt=&mt}};
    for (fault=0;fault<8;fault++) {
        resources=opened=sealed=closes=releases=0; last_resource=8;
        int ret=probe_finish(&p,&mt,true);
        bool failure=fault==1 || fault==2 || fault==3 || fault==4 || fault==6;
        assert((ret<0)==failure);
        if (failure) { assert(!resources && !opened && closes==1); assert(releases==(fault!=1)); }
        else { assert(opened && sealed && closes==0); mtk_thermal_remove(&p); assert(closes==1 && releases==1 && !resources); }
    }
    p.dev.mt=NULL; mtk_thermal_remove(&p);
    const struct config other={.version=3}; mt.conf=&other; p.dev.mt=&mt;
    int old=closes; mtk_thermal_remove(&p); assert(closes==old);
    puts("late_probe_paths=8 remove_before_close=pass allocation_refusal=pass nonV4_remove_unchanged=pass");
}
'''
program = preamble + finish + '\n}\n' + remove + '\n' + main
managed = Path('/workspace/gemini-pda/thermal-observer-work')
managed.mkdir(exist_ok=True)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
with tempfile.TemporaryDirectory(prefix='lifetime-oracle.', dir=managed) as work:
    root=Path(work)
    command=['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(root/'test.c'),'-o',str(root/'test')]
    (root/'test.c').write_text(program)
    subprocess.run(command,check=True)
    subprocess.run([str(root/'test')],check=True,timeout=10)
    mutations={
        'missing-remove-drain': program.replace(remove,remove.replace('devres_release_group(&pdev->dev, mt);','(void)pdev;')),
        'missing-failure-drain': program.replace('if (readers_group)\n\t\tdevres_release_group(&pdev->dev, mt);','if (readers_group)\n\t\t(void)pdev;'),
        'unsealed-success': program.replace('devres_close_group(&pdev->dev, mt);','(void)pdev;'),
    }
    for name,mutant in mutations.items():
        assert mutant!=program,name
        (root/'test.c').write_text(mutant)
        subprocess.run(command+['-Wno-unused-function'],check=True)
        result=subprocess.run([str(root/'test')],capture_output=True,timeout=10)
        assert result.returncode!=0,name
print('lifetime_mutations_rejected=3')
print('driver_sha256='+hashlib.sha256(text.encode()).hexdigest())
