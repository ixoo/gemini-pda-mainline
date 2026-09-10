#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the C slot writer against injected byte I/O and the independent decoder."""
import ctypes
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('records', HERE / 'capture-records.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
CYCLE = bytes(range(16))
IDENTITY = bytes(range(80))

SHIM = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <setjmp.h>
typedef uint8_t u8;
typedef uint32_t u32;
#define __iomem
static u8 memory[65524];
static unsigned int reads, writes, barriers, cut, drop, fault_read;
static char trace[100000];
static unsigned int trace_length;
static jmp_buf interruption;
static void log_op(char op) { if (trace_length + 1 < sizeof(trace)) trace[trace_length++] = op; }
static u8 readb_relaxed(const u8 *p)
{
    reads++; log_op('R');
    return *p ^ (reads == fault_read ? 1 : 0);
}
static void writeb_relaxed(u8 value, u8 *p)
{
    writes++; log_op('W');
    if (writes != drop) *p = value;
    if (writes == cut) longjmp(interruption, 1);
}
static void mb(void) { barriers++; log_op('B'); }
static u32 get_unaligned_le32(const u8 *p)
{ return (u32)p[0] | (u32)p[1] << 8 | (u32)p[2] << 16 | (u32)p[3] << 24; }
static void put_unaligned_le16(unsigned int n, u8 *p)
{ p[0] = n; p[1] = n >> 8; }
static void put_unaligned_le32(u32 n, u8 *p)
{ for (unsigned int i = 0; i < 4; i++) p[i] = n >> (8 * i); }
static u32 crc32_le(u32 crc, const u8 *p, size_t n)
{
    while (n--) {
        crc ^= *p++;
        for (unsigned int i = 0; i < 8; i++)
            crc = (crc >> 1) ^ (0xedb88320U & (0U - (crc & 1)));
    }
    return crc;
}
'''

WRAPPER = r'''
static struct wfc_writer state;
void fresh(void) { memset(&state, 0, sizeof(state)); memset(memory, 0, sizeof(memory)); }
void inject(unsigned int stop, unsigned int lost, unsigned int bad_read)
{
    cut = stop; drop = lost; fault_read = bad_read;
    reads = writes = barriers = trace_length = 0;
}
int begin(const u8 *cycle, const u8 *identity, size_t length)
{
    if (setjmp(interruption)) return -999;
    return wfc_writer_begin(&state, memory, length, cycle, identity);
}
int append(unsigned int kind, u32 transaction, const u8 *payload, size_t length)
{
    if (setjmp(interruption)) return -999;
    return wfc_slot_write(&state, kind, transaction, payload, length);
}
u8 *data(void) { return memory; }
unsigned int store_count(void) { return writes; }
unsigned int load_count(void) { return reads; }
unsigned int next_slot(void) { return state.next; }
int stopped(void) { return state.stopped; }
char *operations(void) { trace[trace_length] = 0; return trace; }
'''


class WriterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='wfc-writer-')
        root = Path(cls.temp.name)
        # Keep every implementation byte except native include directives.
        source = (HERE / 'capture-slot-writer.h').read_text()
        source = '\n'.join(line for line in source.splitlines()
                           if not line.startswith('#include '))
        (root / 'test.c').write_text(SHIM + source + WRAPPER)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-fPIC', '-shared', str(root / 'test.c'),
                        '-o', str(root / 'test.so')], check=True)
        cls.c = ctypes.CDLL(str(root / 'test.so'))
        cls.c.begin.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t]
        cls.c.append.argtypes = [ctypes.c_uint, ctypes.c_uint32,
                                ctypes.c_char_p, ctypes.c_size_t]
        cls.c.data.restype = ctypes.POINTER(ctypes.c_ubyte)
        cls.c.operations.restype = ctypes.c_char_p

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.c.fresh()
        self.c.inject(0, 0, 0)

    def begin(self):
        self.assertEqual(self.c.begin(CYCLE, IDENTITY, r.ZONE_PAYLOAD_BYTES), 0)
        self.c.inject(0, 0, 0)

    def snapshot(self):
        return bytes(self.c.data()[:r.ZONE_PAYLOAD_BYTES])

    def event(self):
        return self.c.append(10, 0, b'event', 5)

    def terminal(self, status=1):
        return self.c.append(255, 0, status.to_bytes(4, 'little'), 4)

    def assert_closed(self):
        before = self.snapshot()
        count = self.c.store_count()
        self.assertTrue(self.c.stopped())
        self.assertLess(self.event(), 0)
        self.assertLess(self.terminal(), 0)
        self.assertLess(self.c.begin(CYCLE, IDENTITY, r.ZONE_PAYLOAD_BYTES), 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.c.store_count(), count)

    def test_bytes_match_independent_codec_and_order(self):
        self.begin()
        self.assertEqual(self.event(), 0)
        expected_order = (b'B' + b'R' * 128 + b'B' + b'W' * 124 + b'B' +
                          b'R' * 128 + b'B' + b'W' * 4 + b'B' + b'R' * 128 + b'B')
        self.assertEqual(self.c.operations(), expected_order)
        self.assertEqual(self.terminal(), 0)
        stream = (r.encode(1, 0, CYCLE, 0, IDENTITY) +
                  r.encode(10, 1, CYCLE, 0, b'event') +
                  r.encode(255, 2, CYCLE, 0, (1).to_bytes(4, 'little')))
        self.assertEqual(self.snapshot(), stream + bytes(r.ZONE_PAYLOAD_BYTES - len(stream)))
        self.assertEqual(r.decode_pmsg(self.snapshot(), CYCLE, IDENTITY)['framing'], 'terminal-recorded')
        self.assert_closed()

    def test_every_interruption_preserves_prefix_and_stops(self):
        for cut in range(1, 129):
            with self.subTest(cut=cut):
                self.setUp()
                self.begin()
                self.c.inject(cut, 0, 0)
                self.assertEqual(self.event(), -999)
                result = r.decode_pmsg(self.snapshot(), CYCLE, IDENTITY)
                self.assertEqual(result['framing'], 'incomplete')
                self.assertEqual(len(result['records']), 2 if cut == 128 else 1)
                self.assert_closed()

    def test_every_body_and_final_readback_fault_stops(self):
        for read in range(129, 385):
            with self.subTest(read=read):
                self.setUp()
                self.begin()
                self.c.inject(0, 0, read)
                self.assertEqual(self.event(), -5)  # EIO
                self.assertEqual(self.c.store_count(), 124 if read <= 256 else 128)
                self.assertEqual(self.c.load_count(), 256 if read <= 256 else 384)
                self.assert_closed()

    def test_lost_nonzero_store_is_detected_without_retry(self):
        record = r.encode(10, 1, CYCLE, 0, b'event')
        for offset, value in enumerate(record):
            if not value:
                continue  # Losing an already-zero store is byte-equivalent.
            with self.subTest(offset=offset):
                self.setUp()
                self.begin()
                self.c.inject(0, offset + 1, 0)
                self.assertEqual(self.event(), -5)
                self.assert_closed()

    def test_nonempty_admission_including_tail_never_writes(self):
        for offset in (0, 127, 128, 65407, 65408, 65523):
            self.setUp()
            self.c.data()[offset] = 1
            before = self.snapshot()
            self.assertEqual(self.c.begin(CYCLE, IDENTITY, r.ZONE_PAYLOAD_BYTES), -16)
            self.assertEqual(self.c.store_count(), 0)
            self.assertEqual(self.c.load_count(), r.ZONE_PAYLOAD_BYTES)
            self.assertEqual(self.snapshot(), before)
            self.assert_closed()

    def test_nonempty_target_is_preserved(self):
        for offset in range(128):
            self.setUp()
            self.begin()
            self.c.data()[128 + offset] = 1
            before = self.snapshot()
            self.assertEqual(self.event(), -16)
            self.assertEqual(self.c.store_count(), 0)
            self.assertEqual(self.snapshot(), before)
            self.assert_closed()

    def test_capacity_commits_overflow_terminal(self):
        self.begin()
        for _ in range(509):
            self.assertEqual(self.event(), 0)
        self.assertEqual(self.c.next_slot(), 510)
        self.assertEqual(self.event(), -28)  # ENOSPC after terminal readback.
        result = r.decode_pmsg(self.snapshot(), CYCLE, IDENTITY)
        self.assertEqual(len(result['records']), 511)
        self.assertEqual(result['producer_status'], 3)
        self.assert_closed()

    def test_recovery_prefix_roundtrip(self):
        self.begin()
        for values in ((1, 12, 0, 0, 0, 0, 0), (2, 12, 1, 0x48, 5, 24576, 0)):
            payload = r.RECOVERY.pack(*values)
            self.assertEqual(self.c.append(11, 0, payload, len(payload)), 0)
        result = r.decode_pmsg(self.snapshot(), CYCLE, IDENTITY)
        r.check_recovery_prefix(result['records'])
        self.assertEqual(result['framing'], 'incomplete')

    def test_invalid_arguments_close_without_stores(self):
        for args in ((1, 0, IDENTITY, 80), (14, 0, b'', 0),
                     (2, 0, bytes(85), 85), (2, 0, None, 1),
                     (255, 1, bytes([1, 0, 0, 0]), 4),
                     (255, 0, None, 4), (255, 0, bytes(4), 4)):
            self.setUp()
            self.begin()
            self.assertEqual(self.c.append(*args), -22)
            self.assertEqual(self.c.store_count(), 0)
            self.assert_closed()
        for cycle, identity, length in ((bytes(16), IDENTITY, 65524),
                                        (None, IDENTITY, 65524),
                                        (CYCLE, None, 65524),
                                        (CYCLE, IDENTITY, 65523)):
            self.setUp()
            self.assertEqual(self.c.begin(cycle, identity, length), -22)
            self.assertEqual(self.c.load_count(), 0)
            self.assertEqual(self.c.store_count(), 0)
            self.assert_closed()


if __name__ == '__main__':
    unittest.main()
