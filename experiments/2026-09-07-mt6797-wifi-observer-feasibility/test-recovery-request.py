#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute both native request-route setters across capture takeover."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('setters', HERE / 'test-recovery-setters.py')
setters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setters)
SOURCE = setters.SOURCE

EXTRA = r'''
#define pr_err(...) do { } while (0)
struct device_node { const char *compatible; };
static struct device_node rgu_of_match[] = {{ "mediatek,mt6797-wdt" }};
static int ext_debugkey_io = 1, ext_debugkey_io_eint = -1;
static struct device_node *of_find_compatible_node(void *a, void *b, const char *c)
{
    (void)a; (void)b; (void)c;
    return &rgu_of_match[0];
}
static uint8_t *of_iomap(struct device_node *node, int index)
{
    assert(node == &rgu_of_match[0] && index == 0);
    return toprgu_base;
}
static int mt_gpio_to_eint(int gpio) { return gpio + 5; }
'''

CASES = r'''
static int operation_result;
static void invoke(unsigned int operation)
{
    if (operation == 0)
        operation_result = mtk_wdt_request_en_set(MTK_WDT_REQ_MODE_SPM_SCPSYS, WD_REQ_EN);
    else if (operation == 1)
        operation_result = mtk_wdt_request_mode_set(MTK_WDT_REQ_MODE_SPM_SCPSYS, WD_REQ_RST_MODE);
    else
        operation_result = mtk_wdt_request_en_set(MTK_WDT_REQ_MODE_EINT, WD_REQ_EN);
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
    for (unsigned int operation = 0; operation < 3; operation++) {
        for (unsigned int ordering = 0; ordering < 3; ordering++) {
            uint32_t snapshot[512];
            pthread_t thread;
            memset(registers, 0, sizeof(registers));
            writes = 0;
            ext_debugkey_io_eint = -1;
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
            memcpy(snapshot, registers, sizeof(snapshot));
            if (ordering == 2) {
                assert(!pthread_mutex_lock(&gate));
                proceed = true;
                assert(!pthread_cond_broadcast(&changed));
                assert(!pthread_mutex_unlock(&gate));
                assert(!pthread_join(thread, NULL));
            } else invoke(operation);
            bool refused = CHILD && EXPERIMENT && ordering;
            assert((writes == 0) == refused);
            assert(operation_result == (refused ? -EBUSY : 0));
            if (refused) {
                assert(!memcmp(snapshot, registers, sizeof(snapshot)));
                assert(ext_debugkey_io_eint == -1);
            } else {
                assert(writes == (operation == 2 ? 2u : 1u));
                assert(ext_debugkey_io_eint == (operation == 2 ? 6 : -1));
            }
        }
    }
    printf("PASS: 9 request-route orderings child=%d experiment=%d\n",
           CHILD, EXPERIMENT);
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('child', type=Path)
    parser.add_argument('support', type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/recovery-request-sources.json').read_text())
    for name, digest in pins['support'].items():
        assert hashlib.sha256((args.support / name).read_bytes()).hexdigest() == digest
    api = (args.support / 'wd_api.h').read_text()
    enums = '\n'.join(re.findall(r'typedef enum wk_req_(?:en|mode) \{.*?\} WD_REQ_(?:CTL|MODE);', api, re.S))
    assert enums.count('typedef enum') == 2
    for child, root in enumerate((args.parent, args.child)):
        source = (root / SOURCE).read_bytes()
        assert hashlib.sha256(source).hexdigest() == pins['child_sha256' if child else 'parent_sha256']
        bodies = '\n'.join(setters.function(source.decode(), name) for name in
                           ('mtk_wdt_request_en_set', 'mtk_wdt_request_mode_set'))
        for experiment in (0, 1):
            with tempfile.TemporaryDirectory(prefix='wifi-recovery-request-') as temporary:
                cfile = Path(temporary) / 'request.c'
                binary = Path(temporary) / 'request'
                shim = setters.SHIM.replace('static unsigned int timeout, writes;',
                                            'static unsigned int writes;').replace(
                                                'static int g_wdt_enable = 1;\n', '')
                cfile.write_text(shim + (args.support / 'mt_wdt.h').read_text() +
                                 enums + EXTRA + bodies + CASES)
                command = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pthread',
                           f'-DCHILD={child}', f'-DEXPERIMENT={experiment}']
                if experiment:
                    command.append('-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR')
                subprocess.run(command + [str(cfile), '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True, timeout=10)


if __name__ == '__main__':
    main()
