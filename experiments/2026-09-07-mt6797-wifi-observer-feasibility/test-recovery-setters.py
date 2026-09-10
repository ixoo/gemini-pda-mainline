#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute native watchdog setters across an injected takeover/lock race."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = 'drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c'
HEADER = 'drivers/watchdog/mediatek/include/ext_wd_drv.h'
SHIM = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
typedef uint32_t u32;
#define TRUE true
static uint32_t registers[512];
static uint8_t *toprgu_base = (uint8_t *)registers;
static unsigned int timeout, writes;
static int g_wdt_enable = 1;
static bool mtk_wdt_recovery_owned;
static pthread_mutex_t rgu_reg_operation_spinlock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t gate = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed = PTHREAD_COND_INITIALIZER;
static bool reached, proceed;
static _Thread_local bool delayed_lock, held;
#define READ_ONCE(value) (value)
#define pr_debug(...) do { } while (0)
static void spin_lock(pthread_mutex_t *lock)
{
    if (delayed_lock) {
        assert(!pthread_mutex_lock(&gate));
        reached = true;
        assert(!pthread_cond_broadcast(&changed));
        while (!proceed) assert(!pthread_cond_wait(&changed, &gate));
        assert(!pthread_mutex_unlock(&gate));
    }
    assert(!pthread_mutex_lock(lock));
    held = true;
}
static void spin_unlock(pthread_mutex_t *lock)
{
    assert(held);
    held = false;
    assert(!pthread_mutex_unlock(lock));
}
static unsigned int __raw_readl(uint8_t *address)
{
    assert(address >= toprgu_base && address < toprgu_base + sizeof(registers));
    assert((address - toprgu_base) % 4 == 0);
    return registers[(address - toprgu_base) / 4];
}
static void mt_reg_sync_writel(unsigned int value, uint8_t *address)
{
    assert(held);
    assert(address >= toprgu_base && address < toprgu_base + sizeof(registers));
    assert((address - toprgu_base) % 4 == 0);
    registers[(address - toprgu_base) / 4] = value;
    writes++;
}
'''
CASES = r'''
static int operation_result;
static void invoke(unsigned int operation)
{
    operation_result = 0;
    switch (operation) {
    case 0: mtk_wdt_set_time_out_value(3); break;
    case 1: mtk_wdt_mode_config(true, true, true, false, false); break;
    case 2: operation_result = mtk_wdt_enable(WK_WDT_DIS); break;
    case 3: mtk_wdt_restart(WD_TYPE_NORMAL); break;
    default: assert(0);
    }
    assert(!held);
}
static void arm(void)
{
    struct mtk_wdt_recovery_state state;
    assert(!mtk_wdt_recovery_arm(12, &state));
    assert(state.owned && writes == 3 && !held);
}
static void *worker(void *argument)
{
    delayed_lock = true;
    invoke(*(unsigned int *)argument);
    return NULL;
}
int main(void)
{
    for (unsigned int operation = 0; operation < 4; operation++) {
        for (unsigned int ordering = 0; ordering < 3; ordering++) {
            uint32_t snapshot[512];
            pthread_t thread;
            memset(registers, 0, sizeof(registers));
            writes = timeout = 0;
            g_wdt_enable = 1;
            mtk_wdt_recovery_owned = reached = proceed = false;
            if (ordering == 2) {
                assert(!pthread_create(&thread, NULL, worker, &operation));
                assert(!pthread_mutex_lock(&gate));
                while (!reached) assert(!pthread_cond_wait(&changed, &gate));
                assert(!pthread_mutex_unlock(&gate));
            }
            if (ordering) arm();
            memcpy(snapshot, registers, sizeof(snapshot));
            unsigned int before = writes;
            if (ordering == 2) {
                assert(!pthread_mutex_lock(&gate));
                proceed = true;
                assert(!pthread_cond_broadcast(&changed));
                assert(!pthread_mutex_unlock(&gate));
                assert(!pthread_join(thread, NULL));
            } else invoke(operation);
            bool refused = ordering && (CHILD || (operation == 3 && ordering == 1));
            assert((writes == before) == refused);
            if (refused) {
                assert(!memcmp(snapshot, registers, sizeof(snapshot)));
                assert(g_wdt_enable == 1);
                assert(timeout == 0);
            }
            assert(operation_result == ((CHILD && ordering && operation == 2) ? -EBUSY : 0));
        }
    }
    puts(CHILD ? "PASS: 12 child setter orderings" : "PASS: 12 parent setter orderings (race reproduced)");
    return 0;
}
'''


def function(source, name):
    match = re.search(r'^(?:void|int) ' + re.escape(name) + r'\(', source, re.M)
    assert match, name
    return source[match.start():source.index('\n}', match.end()) + 2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('child', type=Path)
    parser.add_argument('support', type=Path, help='pinned mt_wdt.h and wd_api.h')
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/recovery-setters-sources.json').read_text())
    for name, expected in pins['support'].items():
        assert hashlib.sha256((args.support / name).read_bytes()).hexdigest() == expected
    api = (args.support / 'wd_api.h').read_text()
    enums = '\n'.join(re.findall(r'typedef enum (?:wk_wdt_en|wd_restart_type) \{.*?\} \w+;', api, re.S))
    assert enums.count('typedef enum') == 2
    for child, root in enumerate((args.parent, args.child)):
        for path, expected in pins['outputs' if child else 'parents'].items():
            assert hashlib.sha256((root / path).read_bytes()).hexdigest() == expected
        source = (root / SOURCE).read_text()
        header = (root / HEADER).read_text()
        state = re.search(r'struct mtk_wdt_recovery_state \{.*?\};', header, re.S).group()
        bodies = '\n'.join(function(source, name) for name in (
            'mtk_wdt_set_time_out_value', 'mtk_wdt_mode_config', 'mtk_wdt_enable',
            'mtk_wdt_recovery_arm', 'mtk_wdt_restart'))
        with tempfile.TemporaryDirectory(prefix='wifi-recovery-setters-') as directory:
            root = Path(directory)
            cfile, binary = root / 'setters.c', root / 'setters'
            cfile.write_text(SHIM + (args.support / 'mt_wdt.h').read_text() + enums + state + bodies + CASES)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pthread',
                            '-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR', f'-DCHILD={child}',
                            str(cfile), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=10)


if __name__ == '__main__':
    main()
