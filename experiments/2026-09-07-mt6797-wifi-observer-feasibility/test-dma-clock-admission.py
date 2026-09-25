#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the selected native clock callback and check its port refusal sites."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('capture_fixture', HERE / 'test-capture-integration.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def main():
    assert len(sys.argv) == 2, 'usage: test-dma-clock-admission.py PREPARED_SOURCE'
    source = Path(sys.argv[1])
    receipt = json.loads((HERE / 'results/dma-clock-admission-sources.json').read_text())
    files = {}
    for path, expected in receipt['output_sha256'].items():
        data = (source / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected, path
        files[Path(path).name] = data.decode()

    ahb = files['ahb.c']
    for name, failure_return in (('kalDevPortRead', 'return FALSE;'),
                                 ('kalDevPortWriteCapture', 'return wfc_fw_tx_port_return(tx, FALSE);')):
        body = fixture.function(ahb, name)
        marker = 'if (!pfWlanDmaOps || !pfWlanDmaOps->DmaClockCtrl(TRUE)) {'
        assert body.count(marker) == 1, name
        start = body.index(marker)
        end = body.index('#else', start)
        failure = body[start:end]
        assert failure.index('WlanDmaFatalErr = 1;') < failure.index('wfc_dma_abort();')
        assert failure.index('wfc_dma_abort();') < failure.index(failure_return)
        assert end < body.index('my_sdio_disable(HifLock)', end)
        assert end < body.index('writel(info.word', end)

    pdma = files['ahb_pdma.c']
    match = re.search(r'#ifdef CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR\n'
                      r'static BOOLEAN HifPdmaClockCtrl\([^;]+?\)\n#else\n'
                      r'static VOID HifPdmaClockCtrl\([^;]+?\)\n#endif\n\{', pdma)
    assert match, 'native callback definition'
    callback = pdma[match.start():pdma.index('\n}\n', match.end()) + 2]
    shim = r'''
#include <assert.h>
typedef int BOOLEAN;
typedef unsigned int UINT_32;
#define IN
#define TRUE 1
#define FALSE 0
#define CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR 1
#define DBGLOG(...) ((void)0)
static int expected, enables, disables;
static void *g_clk_wifi_pdma = (void *)1;
static int clk_prepare_enable(void *clk) {
    assert(clk == g_clk_wifi_pdma);
    enables++;
    return expected;
}
static void clk_disable_unprepare(void *clk) {
    assert(clk == g_clk_wifi_pdma);
    disables++;
}
'''
    checks = r'''
int main(void) {
    expected = -5;
    assert(HifPdmaClockCtrl(TRUE) == FALSE);
    assert(enables == 1 && disables == 0);
    expected = 0;
    assert(HifPdmaClockCtrl(TRUE) == TRUE);
    assert(enables == 2 && disables == 0);
    assert(HifPdmaClockCtrl(FALSE) == TRUE);
    assert(enables == 2 && disables == 1);
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='wifi-dma-clock-admission-') as tmp:
        src = Path(tmp) / 'test.c'
        binary = Path(tmp) / 'test'
        src.write_text(shim + callback + checks)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        str(src), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=10)
    print('native_clock_failure_and_port_order=pass; device_execution=none')


if __name__ == '__main__':
    main()
