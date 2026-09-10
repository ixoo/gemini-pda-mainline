#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run native reset/reload bodies against injected takeover and lock contention."""
import importlib.util
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('setters', HERE / 'test-recovery-setters.py')
setters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setters)

EXTRA = r'''
#include <setjmp.h>
static _Thread_local jmp_buf terminal;
static _Thread_local bool delayed_read;
static unsigned int secure_calls, pmic_calls;
#define MTK_SIP_KERNEL_DISABLE_DFD 1
static void rendezvous(void)
{
    assert(!pthread_mutex_lock(&gate));
    reached = true;
    assert(!pthread_cond_broadcast(&changed));
    while (!proceed) assert(!pthread_cond_wait(&changed, &gate));
    assert(!pthread_mutex_unlock(&gate));
}
static bool read_once(bool value)
{
    if (delayed_read) rendezvous();
    return value;
}
#undef READ_ONCE
#define READ_ONCE(value) read_once(value)
static int spin_trylock(pthread_mutex_t *lock)
{
    int result = pthread_mutex_trylock(lock);
    assert(result == 0 || result == EBUSY);
    if (!result) held = true;
    return !result;
}
static void mt_secure_call(int id, int a, int b, int c)
{
    assert(id == 1 && !a && !b && !c);
    assert(!CHILD || held);
    secure_calls++;
}
static void pmic_pre_wdt_reset(void) { assert(held);pmic_calls++; }
static void udelay(unsigned int usec) { assert(held && usec == 100); }
static void cpu_relax(void) { assert(!held);longjmp(terminal, 1); }
'''
CASES = r'''
static void invoke(unsigned int operation)
{
    if (!setjmp(terminal)) {
        if (operation) wdt_arch_reset(1);
        else mtk_wdt_restart(WD_TYPE_NOLOCK);
        assert(!operation); /* A refused reset must park, never return. */
    }
    assert(!held);
}
static void arm(void)
{
    struct mtk_wdt_recovery_state state;
    assert(!mtk_wdt_recovery_arm(12, &state));
    assert(state.owned && !held);
}
static void *worker(void *argument)
{
    unsigned int operation = *(unsigned int *)argument;
    delayed_read = !operation;
    delayed_lock = !!operation;
    invoke(operation);
    return NULL;
}
int main(void)
{
    for (unsigned int operation = 0; operation < 2; operation++) {
        for (unsigned int ordering = 0; ordering < 3; ordering++) {
            uint32_t snapshot[512];
            pthread_t thread;
            memset(registers, 0, sizeof(registers));
            writes = secure_calls = pmic_calls = 0;
            mtk_wdt_recovery_owned = reached = proceed = false;
            if (ordering == 2) {
                assert(!pthread_create(&thread, NULL, worker, &operation));
                assert(!pthread_mutex_lock(&gate));
                while (!reached) assert(!pthread_cond_wait(&changed, &gate));
                assert(!pthread_mutex_unlock(&gate));
            }
            if (ordering) arm();
            /* Distinguish a repeated key store from the arm's identical value. */
            registers[(MTK_WDT_RESTART - toprgu_base) / 4] = 0;
            memcpy(snapshot, registers, sizeof(snapshot));
            if (ordering == 2) {
                assert(!pthread_mutex_lock(&gate));
                proceed = true;
                assert(!pthread_cond_broadcast(&changed));
                assert(!pthread_mutex_unlock(&gate));
                assert(!pthread_join(thread, NULL));
            } else invoke(operation);
            bool refused = ordering && (CHILD || (!operation && ordering == 1));
            assert((memcmp(snapshot, registers, sizeof(snapshot)) == 0) == refused);
            assert(secure_calls == (operation && !refused));
            assert(pmic_calls == (operation && !refused));
        }
    }
    /* A no-lock caller must not block when the register lock is already held. */
    mtk_wdt_recovery_owned = false;
    registers[(MTK_WDT_RESTART - toprgu_base) / 4] = 0;
    assert(!pthread_mutex_lock(&rgu_reg_operation_spinlock));
    invoke(0);
    assert(!pthread_mutex_unlock(&rgu_reg_operation_spinlock));
    assert((registers[(MTK_WDT_RESTART - toprgu_base) / 4] == 0) == CHILD);
    puts(CHILD ? "PASS: guarded reset/reload orderings and contention" :
                 "PASS: parent reset/reload races reproduced");
    return 0;
}
'''


def main():
    parent, child, support = map(Path, sys.argv[1:])
    api = (support / 'wd_api.h').read_text()
    assert hashlib.sha256(api.encode()).hexdigest() == 'da711e704f392a52ad05f8b43f93bf1be7f0f35e3263591bad6910899a201a09'
    header = (support / 'mt_wdt.h').read_text()
    assert hashlib.sha256(header.encode()).hexdigest() == 'fdbd42a1e238cc5148486a0d765434bddf008808244ad76af77d9371a208fa30'
    enums = '\n'.join(re.findall(r'typedef enum (?:wk_wdt_en|wd_restart_type) \{.*?\} \w+;', api, re.S))
    state = 'struct mtk_wdt_recovery_state { unsigned int owned, mode_before, mode_after, length_after; };'
    for changed, tree in enumerate((parent, child)):
        source = (tree / setters.SOURCE).read_text()
        bodies = '\n'.join(setters.function(source, name) for name in (
            'mtk_wdt_recovery_arm', 'mtk_wdt_restart', 'wdt_arch_reset'))
        with tempfile.TemporaryDirectory(prefix='recovery-reset-') as tmp:
            cfile, binary = Path(tmp) / 'reset.c', Path(tmp) / 'reset'
            cfile.write_text(setters.SHIM + EXTRA + header + enums + state + bodies + CASES)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                            '-Wno-unused-variable', '-Wno-unused-parameter', '-pthread',
                            '-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR', '-DCONFIG_MTK_PSCI',
                            f'-DCHILD={changed}', str(cfile), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=10)


if __name__ == '__main__':
    main()
