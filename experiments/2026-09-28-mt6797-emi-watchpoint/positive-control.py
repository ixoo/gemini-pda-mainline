#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One-use non-blocking EMI watchpoint control on an owned RAM page."""
import ctypes
import mmap
import os
import signal
import struct
import subprocess
import sys

BOOT = '636e12fb-65de-4eb3-88c8-70c3e4cec71e'
OUTPUT = '/var/tmp/gemini-emi-wp-positive-20260928'
WP_ADR = 0x102035e0
WP_CTRL = 0x102035e8
CHKER = 0x102035f0
CHKER_TYPE = 0x102035f4
CHKER_ADR = 0x102035f8
BASELINE = 0x00800000
PATTERN = b'GEMINIWP'


def read32(address):
    value = subprocess.check_output(['/bin/busybox', 'devmem',
                                     hex(address), '32'])
    return int(value, 16)


def write32(address, value):
    with open(os.devnull, 'wb') as null:
        subprocess.check_call(['/bin/busybox', 'devmem', hex(address),
                               '32', hex(value)], stdout=null)


def snapshot(log, prefix):
    for name, address in [('wp_adr', WP_ADR), ('wp_ctrl', WP_CTRL),
                          ('chker', CHKER), ('type', CHKER_TYPE),
                          ('addr', CHKER_ADR)]:
        log.write('%s_%s=0x%08x\n' % (prefix, name, read32(address)))
    log.flush()


def own_page():
    size = os.sysconf('SC_PAGE_SIZE')
    if size != 4096:
        raise RuntimeError('unexpected page size')
    page = mmap.mmap(-1, size)
    page[:len(PATTERN)] = PATTERN
    address = ctypes.addressof(ctypes.c_char.from_buffer(page))
    libc = ctypes.CDLL(None)
    if libc.mlock(ctypes.c_void_p(address), ctypes.c_size_t(size)) != 0:
        raise RuntimeError('mlock failed')
    with open('/proc/self/pagemap', 'rb', buffering=0) as mapping:
        mapping.seek((address // size) * 8)
        entry = struct.unpack('<Q', mapping.read(8))[0]
    pfn = entry & ((1 << 55) - 1)
    physical = pfn * size
    if not (entry & (1 << 63)) or not pfn:
        raise RuntimeError('page frame unavailable')
    if not (0x40000000 <= physical < 0x140000000):
        raise RuntimeError('page outside 32-bit DRAM-offset range')
    return page, physical


def check_identity():
    if os.geteuid() != 0:
        raise RuntimeError('root required')
    with open('/proc/sys/kernel/random/boot_id') as f:
        if f.read().strip() != BOOT:
            raise RuntimeError('boot changed')
    if os.uname().release != '3.18.41+':
        raise RuntimeError('kernel changed')
    with open('/sys/class/net/wlan0/carrier') as f:
        if f.read().strip() != '1':
            raise RuntimeError('Wi-Fi carrier absent')
    with open('/sys/class/power_supply/battery/health') as f:
        if f.read().strip() != 'Good':
            raise RuntimeError('battery health changed')
    with open('/sys/class/power_supply/battery/capacity') as f:
        if int(f.read().strip()) < 40:
            raise RuntimeError('battery capacity too low')
    if (read32(WP_ADR), read32(WP_CTRL), read32(CHKER),
            read32(CHKER_TYPE), read32(CHKER_ADR)) != (0, 0, BASELINE, 0, 0):
        raise RuntimeError('watchpoint not idle')
    if os.path.lexists(OUTPUT):
        raise RuntimeError('one-use output exists')


def stop_on_signal(signum, frame):
    raise RuntimeError('interrupted by signal %d' % signum)


def main():
    os.umask(0o077)
    if len(sys.argv) not in (1, 2) or (len(sys.argv) == 2 and
                                   sys.argv[1] != '--preflight'):
        raise RuntimeError('usage: positive-control.py [--preflight]')
    check_identity()
    page, physical = own_page()
    fd = os.open('/dev/mem', os.O_RDONLY | os.O_SYNC)
    try:
        if os.pread(fd, len(PATTERN), physical) != PATTERN:
            raise RuntimeError('owned-page physical read mismatch')
        if len(sys.argv) == 2:
            print('preflight=pass boot=%s' % BOOT)
            return
        os.mkdir(OUTPUT, 0o700)
        for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, stop_on_signal)
        with open(os.path.join(OUTPUT, 'control.log'), 'w') as log:
            log.write('boot=%s\nphysical_page=0x%08x\n' % (BOOT, physical))
            snapshot(log, 'pre')
            modified = True
            status = 0
            try:
                # 16-byte aligned owned page, relative to DRAM offset.
                write32(WP_ADR, physical - 0x40000000)
                write32(WP_CTRL, 0x000000c4)  # R/W, range=4, no error/IRQ.
                if (read32(WP_ADR), read32(WP_CTRL), read32(CHKER)) != (
                        physical - 0x40000000, 0x000000c4, BASELINE):
                    raise RuntimeError('watchpoint setup readback mismatch')
                write32(CHKER, 0x00880000)
                log.write('armed_chker=0x%08x\n' % read32(CHKER))
                log.flush()
                for index in (1, 2):
                    data = os.pread(fd, len(PATTERN), physical)
                    log.write('read%d_match=%s\n' % (index, data == PATTERN))
                    snapshot(log, 'read%d' % index)
                    if data != PATTERN:
                        raise RuntimeError('owned-page read changed')
            except Exception as error:
                status = 1
                log.write('error=%s\n' % error)
            finally:
                if modified:
                    try:
                        write32(CHKER, BASELINE)
                        write32(WP_CTRL, 0)
                        write32(WP_ADR, 0)
                        write32(CHKER, 0x01800000)
                        snapshot(log, 'post')
                        if (read32(WP_ADR), read32(WP_CTRL), read32(CHKER),
                                read32(CHKER_TYPE), read32(CHKER_ADR)) != (
                                0, 0, BASELINE, 0, 0):
                            raise RuntimeError('watchpoint restoration mismatch')
                    except Exception as error:
                        status = 1
                        log.write('cleanup_error=%s\n' % error)
                log.write('exit_code=%d\n' % status)
                log.flush()
        if status:
            raise RuntimeError('control failed; inspect private log')
    finally:
        os.close(fd)
        page.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('error: %s' % error, file=sys.stderr)
        sys.exit(1)
