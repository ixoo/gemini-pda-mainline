#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native mapping/divided-loader comparison with mocked crypto, HIF and EMI."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dma_fixture', HERE / 'test-dma-capture.py')
dma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dma)
r = dma.r
BASE = 'drivers/misc/mediatek/connectivity/wlan/gen3/'
HIF = BASE + 'os/linux/hif/ahb_sdioLike/'

SHIM = r'''
#include <assert.h>
#include <sys/types.h>
typedef int64_t s64, loff_t;
typedef uint32_t UINT_32, WLAN_STATUS, *PUINT_32;
typedef uint8_t UINT_8;
typedef void *PVOID, **PPVOID;
typedef struct { struct { struct wfc_dma_trace capture; } rHifInfo; } GLUE_INFO_T, *P_GLUE_INFO_T;
typedef struct { P_GLUE_INFO_T prGlueInfo; } ADAPTER_T, *P_ADAPTER_T;
#define IN
#define OUT
#define FALSE 0
#define TRUE 1
#define WLAN_STATUS_SUCCESS 0
#define WLAN_STATUS_FAILURE 0xc0000001U
#define ALIGN_4(n) (((n) + 3U) & ~3U)
#define ASSERT(p) assert(p)
#define DEBUGFUNC(...) ((void)0)
static void ignore_log(const char *format, ...) { (void)format; }
#define DBGLOG(module,level,...) ignore_log(__VA_ARGS__)
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define __aligned(n) __attribute__((aligned(n)))
#define CRYPTO_MINALIGN_ATTR __aligned(8)
#define memzero_explicit(p,n) memset(p,0,n)
#define CFG_ENABLE_FW_DOWNLOAD 1
#define CFG_ENABLE_FW_DIVIDED_DOWNLOAD 1
static GLUE_INFO_T glue;
static ADAPTER_T adapter = { &glue };
static u8 buffer[WFC_FW_BYTES], emi[0x80000];
static int io_mode, native_mode, crypto_mode, lost_record;
static uint64_t native_events[128];
static unsigned int native_count, allocations, frees, hashes;
static struct wfc_fw_buffer witness;
static void event(uint64_t value) { assert(native_count < 128); native_events[native_count++] = value; }
struct fake_inode { loff_t i_size; } inode;
struct fake_dentry { struct fake_inode *d_inode; } entry;
struct fake_file;
struct fake_ops { ssize_t (*read)(struct fake_file *, void *, size_t, int64_t *); } operations;
struct fake_file { struct fake_ops *f_op; int64_t f_pos;
    struct { struct fake_dentry *dentry; } f_path; } file, *filp;
static ssize_t read_file(struct fake_file *p, void *out, size_t bytes, int64_t *position) {
    assert(p == &file && out == buffer && bytes == WFC_FW_BYTES && position == &file.f_pos);
    event(2); event(bytes); event(*position); *position += bytes;
    return io_mode == 3 ? (ssize_t)bytes - 1 : (ssize_t)bytes;
}
static WLAN_STATUS kalFirmwareOpen(P_GLUE_INFO_T p) {
    assert(p == &glue); event(1); return io_mode == 1 ? WLAN_STATUS_FAILURE : WLAN_STATUS_SUCCESS;
}
static void *vmalloc(size_t bytes) { event(3); event(bytes); return io_mode == 2 ? NULL : buffer; }
static void vfree(void *p) { assert(p == buffer); event(4); }
static WLAN_STATUS kalFirmwareClose(P_GLUE_INFO_T p) { assert(p == &glue); event(5); return 0; }
struct crypto_shash { int marker; } algorithm;
struct sha256_state { u32 state[8]; u64 count; u8 buf[64]; };
struct shash_desc { struct crypto_shash *tfm; u32 flags; void *__ctx[] CRYPTO_MINALIGN_ATTR; };
static int (*hash_callback)(const void *, u32, void *);
void set_hash(int (*callback)(const void *, u32, void *)) { hash_callback = callback; }
static struct crypto_shash *crypto_alloc_shash(const char *name, u32 type, u32 mask) {
    assert(!strcmp(name, "sha256-generic") && !type && !mask); allocations++;
    return crypto_mode == 1 ? (void *)-ENOMEM : &algorithm;
}
static unsigned int crypto_shash_descsize(struct crypto_shash *p) {
    assert(p == &algorithm); return sizeof(struct sha256_state) + (crypto_mode == 2);
}
static unsigned int crypto_shash_digestsize(struct crypto_shash *p) {
    assert(p == &algorithm); return crypto_mode == 3 ? 28 : 32;
}
static int crypto_shash_digest(struct shash_desc *desc, const u8 *data, u32 bytes, u8 *out) {
    assert(desc->tfm == &algorithm && !desc->flags && data == buffer && bytes == WFC_FW_BYTES);
    hashes++;
    if ((crypto_mode == 4 && hashes == 1) || (crypto_mode == 5 && hashes == 2)) return -EIO;
    if (crypto_mode == 6) glue.rHifInfo.capture.retired.counter = 1;
    if (lost_record == 3 && hashes == 2) drop = writes + 1;
    assert(hash_callback); return hash_callback(data, bytes, out);
}
static void crypto_free_shash(struct crypto_shash *p) { assert(p == &algorithm); frees++; }
typedef struct { u32 u4Offset; u8 ucKIdx, ucEnc; uint16_t u2Reserved; u32 u4Length, u4DestAddr; } SECTION;
typedef struct { u32 u4Signature, u4CRC, u4NumOfEntries; uint16_t major, minor;
    u32 chip, reserved; SECTION arSection[]; } FIRMWARE_DIVIDED_DOWNLOAD_T, *P_FIRMWARE_DIVIDED_DOWNLOAD_T;
static u64 gConEmiPhyBase;
#define NO_PROTECTION 0
#define FORBIDDEN 5
#define SET_ACCESS_PERMISSON(a,b,c,d,e,f,g,h) ((a)|((b)<<3)|((c)<<6)|((d)<<9)|((e)<<12)|((f)<<15)|((g)<<18)|((h)<<21))
static int emi_mpu_set_region_protection(u64 first, u64 last, u32 region, u32 permission) {
    event(10); event(first); event(last); event(region); event(permission); return 0;
}
static void *ioremap_nocache(u64 first, u32 bytes) {
    assert(first == gConEmiPhyBase && bytes == sizeof(emi)); event(11); return emi;
}
static void kalMemCopy(void *destination, const void *source, size_t bytes) {
    assert((u8 *)destination >= emi && (u8 *)destination + bytes <= emi + sizeof(emi));
    assert((const u8 *)source >= buffer && (const u8 *)source + bytes <= buffer + sizeof(buffer));
    event(12); event((u8 *)destination - emi); event((const u8 *)source - buffer); event(bytes);
    memcpy(destination, source, bytes);
}
static WLAN_STATUS wlanImageSectionDownloadStage(P_ADAPTER_T p, void *image, u32 index,
                                                 u32 bytes, int valid, u32 address) {
    assert(p == &adapter && image == buffer && bytes == sizeof(buffer) && valid && !address);
    event(20); event(index);
    if ((native_mode == 4 && index == 0) || native_mode == 5) buffer[WFC_FW_BYTES - 1] ^= 1;
    return (native_mode == 1 && index == 0) || (native_mode == 2 && index == 1) ? WLAN_STATUS_FAILURE : 0;
}
'''

WRAPPER = r'''
static void setup(int enabled, int io, int native, int crypto, int lost) {
    io_mode=io; native_mode=native; crypto_mode=crypto; lost_record=lost;
    native_count=allocations=frees=hashes=0;
    memset(&glue,0,sizeof(glue)); memset(&witness,0,sizeof(witness));
    memset(memory,0,sizeof(memory)); memset(&state,0,sizeof(state));
    reads=writes=barriers=trace_length=cut=drop=fault_read=0;
    wfc_devices.counter=wfc_transactions.counter=wfc_fw_reads.counter=0;
    memset(buffer,0,sizeof(buffer)); memset(emi,0,sizeof(emi));
    put_unaligned_le32(0x454b544d,buffer); put_unaligned_le32(4,buffer+8);
    for (unsigned int i=0;i<4;i++) {
        u8 *section=buffer+24+i*16;
        put_unaligned_le32(88+i*16,section); section[4]=i & 3; section[5]=i<2;
        put_unaligned_le32(16,section+8); put_unaligned_le32(0x10001000+i*0x1000,section+12);
        memset(buffer+88+i*16,0x40+i,16);
    }
    file.f_op=&operations; operations.read=read_file; file.f_pos=99;
    inode.i_size=sizeof(buffer); entry.d_inode=&inode; file.f_path.dentry=&entry; filp=&file;
    gConEmiPhyBase=native==3 ? 0 : 0x10000000;
    if (enabled) {
        u8 cycle[16],identity[80];
        for(unsigned int i=0;i<16;i++) cycle[i]=i;
        for(unsigned int i=0;i<80;i++) identity[i]=i;
        assert(!wfc_writer_begin(&state,memory,sizeof(memory),cycle,identity));
    }
    wfc_dma_bind(&glue.rHifInfo.capture,&glue,1);
    if(lost==1) drop=writes+1;
}
static void terminal(void) {
    u8 status[4]={1,0,0,0};
    if(ramoops_capture_active()) ramoops_capture_append(255,0,status,4);
}
u32 run_case(int enabled,int io,int native,int crypto,int lost,int bad_witness) {
    setup(enabled,io,native,crypto,lost);
    void *mapped=NULL; UINT_32 bytes=0;
    void *handle=MAPPING_CALL;
    if (!handle) { terminal(); return WLAN_STATUS_FAILURE; }
    assert(handle==buffer && mapped==buffer && bytes==sizeof(buffer));
    if(lost==2) drop=writes+1;
    if(bad_witness==1) witness.read_id=0;
    if(bad_witness==2) witness.device++;
    if(bad_witness==3) witness.bytes--;
    if(bad_witness==4) witness.buffer=buffer+1;
    u32 status=LOADER_CALL;
    terminal(); return status;
}
void run_guard(int fault) {
    setup(1,0,0,0,0);
    void *mapped=NULL; UINT_32 bytes=0;
    assert(MAPPING_CALL == buffer);
    struct wfc_fw_image image;
    const struct wfc_dma_trace *binding=&glue.rHifInfo.capture;
    const struct wfc_fw_buffer *read=&witness;
    const void *input=buffer, *header=buffer;
    if(fault==1) read=NULL;
    if(fault==2) binding=NULL;
    if(fault==3) input=NULL;
    if(fault==4) header=buffer+1;
    if(fault==5) bytes--;
    if(fault==6) buffer[0]^=1;
    if(fault==7) put_unaligned_le32(5,buffer+8);
    if(fault==8) put_unaligned_le32(87,buffer+24);
    if(fault==9) put_unaligned_le32(WFC_FW_BYTES+1,buffer+24);
    if(fault==10) put_unaligned_le32(0,buffer+32);
    if(fault==11) put_unaligned_le32(WFC_FW_BYTES,buffer+32);
    if(fault==12) put_unaligned_le32(UINT32_MAX,buffer+36);
    if(fault==13) glue.rHifInfo.capture.retired.counter=1;
    if(fault==14) witness.read_id=0;
    if(fault==15) witness.bytes--;
    if(fault==16) witness.device++;
    if(fault==17) glue.rHifInfo.capture.device=0;
    wfc_fw_image_begin(&image,binding,read,input,bytes,header);
    if(fault==18) { wfc_fw_image_section(&image,0); wfc_fw_image_section(&image,0); }
    if(fault==19) wfc_fw_image_section(&image,4);
    assert(wfc_fw_image_return(&image,0x1234)==0x1234);
    terminal();
}
u8 *data(void) { return memory; }
u8 *firmware(void) { return buffer; }
uint64_t *effects(void) { return native_events; }
unsigned int effect_count(void) { return native_count; }
unsigned int store_count(void) { return writes; }
unsigned int allocation_count(void) { return allocations; }
unsigned int free_count(void) { return frees; }
unsigned int hash_count(void) { return hashes; }
u32 witness_field(unsigned int n) {
    return n==0 ? witness.buffer==buffer : n==1 ? witness.bytes : n==2 ? witness.read_id : witness.device;
}
'''


def build(root, tree, helpers, observed, changed):
    source = dma.writer.SHIM + dma.without_includes((HERE / 'capture-slot-writer.h').read_text()) + dma.EXTRA
    for relative in ('include/hif_capture.h', 'hif_capture.c'):
        source += dma.without_includes((helpers / relative).read_text())
    source += dma.without_includes((changed / HIF / 'include/hif_fw_capture.h').read_text())
    source += SHIM
    source += dma.without_includes((changed / HIF / 'hif_fw_capture.c').read_text())
    text = (tree / BASE / 'os/linux/gl_kal.c').read_text()
    start = text.index('/* The selected MT6797 observer')
    source += text[start:text.index('static WLAN_STATUS\nkalFirmwareLoadCapture', start)]
    source += 'static WLAN_STATUS\n' + dma.native.fixture.function(text, 'kalFirmwareLoadCapture')
    for name in ('kalFirmwareLoad', 'kalFirmwareSize', 'kalFirmwareImageMapping'):
        source += dma.native.fixture.function(text, name)
    source += 'static WLAN_STATUS\n' + dma.native.fixture.function(
        (tree / BASE / 'common/wlan_lib.c').read_text(), 'wlanImageDividDownload')
    mapping = 'kalFirmwareImageMapping(&glue,&mapped,&bytes' + (',&witness)' if observed else ')')
    loader = 'wlanImageDividDownload(&adapter,(void *)buffer,buffer,bytes,0' + (',&witness)' if observed else ')')
    source += WRAPPER.replace('MAPPING_CALL', mapping).replace('LOADER_CALL', loader)
    path = root / ('observed' if observed else 'parent')
    path.with_suffix('.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                    str(path.with_suffix('.c')), '-o', str(path.with_suffix('.so'))], check=True)
    library = ctypes.CDLL(str(path.with_suffix('.so')))
    library.run_case.restype = ctypes.c_uint32
    library.data.restype = library.firmware.restype = ctypes.POINTER(ctypes.c_ubyte)
    library.effects.restype = ctypes.POINTER(ctypes.c_uint64)
    return library


def effects(library):
    return list(library.effects()[:library.effect_count()])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('changed', type=Path)
    parser.add_argument('dma_sources', type=Path)
    args = parser.parse_args()
    receipt = json.loads((HERE / 'results/firmware-image-capture-sources.json').read_text())
    for section, tree in (('parents', args.parent), ('outputs', args.changed)):
        for path, expected in receipt[section].items():
            assert hashlib.sha256((tree / path).read_bytes()).hexdigest() == expected, path
    pins = json.loads((HERE / 'results/dma-capture-sources.json').read_text())['outputs']
    for path, expected in pins.items():
        if Path(path).name in ('hif_capture.h', 'hif_capture.c'):
            relative = ('include/' if path.endswith('.h') else '') + Path(path).name
            assert hashlib.sha256((args.dma_sources / relative).read_bytes()).hexdigest() == expected
    digests = []
    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p)
    def hash_buffer(data, size, out):
        digest = hashlib.sha256(ctypes.string_at(data, size)).digest()
        digests.append(digest)
        ctypes.memmove(out, digest, len(digest))
        return 0
    with tempfile.TemporaryDirectory(prefix='wifi-fw-image-') as tmp:
        parent = build(Path(tmp), args.parent, args.dma_sources, False, args.changed)
        observed = build(Path(tmp), args.changed, args.dma_sources, True, args.changed)
        parent.set_hash(hash_buffer)
        observed.set_hash(hash_buffer)
        for native in range(6):
            expected_status = parent.run_case(0, 0, native, 0, 0, 0)
            expected = effects(parent)
            for enabled in (0, 1):
                digests.clear()
                assert observed.run_case(enabled, 0, native, 0, 0, 0) == expected_status
                assert effects(observed) == expected
                if not enabled:
                    assert observed.allocation_count() == observed.hash_count() == observed.store_count() == 0
                    continue
                assert observed.allocation_count() == observed.free_count() == 1
                assert observed.hash_count() == 2
                data, result = dma.stream(observed)
                rows = [row for row in result['records'] if row['kind'] == 7]
                assert [int.from_bytes(row['payload'][:4], 'little') for row in rows[:4]] == [8, 9, 10, 11]
                assert r.FW_IMAGE.unpack(rows[4]['payload']) == (5, 1, 1, 411632, 4, digests[0])
                if native == 4:
                    assert digests[0] != digests[1] and result['producer_status'] == 2
                    assert int.from_bytes(rows[-1]['payload'][:4], 'little') == 6
                else:
                    assert digests[0] == digests[1]
                    assert r.FW_IMAGE_RETURN.unpack(rows[-1]['payload']) == (7, 1, 1, expected_status)
                if native in (0, 5):
                    sections = [(88 + i * 16, 16, 0x10001000 + i * 0x1000, int(i < 2), i)
                                for i in range(4)]
                    assert r.check_image_read(data, dma.writer.CYCLE, digests[0], 411632, sections)['checked_read'] == 1
                    if native == 0:
                        for fault in ('read_id', 'adapter', 'extent', 'order', 'envelope'):
                            altered = [dict(row) for row in result['records']]
                            read_rows = [row for row in altered if row['kind'] == 7 and
                                         int.from_bytes(row['payload'][:4], 'little') in (8, 9, 10, 11)]
                            image_rows = [row for row in altered if row['kind'] == 7 and
                                          int.from_bytes(row['payload'][:4], 'little') in (5, 6, 7)]
                            if fault == 'order':
                                altered = [row for row in altered[:-1] if row not in read_rows] + read_rows + altered[-1:]
                            elif fault == 'envelope':
                                for row in image_rows:
                                    row['transaction'] += 1
                            else:
                                for row in read_rows:
                                    if fault == 'read_id':
                                        row['transaction'] += 1
                                    else:
                                        layout = r.FW_STOP_LAYOUTS[int.from_bytes(row['payload'][:4], 'little')]
                                        values = list(layout.unpack(row['payload']))
                                        if fault == 'adapter':
                                            values[1] += 1
                                        elif values[0] == 9:
                                            values[2] = values[3] = 16
                                        elif values[0] == 10:
                                            values[2] = values[4] = 16
                                        elif values[0] == 11:
                                            values[3] = 16
                                        row['payload'] = layout.pack(*values)
                            bad_data = b''.join(r.encode(row['kind'], i, dma.writer.CYCLE,
                                                       row['transaction'], row['payload'])
                                                for i, row in enumerate(altered))
                            r.check_firmware_read(bad_data, dma.writer.CYCLE)
                            r._image_metadata(bad_data, dma.writer.CYCLE, digests[0], 411632, sections)
                            try:
                                r.check_image_read(bad_data, dma.writer.CYCLE, digests[0], 411632, sections)
                            except ValueError:
                                pass
                            else:
                                raise AssertionError('accepted wrong read/image join: ' + fault)
                    assert [r.FW_SECTION.unpack(row['payload']) for row in rows[5:9]] == [
                        (6, 1, 1, i, 88 + i * 16, 16, 0x10001000 + i * 0x1000, int(i < 2), i)
                        for i in range(4)]
        for io in (1, 2, 3):
            expected_status = parent.run_case(1, io, 0, 0, 0, 0)
            expected = effects(parent)
            assert observed.run_case(1, io, 0, 0, 0, 0) == expected_status
            assert effects(observed) == expected
            assert observed.allocation_count() == observed.hash_count() == 0
            assert [observed.witness_field(i) for i in range(4)] == [0, 0, 0, 0]
        for crypto in range(1, 7):
            assert observed.run_case(1, 0, 0, crypto, 0, 0) == 0
            assert observed.allocation_count() == 1
            assert observed.free_count() == int(crypto != 1)
            _, result = dma.stream(observed)
            assert result['producer_status'] == 2
        for bad in range(1, 5):
            assert observed.run_case(1, 0, 0, 0, 0, bad) == 0
            assert observed.allocation_count() == observed.hash_count() == 0
            _, result = dma.stream(observed)
            assert result['producer_status'] == 2
        for lost in (1, 2, 3):
            assert observed.run_case(1, 0, 0, 0, lost, 0) == 0
            assert observed.allocation_count() == observed.free_count()
            _, result = dma.stream(observed)
            assert result['framing'] == 'incomplete'
        for fault in range(1, 20):
            observed.run_guard(fault)
            assert observed.allocation_count() == observed.free_count() == int(fault >= 18)
            assert observed.hash_count() == int(fault >= 18)
            _, result = dma.stream(observed)
            assert result['producer_status'] == 2
    print('firmware-image-capture=pass native_paths=6 mapping_failures=3 crypto_faults=6 witness_faults=4 lost_records=3 guards=19 bad_record_joins=5')
    print('hashes_use_actual_buffer=verified boundary_digest_match_does_not_prove_immutability')
    print('no_real_crypto_backend_file_io_radio_or_device_execution')


if __name__ == '__main__':
    main()
