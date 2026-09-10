#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute native initialization wrappers and controller with injected effects."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE = 'drivers/misc/mediatek/connectivity/common/common_detect/'
SHIM = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define _IOW(type, nr, size) (0x40000000U | (sizeof(size) << 16) | ((type) << 8) | (nr))
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint32_t __le32;
#define cpu_to_le32(x) ((uint32_t)(x))
#define __user
#define CAP_SYS_ADMIN 21
#define WMT_DETECT_INFO_FUNC(...) do { } while (0)
#define WMT_DETECT_DBG_FUNC(...) do { } while (0)
#define WMT_DETECT_ERR_FUNC(...) do { } while (0)
struct file { int unused; };
struct mtk_wdt_recovery_state { unsigned int owned, mode_before, mode_after, length_after; };
static int allowed, copy_fault, gate_error, gate_calls, attempted;
static int native_calls, native_fault, native_result, append_calls, append_fault;
static int active, terminal_calls, count, sites[10];
static u32 records[26][3];
static int capable(int cap) { assert(cap == CAP_SYS_ADMIN); return allowed; }
static int copy_from_user(void *dst, const void *src, size_t size)
{ if (copy_fault) return 1; memcpy(dst, src, size); return 0; }
static int mtk_wdt_capture_begin(const u8 *cycle, const u8 *identity,
                                 struct mtk_wdt_recovery_state *state)
{
    assert(cycle[0] && identity[0]); (void)state; gate_calls++;
    if (attempted++) return -EALREADY;
    active = !gate_error; return gate_error;
}
static int ramoops_capture_append(unsigned int kind, u32 tx, const u8 *data, size_t size)
{
    assert(!tx);
    if (kind == 255) {
        assert(size == 4 && *(const u32 *)data == 2); terminal_calls++; active = 0; return 0;
    }
    assert(kind == 12 && size == 12);
    if (!active) return -EPERM;
    if (++append_calls == append_fault) { active = 0; return -ENOSPC; }
    assert(count < 26); memcpy(records[count++], data, size); return 0;
}
static void mtk_wcn_wmt_set_chipid(int chip)
{ assert(chip == 0x6797 && active && gate_calls == 1 && count == 1); }
static void wmt_detect_set_chip_type(int chip)
{ assert(chip == 0x6797 && active && count == 2); }
static int native(int site)
{
    assert(active && count && records[count - 1][0] == (u32)site);
    assert(records[count - 1][1] == 1 && native_calls < 10);
    sites[native_calls++] = site;
    return native_calls == native_fault ? native_result : 0;
}
static int mtk_wcn_hif_sdio_drv_init(void) { return native(11); }
static int mtk_wcn_common_drv_init(void) { return native(12); }
static int mtk_wcn_stp_uart_drv_init(void) { return native(13); }
static int mtk_wcn_stp_sdio_drv_init(void) { return native(14); }
static int do_bluetooth_drv_init(int chip) { assert(chip == 0x6797); return native(2); }
static int do_gps_drv_init(int chip) { assert(chip == 0x6797); return native(3); }
static int do_fm_drv_init(int chip) { assert(chip == 0x6797); return native(4); }
static int mtk_wcn_wmt_wifi_init(void) { return native(21); }
static int mtk_wcn_wlan_gen3_init(void) { return native(22); }
static int do_ant_drv_init(int chip) { assert(chip == 0x6797); return native(6); }
'''
CASES = r'''
static void reset(void)
{
    allowed = 1; copy_fault = gate_error = gate_calls = attempted = 0;
    native_calls = native_fault = append_calls = append_fault = 0;
    active = terminal_calls = count = 0; native_result = -EIO;
    memset(records, 0, sizeof(records));
}
int main(int argc, char **argv)
{
    struct wmt_capture_identity input = {{1}, {1}};
    struct file file = {0};
    unsigned long arg = (unsigned long)&input;
    const int expected[] = {11, 12, 13, 14, 2, 3, 4, 21, 22, 6};
    assert(argc == 2 && sizeof(input) == 96 && COMBO_IOCTL_CAPTURE_INIT == 0x40607709);
    reset();
    assert(!wmt_detect_unlocked_ioctl(&file, COMBO_IOCTL_CAPTURE_INIT, arg));
    assert(native_calls == 10 && count == 26 && active && !terminal_calls);
    assert(!memcmp(sites, expected, sizeof(expected)));
    FILE *stream = fopen(argv[1], "wb"); assert(stream);
    assert(fwrite(records, sizeof(records), 1, stream) == 1 && !fclose(stream));
    assert(wmt_detect_unlocked_ioctl(&file, COMBO_IOCTL_CAPTURE_INIT, arg) == -EALREADY);
    assert(native_calls == 10 && count == 26);
    for (int fault = 1; fault <= 10; fault++) {
        for (int positive = 0; positive < 2; positive++) {
            reset(); native_fault = fault; native_result = positive ? 7 : -EIO;
            assert(wmt_detect_unlocked_ioctl(&file, COMBO_IOCTL_CAPTURE_INIT, arg) == -EIO);
            assert(native_calls == fault && terminal_calls == 1 && !active);
            assert(!memcmp(sites, expected, fault * sizeof(int)));
        }
    }
    for (int fault = 1; fault <= 26; fault++) {
        reset(); append_fault = fault;
        assert(wmt_detect_unlocked_ioctl(&file, COMBO_IOCTL_CAPTURE_INIT, arg) < 0);
        assert(count == fault - 1 && terminal_calls == 1 && !active);
    }
    for (int fault = 0; fault < 4; fault++) {
        reset();
        if (fault == 0) allowed = 0;
        if (fault == 1) copy_fault = 1;
        if (fault == 2) gate_error = -EIO;
        unsigned int cmd = fault == 3 ? 0x80047704 : COMBO_IOCTL_CAPTURE_INIT;
        assert(wmt_detect_unlocked_ioctl(&file, cmd, arg) < 0);
        assert(!native_calls && !count && !terminal_calls);
        assert(gate_calls == (fault == 2 ? 1 : 0));
    }
    puts("PASS: native startup, 20 initializer failures, 26 lost records, 4 preflight refusals, duplicate refusal");
}
'''


def function(source, name):
    match = re.search(r'^(?:static long|int) ' + name + r'\(', source, re.M)
    assert match, name
    return source[match.start():source.index('\n}', match.end()) + 2] + '\n'


def main():
    tree = Path(sys.argv[1])
    pins = json.loads((HERE / 'results/controller-init-sources.json').read_text())
    for path, expected in pins['outputs'].items():
        assert hashlib.sha256((tree / path).read_bytes()).hexdigest() == expected
    header = (tree / BASE / 'wmt_capture_init.h').read_text()
    header = re.sub(r'^#include .+\n', '', header, flags=re.M)
    identity = re.search(r'struct wmt_capture_identity \{.*?\};',
                         (tree / BASE / 'wmt_detect.h').read_text(), re.S).group()
    identity += "\n#define COMBO_IOCTL_CAPTURE_INIT _IOW('w', 9, struct wmt_capture_identity)\n"
    bodies = ''
    for path, name in [('drv_init/common_drv_init.c', 'do_common_drv_init'),
                       ('drv_init/wlan_drv_init.c', 'do_wlan_drv_init'),
                       ('drv_init/conn_drv_init.c', 'do_connectivity_driver_init'),
                       ('wmt_detect.c', 'wmt_capture_initialize'),
                       ('wmt_detect.c', 'wmt_detect_unlocked_ioctl')]:
        bodies += function((tree / BASE / path).read_text(), name)
    with tempfile.TemporaryDirectory(prefix='wifi-controller-init-') as directory:
        root = Path(directory)
        cfile, binary, output = root / 'init.c', root / 'init', root / 'records'
        cfile.write_text(SHIM + header + identity + bodies + CASES)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                        '-DCONFIG_MTK_A72_RECOVERY_DISCRIMINATOR', '-DMTK_WCN_REMOVE_KO=1',
                        '-DCONFIG_MTK_COMBO_WIFI', '-DMTK_WCN_WLAN_GEN3', str(cfile), '-o', str(binary)], check=True)
        subprocess.run([str(binary), str(output)], check=True, timeout=10)
        spec = importlib.util.spec_from_file_location('records', HERE / 'capture-records.py')
        r = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(r)
        cycle = bytes(range(16))
        stream = r.encode(1, 0, cycle, 0, bytes(range(80)))
        stream += r.encode(11, 1, cycle, 0, r.RECOVERY.pack(1, 12, 0, 0, 0, 0, 0))
        stream += r.encode(11, 2, cycle, 0, r.RECOVERY.pack(2, 12, 1, 0, 5, 24576, 0))
        raw = output.read_bytes()
        assert len(raw) == 26 * 12
        for i in range(26):
            stream += r.encode(12, i + 3, cycle, 0, raw[i * 12:(i + 1) * 12])
        records = r.decode(stream, cycle)
        r.check_startup_prefix(records)
        for i in range(3, 29):
            for mutation in (records[:i] + records[i + 1:], records[:i] + [records[i]] + records[i:]):
                try:
                    r.check_startup_prefix(mutation)
                except ValueError:
                    continue
                raise AssertionError('accepted lost/repeated initialization record')
        print('PASS: actual native record bytes decode; 52 missing/repeated-event refusals')


if __name__ == '__main__':
    main()
