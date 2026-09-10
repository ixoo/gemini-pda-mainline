#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise extracted restart/takeover bodies with controlled claim orderings."""
import importlib.util
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
#include <stdatomic.h>
typedef atomic_int atomic_t;
#define ATOMIC_INIT(v) (v)
static _Thread_local jmp_buf terminal;
static _Thread_local bool irq_disabled, arming;
static _Thread_local unsigned int pause_at;
static unsigned int effects;
static bool parked;
static void cpu_relax(void) { assert(!held); parked = true; longjmp(terminal, 1); }
static void rendezvous(void)
{
    assert(!pthread_mutex_lock(&gate));
    reached = true;
    assert(!pthread_cond_broadcast(&changed));
    while (!proceed) assert(!pthread_cond_wait(&changed, &gate));
    assert(!pthread_mutex_unlock(&gate));
}
static int atomic_cmpxchg(atomic_t *value, int old, int next)
{
    if (arming) assert(irq_disabled && held);
    if (pause_at == 1) rendezvous();
    int seen = old;
    atomic_compare_exchange_strong(value, &seen, next);
    if (pause_at == 2) rendezvous();
    return seen;
}
#define spin_lock_irqsave(lock, flags) do { \
    (flags) = irq_disabled; irq_disabled = true; spin_lock(lock); \
} while (0)
#define spin_unlock_irqrestore(lock, flags) do { \
    spin_unlock(lock); irq_disabled = (flags); \
} while (0)
static void local_irq_disable(void) { effects++; }
static void smp_send_stop(void) { effects++; }
static int reboot_notifier_list, system_state, reboot_mode;
#define SYS_RESTART 1
#define SYSTEM_RESTART 2
#define KMSG_DUMP_EMERG 3
#define MTK_SIP_KERNEL_DISABLE_DFD 4
#define pr_emerg(...) do { } while (0)
#define printk(...) do { } while (0)
static void blocking_notifier_call_chain(int *list, int kind, char *cmd) { effects++; }
static void usermodehelper_disable(void) { effects++; }
static void device_shutdown(void) { effects++; }
static void kmsg_dump(int kind) { effects++; }
static void stop_after_callback(void) { effects++;longjmp(terminal, 1); }
static void restart_callback(int mode, const char *cmd) { stop_after_callback(); }
static void (*arm_pm_restart)(int, const char *) = restart_callback;
static void do_kernel_restart(char *cmd) { stop_after_callback(); }
static void machine_restart(char *cmd);
static void machine_emergency_restart(void) { machine_restart(NULL); }
static void mt_secure_call(int id, int a, int b, int c) { effects++; }
static void pmic_pre_wdt_reset(void) { assert(held);effects++; }
static void udelay(unsigned int usec) { assert(held && usec == 100); }
'''

CASES = r'''
static void fresh(void)
{
    assert(!held && !irq_disabled);
    memset(registers, 0, sizeof(registers));
    writes = effects = 0;
    parked = reached = proceed = mtk_wdt_recovery_owned = false;
    atomic_store(&mtk_wdt_transition, MTK_WDT_TRANSITION_IDLE);
}
static int arm(void)
{
    struct mtk_wdt_recovery_state state;
    arming = true;
    int result = mtk_wdt_recovery_arm(12, &state);
    arming = false;
    assert(!held && !irq_disabled);
    assert(state.owned == (result == 0 || result == -EALREADY));
    return result;
}
static void invoke(unsigned int entry)
{
    if (!setjmp(terminal)) {
        if (entry == 0) kernel_restart_prepare(NULL);
        else if (entry == 1) emergency_restart();
        else if (entry == 2) machine_restart(NULL);
        else wdt_arch_reset(1);
    }
    assert(!held && !irq_disabled);
}
static void wait_for_worker(void)
{
    assert(!pthread_mutex_lock(&gate));
    while (!reached) assert(!pthread_cond_wait(&changed, &gate));
    assert(!pthread_mutex_unlock(&gate));
}
static void release_worker(pthread_t thread)
{
    assert(!pthread_mutex_lock(&gate));
    proceed = true;
    assert(!pthread_cond_broadcast(&changed));
    assert(!pthread_mutex_unlock(&gate));
    assert(!pthread_join(thread, NULL));
}
static int worker_result;
static void *arming_worker(void *argument)
{
    pause_at = *(unsigned int *)argument;
    worker_result = arm();
    return NULL;
}
static void *restart_worker(void *argument)
{
    pause_at = 1;
    invoke(*(unsigned int *)argument);
    return NULL;
}
int main(void)
{
    for (unsigned int entry = 0; entry < 4; entry++) {
        fresh();
        assert(!arm() && writes == 3);
        invoke(entry);
        /* The parent already guards the low-level reset, but not preludes. */
        assert((effects == 0) == (CHILD || entry == 3));
        assert(!CHILD || (parked && writes == 3));
        assert(arm() == -EALREADY && writes == 3);
        fresh();
        invoke(entry);
        assert(effects > 0);
        unsigned int previous_writes = writes;
        assert(arm() == (CHILD ? -EBUSY : 0));
        assert(writes == previous_writes + (CHILD ? 0 : 3));
    }
    if (CHILD) {
        pthread_t thread;
        unsigned int pause = 1, entry = 0;
        /* Restart wins while takeover is waiting to claim. */
        fresh();
        assert(!pthread_create(&thread, NULL, arming_worker, &pause));
        wait_for_worker();
        invoke(0);
        release_worker(thread);
        assert(worker_result == -EBUSY && writes == 0 && effects == 3);
        /* Restart on another CPU cannot stop an in-flight arming CPU. */
        fresh();pause = 2;
        assert(!pthread_create(&thread, NULL, arming_worker, &pause));
        wait_for_worker();
        invoke(1);
        assert(parked && !effects && !writes);
        release_worker(thread);
        assert(!worker_result && writes == 3);
        /* Capture wins while an earlier restart invocation awaits its claim. */
        fresh();
        assert(!pthread_create(&thread, NULL, restart_worker, &entry));
        wait_for_worker();
        assert(!arm());
        release_worker(thread);
        assert(parked && !effects && writes == 3);
    }
    puts(CHILD ? "PASS: four restart entries, both orders and three claim races" :
                 "PASS: parent restart preludes reproduce the takeover race");
    return 0;
}
'''


def main():
    parent, child = map(Path, sys.argv[1:])
    changed_source = (child / setters.SOURCE).read_text()
    transition = re.search(r'enum \{\n\tMTK_WDT_TRANSITION_IDLE,.*?static atomic_t .*?;',
                           changed_source, re.S).group()
    header = (parent / 'drivers/watchdog/mediatek/wdt/mt6797/mt_wdt.h').read_text()
    state = re.search(r'struct mtk_wdt_recovery_state \{.*?\};',
                      (parent / setters.HEADER).read_text(), re.S).group()
    for changed, tree in enumerate((parent, child)):
        source = (tree / setters.SOURCE).read_text()
        guard = (setters.function(source, 'mtk_wdt_recovery_restart_guard') if changed
                 else 'static void mtk_wdt_recovery_restart_guard(void) { }')
        bodies = '\n'.join(setters.function(source, name) for name in
                           ('mtk_wdt_recovery_arm', 'wdt_arch_reset'))
        bodies += '\n' + setters.function((tree / 'arch/arm64/kernel/process.c').read_text(),
                                          'machine_restart').replace('void machine_restart',
                                                                     'static void machine_restart', 1)
        reboot = (tree / 'kernel/reboot.c').read_text()
        bodies += '\n' + '\n'.join(setters.function(reboot, name) for name in
                                   ('kernel_restart_prepare', 'emergency_restart'))
        with tempfile.TemporaryDirectory(prefix='wifi-restart-gate-') as tmp:
            cfile, binary = Path(tmp) / 'gate.c', Path(tmp) / 'gate'
            cfile.write_text(setters.SHIM + EXTRA + header + state + transition + guard + bodies + CASES)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pthread',
                            '-Wno-unused-function', '-Wno-unused-variable', '-Wno-unused-parameter',
                            '-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR', '-DCONFIG_MTK_PSCI',
                            f'-DCHILD={changed}', str(cfile), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=10)


if __name__ == '__main__':
    main()
