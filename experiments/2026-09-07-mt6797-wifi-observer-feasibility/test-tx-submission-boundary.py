#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise pinned native TX staging and AHB-selected macros with injected I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SHIM = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t UINT_8, *PUINT_8;
typedef uint16_t UINT_16;
typedef uint32_t UINT_32, *PUINT_32;
typedef void *PVOID;
typedef int WLAN_STATUS;
#define IN
#define ASSERT assert
#define WLAN_STATUS_SUCCESS 0
#define ACPI_STATE_D3 3
#define MCR_WTDR1 0x34
#define ALIGN_4(x) (((x) + 3U) & ~3U)
#define TFCB_FRAME_PAD_TO_DW ALIGN_4
#define HIF_TX_HDR_TX_BYTE_COUNT_MASK 0xffff
struct tx { PUINT_8 pucTxCoalescingBufPtr; };
typedef struct tx *P_TX_CTRL_T;
struct adapter { struct tx rTxCtrl; UINT_32 u4CoalescingBufCachedSize;
    int rAcpiState; void *prGlueInfo; };
typedef struct adapter *P_ADAPTER_T;
struct command { UINT_16 u2InfoBufLen; PUINT_8 pucInfoBuffer; };
typedef struct command *P_CMD_INFO_T;
static unsigned int calls, supplied, fault;
static uint8_t observed[4096];
static void injected_copy(void *dst, const void *src, size_t bytes)
{
    memcpy(dst, src, bytes);
    /* Deterministic corruption after staging, not a kernel scheduler. */
    if (fault == 2) ((uint8_t *)dst)[8] ^= 1;
}
#define kalMemCopy injected_copy
static int kalDevPortWrite(void *glue, UINT_16 port, UINT_32 bytes,
                           PUINT_8 buffer, UINT_32 capacity)
{
    assert(glue && port == MCR_WTDR1 && bytes <= capacity);
    calls++; supplied = bytes;
    memcpy(observed, buffer, bytes);
    return fault != 1;
}
'''
CASES = r'''
int main(void)
{
    union { uint32_t align; uint8_t bytes[4096]; } storage;
    uint8_t command[2056], original[2056];
    memset(command, 0x37, sizeof(command));
    memcpy(original, command, sizeof(command));
    struct adapter adapter = {{storage.bytes}, sizeof(storage.bytes), 0, &storage};
    struct command info = {sizeof(command), command};
    for (fault = 0; fault < 4; fault++) {
        memset(storage.bytes, 0xa5, sizeof(storage.bytes));
        calls = supplied = 0;
        info.u2InfoBufLen = fault == 3 ? 39 : sizeof(command);
        assert(nicTxInitCmd(&adapter, &info) == WLAN_STATUS_SUCCESS);
        assert(calls == 1 && supplied == ALIGN_4(info.u2InfoBufLen));
        assert(!memcmp(command, original, sizeof(command)));
        if (fault == 2)
            assert(observed[8] == (command[8] ^ 1));
        else
            assert(!memcmp(observed, command, info.u2InfoBufLen));
        if (fault == 3) assert(observed[39] == 0xa5);
        /* The macro clears one dword beyond the supplied aligned extent. */
        for (unsigned int n = 0; n < 4; n++)
            assert(storage.bytes[supplied + n] == 0);
        assert(storage.bytes[supplied + 4] == 0xa5);
    }
    puts("PASS: native staging, ignored port refusal, changed copy, stale alignment byte");
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', type=Path, help='directory with pinned nic_tx.c, hal.h and hif_tx.h')
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/capture-sizing.json').read_text())['sources']
    sources = {}
    for name in ('nic_tx.c', 'hal.h', 'hif_tx.h'):
        entry, = [item for item in pins if Path(item['path']).name == name]
        data = (args.sources / name).read_bytes()
        assert len(data) == entry['bytes']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        sources[name] = data.decode()
    assert re.search(r'#define HIF_TX_HDR_TX_BYTE_COUNT_MASK\s+BITS\(0, 15\)', sources['hif_tx.h'])
    assert re.search(r'#define TFCB_FRAME_PAD_TO_DW\(u2Length\)\s+ALIGN_4\(u2Length\)',
                     sources['hif_tx.h'])
    tx = sources['nic_tx.c']
    start = tx.index('WLAN_STATUS nicTxInitCmd(')
    function = tx[start:tx.index('\n}', start) + 2]
    macros = []
    for name in ('HAL_PORT_WR', 'HAL_WRITE_TX_PORT'):
        # Last HAL_PORT_WR is the non-SDIO definition selected by native AHB.
        matches = re.findall(r'^#define ' + name + r'\([^\n]*\n(?:[^\n]*\\\n)*[^\n]*',
                             sources['hal.h'], re.MULTILINE)
        assert len(matches) == (2 if name == 'HAL_PORT_WR' else 1)
        macros.append(matches[-1])
    with tempfile.TemporaryDirectory(prefix='wifi-tx-boundary-') as directory:
        root = Path(directory)
        cfile, binary = root / 'boundary.c', root / 'boundary'
        cfile.write_text(SHIM + '\n'.join(macros) + '\n' + function + CASES)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', str(cfile), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    main()
