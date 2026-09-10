#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise native capture acquisition and owner functions with injected I/O."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('slot_tests', HERE / 'test-capture-writer.py')
slot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slot)
r, CYCLE, IDENTITY = slot.r, slot.CYCLE, slot.IDENTITY
SOURCE = None


def function(text, name):
    match = re.search(r'^[^\n;]*\b' + re.escape(name) + r'\([^;]*?\)\n\{', text, re.M)
    assert match, name
    start = text.index('{', match.start())
    depth = 1
    end = start + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end] + '\n'


STUBS = r'''
#include <stdlib.h>
#include <assert.h>
#include <pthread.h>
typedef uint64_t phys_addr_t;
#define CONFIG_ARM64 1
#define CONFIG_HAVE_ARCH_PFN_VALID 1
#define IS_ENABLED(x) (x)
#define PAGE_SHIFT 12
#define PAGE_SIZE 4096
#define IS_ALIGNED(x, a) (!((x) & ((a) - 1)))
#define BUILD_BUG_ON(x) _Static_assert(!(x), "layout")
#define PERSISTENT_RAM_CAPTURE_ADDRESS 0x444e0000ULL
#define PERSISTENT_RAM_CAPTURE_SIZE 65536U
#define PERSISTENT_RAM_CAPTURE_HEADER_SIZE 12U
#define GFP_KERNEL 0
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define IS_ERR_OR_NULL(p) (!(p) || IS_ERR(p))
#define READ_ONCE(x) __atomic_load_n(&(x), __ATOMIC_SEQ_CST)
#define dev_err(...) ((void)0)
struct device { int unused; };
struct persistent_ram_buffer { u32 sig, start, size; u8 data[0]; };
struct persistent_ram_ecc_info { int block_size, ecc_size, symsize, poly; };
struct persistent_ram_zone {
    phys_addr_t paddr;
    size_t size;
    void *vaddr;
    struct persistent_ram_buffer *buffer;
    size_t buffer_size;
    char *par_buffer, *par_header;
    void *rs_decoder;
    struct persistent_ram_ecc_info ecc_info;
    char *old_log;
    size_t old_log_size;
};
static unsigned int allocations, live_allocations, fail_allocation;
static unsigned int requests, releases, mappings, unmaps, valid_page, pfn_checks;
static unsigned int fail_request, fail_mapping, reservation, zaps, normal_calls;
static unsigned int interrupt_context, nmi_context;
static void *kmalloc(size_t n, int flags)
{
    (void)flags;
    if (++allocations == fail_allocation) return NULL;
    void *p = malloc(n); assert(p); live_allocations++; return p;
}
static void *kzalloc(size_t n, int flags)
{ void *p = kmalloc(n, flags); if (p) memset(p, 0, n); return p; }
static void kfree(void *p)
{ if (p) { assert(live_allocations); live_allocations--; free(p); } }
static int pfn_valid(phys_addr_t pfn)
{
    pfn_checks++;
    return valid_page && pfn == (PERSISTENT_RAM_CAPTURE_ADDRESS >> PAGE_SHIFT) + valid_page - 1;
}
static void *request_mem_region(phys_addr_t p, size_t n, const char *name)
{
    assert(p == PERSISTENT_RAM_CAPTURE_ADDRESS && n == 65536 && name);
    requests++;
    if (fail_request) return NULL;
    assert(!reservation); reservation = 1; return memory;
}
static void release_mem_region(phys_addr_t p, size_t n)
{ assert(p == PERSISTENT_RAM_CAPTURE_ADDRESS && n == 65536 && reservation); releases++; reservation = 0; }
static void *ioremap_wc(phys_addr_t p, size_t n)
{ assert(p == PERSISTENT_RAM_CAPTURE_ADDRESS && n == 65536); mappings++; return fail_mapping ? NULL : memory; }
static void iounmap(void *p) { assert(p == memory); unmaps++; }
static void vunmap(void *p) { (void)p; assert(0); }
static void persistent_ram_free_old(struct persistent_ram_zone *p)
{ kfree(p->old_log); p->old_log = NULL; p->old_log_size = 0; }
static void persistent_ram_zap(struct persistent_ram_zone *p) { assert(p); zaps++; }
static struct persistent_ram_zone *persistent_ram_new(phys_addr_t a, size_t n,
                    u32 sig, struct persistent_ram_ecc_info *ecc, unsigned int mode)
{ (void)a; (void)n; (void)sig; (void)ecc; (void)mode; normal_calls++; return kzalloc(sizeof(struct persistent_ram_zone), 0); }
struct ramoops_context {
    phys_addr_t phys_addr;
    size_t size;
    unsigned int memtype;
    struct persistent_ram_ecc_info ecc_info;
    struct persistent_ram_zone *mprz;
    struct persistent_ram_zone **przs;
    unsigned int max_dump_cnt;
};
static struct ramoops_context oops_cxt;
static bool pmsg_capture, pmsg_capture_locked;
static bool pmsg_capture_registered, pmsg_capture_attempted;
static u8 *pmsg_capture_tail;
static bool test_and_set_bit(unsigned int bit, unsigned long *value)
{ assert(bit < 2); return !!(__atomic_fetch_or(value, 1UL << bit, __ATOMIC_SEQ_CST) & (1UL << bit)); }
static pthread_mutex_t pmsg_capture_lock = PTHREAD_MUTEX_INITIALIZER;
#define raw_spin_lock_irqsave(p, flags) do { (flags) = 0; assert(!pthread_mutex_lock(p)); } while (0)
#define raw_spin_unlock_irqrestore(p, flags) do { (void)(flags); assert(!pthread_mutex_unlock(p)); } while (0)
static bool in_interrupt(void) { return interrupt_context; }
static bool in_nmi(void) { return nmi_context; }
'''

WRAPPER = r'''
void fresh(void)
{
    if (oops_cxt.mprz && !IS_ERR(oops_cxt.mprz)) persistent_ram_free(oops_cxt.mprz);
    memset(&oops_cxt, 0, sizeof(oops_cxt));
    memset(&pmsg_writer, 0, sizeof(pmsg_writer));
    assert(!live_allocations && !reservation);
    memset(memory, 0, sizeof(memory));
    allocations = fail_allocation = requests = releases = mappings = unmaps = 0;
    valid_page = pfn_checks = fail_request = fail_mapping = zaps = normal_calls = 0;
    pmsg_capture = pmsg_capture_locked = true;
    pmsg_capture_registered = pmsg_capture_attempted = false;
    pmsg_capture_tail = NULL;
    pmsg_capture_denials = interrupt_context = nmi_context = 0;
    reads = writes = barriers = trace_length = cut = drop = fault_read = interference_read = 0;
    oops_cxt.phys_addr = 0x44410000;
    oops_cxt.size = 0xe0000;
}
void inject(unsigned int stop, unsigned int lost, unsigned int bad_read, unsigned int denial)
{
    cut = stop; drop = lost; fault_read = bad_read; interference_read = denial;
    reads = writes = barriers = trace_length = 0;
}
void map_faults(unsigned int alloc, unsigned int request, unsigned int mapping, unsigned int page)
{ fail_allocation = alloc; fail_request = request; fail_mapping = mapping; valid_page = page; }
int open_zone(uint64_t address, size_t length)
{
    struct device dev;
    phys_addr_t cursor = address;
    int ret = ramoops_init_prz(&dev, &oops_cxt, &oops_cxt.mprz, &cursor, length, 0);
    if (!ret) { assert(cursor == address + length); pmsg_capture_registered = true; }
    else assert(cursor == address);
    return ret;
}
int begin(const u8 *cycle, const u8 *identity)
{
    return ramoops_capture_begin(cycle, identity);
}
int append(unsigned int kind, u32 transaction, const u8 *payload, size_t length)
{
    return ramoops_capture_append(kind, transaction, payload, length);
}
int interrupted_begin(const u8 *cycle, const u8 *identity)
{
    if (setjmp(interruption)) { pthread_mutex_unlock(&pmsg_capture_lock); return -999; }
    return ramoops_capture_begin(cycle, identity);
}
u8 *data(void) { return memory; }
u8 *old_data(void) { return (u8 *)oops_cxt.mprz->old_log; }
unsigned int store_count(void) { return writes; }
unsigned int load_count(void) { return reads; }
unsigned int live_count(void) { return live_allocations; }
unsigned int reservation_count(void) { return reservation; }
unsigned int map_count(void) { return mappings; }
unsigned int zap_count(void) { return zaps; }
int deny(unsigned int bit) { return ramoops_capture_deny(bit); }
char *operations(void) { trace[trace_length] = 0; return trace; }
void denied(void) { __atomic_fetch_or(&pmsg_capture_denials, 1UL, __ATOMIC_SEQ_CST); }
void corrupt_contract(void) { oops_cxt.mprz->ecc_info.ecc_size = 1; }
void contexts(unsigned int irq, unsigned int nmi) { interrupt_context = irq; nmi_context = nmi; }
void check_dump_cleanup(void)
{
    struct ramoops_context c = { 0 };
    /* The third pointer is a live guard outside the logical two-entry array. */
    c.przs = kmalloc(3 * sizeof(*c.przs), 0);
    for (unsigned int i = 0; i < 3; i++) c.przs[i] = kzalloc(sizeof(**c.przs), 0);
    struct persistent_ram_zone *guard = c.przs[2];
    unsigned int before = live_allocations;
    c.max_dump_cnt = 2;
    ramoops_free_przs(&c);
    assert(!c.przs && !c.max_dump_cnt && live_allocations == before - 3);
    ramoops_free_przs(&c);
    persistent_ram_free(guard);
}
'''


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        receipt = json.loads((HERE / 'results/capture-integration-sources.json').read_text())
        for name, expected in receipt['outputs'].items():
            assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == expected, name
        ram = (SOURCE / 'fs/pstore/ram.c').read_text()
        core = (SOURCE / 'fs/pstore/ram_core.c').read_text()
        header = (SOURCE / 'fs/pstore/wifi_capture.h').read_text()
        assert header == (HERE / 'capture-slot-writer.h').read_text()
        header = '\n'.join(x for x in header.splitlines() if not x.startswith('#include '))
        shim = slot.SHIM.replace('memory[65524]', 'memory[65536]')
        shim = shim.replace('static unsigned int reads,',
                            'static unsigned int interference_read;\nstatic unsigned int reads,')
        shim = shim.replace('#include <stdint.h>', '#include <pthread.h>\n#include <stdint.h>')
        shim = shim.replace('static u8 memory', r"""
static pthread_mutex_t pause_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t pause_condition = PTHREAD_COND_INITIALIZER;
static unsigned int pause_read, paused, released;
void pause_on(unsigned int n) { pause_read = n; paused = released = 0; }
unsigned int is_paused(void) { return __atomic_load_n(&paused, __ATOMIC_SEQ_CST); }
unsigned long denial_bits(void) { return __atomic_load_n(&pmsg_capture_denials, __ATOMIC_SEQ_CST); }
void release_pause(void) {
    pthread_mutex_lock(&pause_lock); released = 1;
    pthread_cond_broadcast(&pause_condition); pthread_mutex_unlock(&pause_lock);
}
static void pause_here(unsigned int n) {
    if (n != pause_read) return;
    pthread_mutex_lock(&pause_lock); __atomic_store_n(&paused, 1, __ATOMIC_SEQ_CST);
    while (!released) pthread_cond_wait(&pause_condition, &pause_lock);
    pthread_mutex_unlock(&pause_lock);
}
static u8 memory""")
        shim = 'static unsigned long pmsg_capture_denials;\n' + shim
        shim = shim.replace("reads++; log_op('R');", "reads++; log_op('R'); if (reads == interference_read) __atomic_fetch_or(&pmsg_capture_denials, 1UL, __ATOMIC_SEQ_CST); pause_here(reads);")
        functions = ''.join(function(core, name) for name in
                            ('persistent_ram_free', 'persistent_ram_capture_map', 'persistent_ram_capture_prepare'))
        functions += function(ram, 'ramoops_init_prz')
        functions += function(ram, 'ramoops_free_przs')
        functions += function(ram, 'ramoops_capture_deny')
        functions += function(ram, 'ramoops_capture_begin') + function(ram, 'ramoops_capture_append')
        # Only the PMSG capture branches change in the two full callbacks.
        for name, bit in (('ramoops_pstore_write_buf', 0), ('ramoops_pstore_erase', 1)):
            callback = function(ram, name)
            assert callback.count(f'return ramoops_capture_deny({bit});') == 1
            assert callback.index(f'return ramoops_capture_deny({bit});') < callback.index(
                'persistent_ram_write(cxt->mprz' if bit == 0 else 'persistent_ram_free_old(prz)')
        # The complete probe is target-compiled. Check these integration boundaries explicitly.
        probe = function(ram, 'ramoops_probe')
        assert probe.index('atomic_cmpxchg(&pmsg_capture_probe_attempted') < probe.index('ramoops_init_przs(')
        assert probe.index('pdata->mem_address != 0x44410000') < probe.index('ramoops_init_przs(')
        assert probe.index('pstore_register(') < probe.index('pmsg_capture_registered = true')
        cls.temp = tempfile.TemporaryDirectory(prefix='wfc-integration-')
        root = Path(cls.temp.name)
        (root / 'test.c').write_text(shim + STUBS + header + '\nstatic struct wfc_writer pmsg_writer;\n' + functions + WRAPPER)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                        '-fPIC', '-shared', '-pthread', str(root / 'test.c'), '-o', str(root / 'test.so')], check=True)
        cls.c = ctypes.CDLL(str(root / 'test.so'))
        cls.c.open_zone.argtypes = [ctypes.c_uint64, ctypes.c_size_t]
        cls.c.begin.argtypes = cls.c.interrupted_begin.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        cls.c.append.argtypes = [ctypes.c_uint, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
        cls.c.operations.restype = ctypes.c_char_p
        cls.c.data.restype = cls.c.old_data.restype = ctypes.POINTER(ctypes.c_ubyte)

    @classmethod
    def tearDownClass(cls):
        cls.c.fresh()
        cls.temp.cleanup()

    def setUp(self):
        self.c.fresh()
        self.c.pause_on(0)

    def open(self):
        self.assertEqual(self.c.open_zone(0x444e0000, 65536), 0)
        self.assertEqual(self.c.zap_count(), 0)
        self.assertEqual(self.c.store_count(), 0)
        self.c.inject(0, 0, 0, 0)

    def begin(self):
        self.open()
        self.assertEqual(self.c.begin(CYCLE, IDENTITY), 0)
        self.c.inject(0, 0, 0, 0)

    def snapshot(self):
        return bytes(self.c.data()[:65536])

    def event(self):
        return self.c.append(2, 0, b'event', 5)

    def assert_closed(self):
        before, count = self.snapshot(), self.c.store_count()
        self.assertLess(self.c.begin(CYCLE, IDENTITY), 0)
        self.assertLess(self.event(), 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.c.store_count(), count)

    def test_snapshot_preserves_invalid_header_and_every_byte(self):
        original = bytes((i * 17 + 3) % 256 for i in range(65536))
        ctypes.memmove(self.c.data(), original, len(original))
        self.open()
        self.assertEqual(bytes(self.c.old_data()[:65536]), original)
        self.assertEqual(self.snapshot(), original)
        self.assertEqual(self.c.begin(CYCLE, IDENTITY), -16)
        self.assertEqual(self.c.store_count(), 0)
        self.assert_closed()

    def test_old_snapshot_prevents_admission_even_if_live_bytes_change(self):
        self.c.data()[65535] = 1
        self.open()
        # Fixture mutation models an external violation, not a clearing API.
        self.c.data()[65535] = 0
        self.assertEqual(self.c.begin(CYCLE, IDENTITY), -16)
        self.assertEqual(self.c.store_count(), 0)
        self.assert_closed()

    def test_mapping_refusals_release_resources_without_stores(self):
        for faults in ((1, 0, 0, 0), (2, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)):
            self.setUp()
            self.c.data()[0] = 7
            before = self.snapshot()
            self.c.map_faults(*faults)
            self.assertLess(self.c.open_zone(0x444e0000, 65536), 0)
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.c.store_count(), 0)
            self.assertEqual(self.c.live_count(), 0)
            self.assertEqual(self.c.reservation_count(), 0)
        for page in range(1, 17):
            self.setUp()
            self.c.map_faults(0, 0, 0, page)
            self.assertEqual(self.c.open_zone(0x444e0000, 65536), -16)
            self.assertEqual(self.c.map_count(), 0)
            self.assertEqual(self.c.live_count(), 0)

    def test_wrong_extent_refuses_before_mapping(self):
        for address, size in ((0x444e0001, 65536), (0x444d0000, 65536),
                              (0x444e0000, 65535), (0x444e0000, 65537)):
            self.setUp()
            self.assertLess(self.c.open_zone(address, size), 0)
            self.assertEqual(self.c.map_count(), 0)
            self.assertEqual(self.c.store_count(), 0)

    def test_dump_cleanup_stops_at_count_and_clears_pointer(self):
        self.c.check_dump_cleanup()
        self.assertEqual(self.c.live_count(), 0)
        self.assertEqual(self.c.store_count(), 0)

    def test_header_then_identity_and_terminal_match_reader(self):
        self.begin()
        raw = self.snapshot()
        self.assertEqual(raw[:12], bytes.fromhex('4442474300000000f4ff0000'))
        self.assertEqual(raw[12:140], r.encode(1, 0, CYCLE, 0, IDENTITY))
        self.assertEqual(bytes(self.c.old_data()[:65536]), bytes(65536))
        self.assertEqual(self.event(), 0)
        self.assertEqual(self.c.append(255, 0, (1).to_bytes(4, 'little'), 4), 0)
        result = r.decode_pmsg_zone(self.snapshot(), CYCLE, IDENTITY)
        self.assertEqual(result['framing'], 'terminal-recorded')
        self.assertEqual(len(result['records']), 3)
        self.assert_closed()

    def test_every_header_store_interruption_stops_before_identity(self):
        for cut in range(1, 13):
            self.setUp()
            self.open()
            self.c.inject(cut, 0, 0, 0)
            self.assertEqual(self.c.interrupted_begin(CYCLE, IDENTITY), -999)
            self.assertEqual(self.c.store_count(), cut)
            self.assertEqual(self.snapshot()[12:], bytes(65524))
            self.assert_closed()

    def test_every_header_readback_fault_stops_before_identity(self):
        for offset in range(1, 25):
            self.setUp()
            self.open()
            self.c.inject(0, 0, 65536 + offset, 0)
            self.assertEqual(self.c.begin(CYCLE, IDENTITY), -5)
            self.assertEqual(self.c.store_count(), 8 if offset <= 12 else 12)
            self.assertEqual(self.snapshot()[12:], bytes(65524))
            self.assert_closed()

    def test_denial_before_and_during_append_closes_capture(self):
        self.open()
        self.c.denied()
        self.assertLess(self.c.begin(CYCLE, IDENTITY), 0)
        self.assertEqual(self.c.store_count(), 0)
        self.assert_closed()
        self.setUp()
        self.begin()
        self.c.inject(0, 0, 0, 200)
        self.assertEqual(self.event(), -16)
        self.assert_closed()

    def test_bad_contract_and_arguments_do_not_initialize_header(self):
        for bad in ('ecc', 'cycle', 'identity'):
            self.setUp()
            self.open()
            if bad == 'ecc':
                self.c.corrupt_contract()
            cycle = bytes(16) if bad == 'cycle' else CYCLE
            identity = None if bad == 'identity' else IDENTITY
            self.assertLess(self.c.begin(cycle, identity), 0)
            self.assertEqual(self.c.store_count(), 0)
            self.assert_closed()

    def test_serialized_callers_keep_contiguous_sequences(self):
        self.begin()
        results = []
        def worker():
            for _ in range(40):
                results.append(self.event())
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(results, [0] * 80)
        self.assertEqual(self.c.append(255, 0, (1).to_bytes(4, 'little'), 4), 0)
        result = r.decode_pmsg_zone(self.snapshot(), CYCLE, IDENTITY)
        self.assertEqual(len(result['records']), 82)
        self.assert_closed()

    def terminal(self):
        self.assertEqual(self.c.append(255, 0, (1).to_bytes(4, 'little'), 4), 0)
        self.c.inject(0, 0, 0, 0)

    def test_completed_denial_after_terminal_survives_raw_recovery(self):
        for bit in (0, 1):
            self.setUp()
            self.begin()
            self.terminal()
            before = self.snapshot()
            self.assertEqual(self.c.deny(bit), -16)
            expected = bytearray(before)
            expected[12 + 511 * 128 + bit] = 255
            self.assertEqual(self.snapshot(), expected)
            self.assertEqual(self.c.store_count(), 1)
            self.assertEqual(self.c.operations(), b'BRBWBRB')
            self.assert_closed()
            retained = self.snapshot()
            self.setUp()
            ctypes.memmove(self.c.data(), retained, len(retained))
            self.open()
            self.assertEqual(bytes(self.c.old_data()[:65536]), retained)
            with self.assertRaisesRegex(ValueError, 'tail'):
                r.decode_pmsg_zone(retained, CYCLE, IDENTITY)
            self.assertLess(self.c.begin(CYCLE, IDENTITY), 0)
            self.assertEqual(self.c.deny(bit), -16)
            self.assertEqual(self.c.store_count(), 0)
            self.assertEqual(self.snapshot(), retained)

    def test_denial_before_acquisition_never_touches_retained_storage(self):
        for mapped in (False, True):
            self.setUp()
            self.c.data()[65535] = 7
            if mapped:
                self.open()
            before = self.snapshot()
            for bit in (0, 1):
                self.assertEqual(self.c.deny(bit), -16)
            if not mapped:
                self.open()
            self.assertLess(self.c.begin(CYCLE, IDENTITY), 0)
            self.assertEqual(self.c.store_count(), 0)
            self.assertEqual(self.snapshot(), before)

    def test_repeated_concurrent_denials_have_two_store_budget(self):
        self.begin()
        before = self.snapshot()
        results = []
        def worker(bit):
            for _ in range(50):
                results.append(self.c.deny(bit))
        threads = [threading.Thread(target=worker, args=(bit,)) for bit in (0, 1, 0, 1)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(results, [-16] * 200)
        self.assertEqual(self.c.store_count(), 2)
        expected = bytearray(before)
        expected[65420:65422] = b'\xff\xff'
        self.assertEqual(self.snapshot(), expected)
        self.assert_closed()

    def test_nonempty_denial_tail_is_preserved_without_retry(self):
        self.begin()
        self.c.data()[65420] = 3
        before = self.snapshot()
        self.assertEqual(self.c.deny(0), -16)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.c.store_count(), 0)
        # Outside clearing cannot reopen a consumed marker attempt.
        self.c.data()[65420] = 0
        self.assertEqual(self.c.deny(0), -16)
        self.assertEqual(self.c.store_count(), 0)
        self.assert_closed()

    def test_denial_io_faults_do_not_retry_or_imply_durable_success(self):
        for lost, bad_read, expected_ret, expected_writes, retained in (
                (1, 0, -5, 1, 0), (0, 2, -5, 1, 255), (0, 1, -16, 0, 0)):
            self.setUp()
            self.begin()
            self.terminal()
            self.c.inject(0, lost, bad_read, 0)
            self.assertEqual(self.c.deny(0), expected_ret)
            self.assertEqual(self.c.store_count(), expected_writes)
            self.assertEqual(self.c.data()[65420], retained)
            self.c.inject(0, 0, 0, 0)
            self.assertEqual(self.c.deny(0), -16)
            self.assertEqual(self.c.store_count(), 0)
            if retained:
                with self.assertRaisesRegex(ValueError, 'tail'):
                    r.decode_pmsg_zone(self.snapshot(), CYCLE, IDENTITY)
            else:
                # An absent marker cannot prove the absence of a denied call.
                self.assertEqual(r.decode_pmsg_zone(self.snapshot(), CYCLE, IDENTITY)['framing'],
                                 'terminal-recorded')
            self.assert_closed()

    def test_denial_waiting_on_terminal_writer_marks_after_unlock(self):
        self.begin()
        self.c.pause_on(200)
        results = {}
        writer = threading.Thread(target=lambda: results.update(
            terminal=self.c.append(255, 0, (1).to_bytes(4, 'little'), 4)))
        denial = threading.Thread(target=lambda: results.update(denial=self.c.deny(0)))
        writer.start()
        try:
            deadline = time.monotonic() + 3
            while not self.c.is_paused() and time.monotonic() < deadline:
                time.sleep(0.001)
            self.assertTrue(self.c.is_paused())
            denial.start()
            while not self.c.denial_bits() and time.monotonic() < deadline:
                time.sleep(0.001)
            self.assertEqual(self.c.denial_bits(), 1)
        finally:
            self.c.release_pause()
            writer.join()
            if denial.ident is not None:
                denial.join()
        self.assertEqual(results, {'terminal': -16, 'denial': -16})
        self.assertEqual(self.c.store_count(), 129)
        self.assertEqual(self.c.data()[65420], 255)
        with self.assertRaisesRegex(ValueError, 'tail'):
            r.decode_pmsg_zone(self.snapshot(), CYCLE, IDENTITY)
        self.assert_closed()

    def test_recovery_snapshot_decodes_and_cannot_be_reused(self):
        self.begin()
        self.assertEqual(self.event(), 0)
        self.assertEqual(self.c.append(255, 0, (2).to_bytes(4, 'little'), 4), 0)
        retained = self.snapshot()
        self.setUp()
        ctypes.memmove(self.c.data(), retained, len(retained))
        self.open()
        recovered = bytes(self.c.old_data()[:65536])
        self.assertEqual(recovered, retained)
        self.assertEqual(r.decode_pmsg_zone(recovered, CYCLE, IDENTITY)['producer_status'], 2)
        self.assertEqual(self.c.begin(CYCLE, IDENTITY), -16)
        self.assertEqual(self.snapshot(), retained)
        self.assert_closed()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args, remaining = parser.parse_known_args()
    SOURCE = args.source
    unittest.main(argv=[__file__, *remaining])
