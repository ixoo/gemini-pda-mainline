#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the complete native subsystem-reset setter across takeover."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('setters', HERE / 'test-recovery-setters.py')
setters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setters)

CASES = r'''
static int operation_result;
static void invoke(unsigned int operation)
{
    operation_result = mtk_wdt_swsysret_config(MTK_WDT_SWSYS_RST_CONMCU_RST,
                                                operation == 0 ? 1 : 0);
    assert(!held);
}
static void *worker(void *argument)
{
    delayed_lock = true;
    invoke(*(unsigned int *)argument);
    return NULL;
}
int main(void)
{
    for (unsigned int operation = 0; operation < 2; operation++) {
        for (unsigned int ordering = 0; ordering < 3; ordering++) {
            pthread_t thread;
            unsigned int before = operation ? MTK_WDT_SWSYS_RST_CONMCU_RST : 0;
            memset(registers, 0, sizeof(registers));
            registers[0x18 / 4] = before;
            writes = reads = 0;
            mtk_wdt_recovery_owned = reached = proceed = false;
            if (ordering == 2) {
                assert(!pthread_create(&thread, NULL, worker, &operation));
                assert(!pthread_mutex_lock(&gate));
                while (!reached) assert(!pthread_cond_wait(&changed, &gate));
                assert(!pthread_mutex_unlock(&gate));
            }
            if (ordering) {
                spin_lock(&rgu_reg_operation_spinlock);
                mtk_wdt_recovery_owned = true;
                spin_unlock(&rgu_reg_operation_spinlock);
            }
            if (ordering == 2) {
                assert(!pthread_mutex_lock(&gate));
                proceed = true;
                assert(!pthread_cond_broadcast(&changed));
                assert(!pthread_mutex_unlock(&gate));
                assert(!pthread_join(thread, NULL));
            } else invoke(operation);
            bool refused = CHILD && EXPERIMENT && ordering;
            assert(operation_result == (refused ? -EBUSY : 0));
            assert(reads == (refused ? 0u : 1u));
            assert(writes == (refused ? 0u : 1u));
            assert(registers[0x18 / 4] ==
                   (refused ? before : MTK_WDT_SWSYS_RST_KEY |
                    (operation ? 0u : MTK_WDT_SWSYS_RST_CONMCU_RST)));
        }
    }
    printf("PASS: 6 subsystem-reset orderings child=%d experiment=%d\n",
           CHILD, EXPERIMENT);
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('child', type=Path)
    parser.add_argument('header', type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/recovery-subsystem-sources.json').read_text())
    assert hashlib.sha256(args.header.read_bytes()).hexdigest() == pins['header_sha256']
    assert hashlib.sha256((HERE / pins['patch']).read_bytes()).hexdigest() == pins['patch_sha256']
    shim = setters.SHIM.replace('static unsigned int timeout, writes;',
                                'static unsigned int writes, reads;').replace(
                                    'static int g_wdt_enable = 1;\n', '').replace(
                                        'return registers[(address - toprgu_base) / 4];',
                                        'reads++; return registers[(address - toprgu_base) / 4];')
    for child, root in enumerate((args.parent, args.child)):
        source = (root / pins['source_path']).read_bytes()
        assert hashlib.sha256(source).hexdigest() == pins['child_sha256' if child else 'parent_sha256']
        body = setters.function(source.decode(), 'mtk_wdt_swsysret_config')
        for experiment in (0, 1):
            with tempfile.TemporaryDirectory(prefix='wifi-recovery-subsystem-') as temporary:
                cfile = Path(temporary) / 'subsystem.c'
                binary = Path(temporary) / 'subsystem'
                cfile.write_text(shim + args.header.read_text() + body + CASES)
                command = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pthread',
                           f'-DCHILD={child}', f'-DEXPERIMENT={experiment}']
                if experiment:
                    command.append('-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR')
                subprocess.run(command + [str(cfile), '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True, timeout=10)


if __name__ == '__main__':
    main()
