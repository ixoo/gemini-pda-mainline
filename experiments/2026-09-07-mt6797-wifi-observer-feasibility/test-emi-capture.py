#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise native EMI loader, locked wrapper and lower call with injected I/O."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('image_fixture', HERE / 'test-firmware-image-capture.py')
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)
dma, r = image.dma, image.r
BASE, HIF = image.BASE, image.HIF
MPU = 'drivers/misc/mediatek/emi_mpu/'
HEADER = 'drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h'

EXTRA = r'''
#define __force
static int emi_mpu_lock, lock_held, secure_calls;
#define spin_lock_irqsave(p,f) do { assert((p)==&emi_mpu_lock && !lock_held); (f)=1; lock_held=1; event(30); } while (0)
#define spin_unlock_irqrestore(p,f) do { assert((p)==&emi_mpu_lock && lock_held && (f)==1); event(31); lock_held=0; } while (0)
static int emi_mpu_smc_set(u64 start, u64 end, u32 policy) {
    assert(lock_held); secure_calls++; event(10); event(start); event(end); event(policy);
    if(native_mode==9) return -13;
    if(native_mode==10) return 7;
    return 0;
}
static int locked_append(unsigned int kind,u32 tx,const u8 *data,size_t bytes) {
    assert(kind==8 && get_unaligned_le32(data)==2 && lock_held);
    return ramoops_capture_append(kind,tx,data,bytes);
}
'''


def function(text, name):
    return dma.native.fixture.function(text, name)


def build(root, tree, image_sources, helpers, changed, secure):
    source = dma.writer.SHIM + dma.without_includes((HERE / 'capture-slot-writer.h').read_text()) + dma.EXTRA
    for rel in ('include/hif_capture.h', 'hif_capture.c'):
        source += dma.without_includes((helpers / rel).read_text())
    source += dma.without_includes((tree / HIF / 'include/hif_fw_capture.h').read_text())
    shim = image.SHIM
    begin = shim.index('static int emi_mpu_set_region_protection(')
    end = shim.index('static void *ioremap_nocache', begin)
    shim = shim[:begin] + shim[end:]
    shim = shim.replace('return emi;', 'return native_mode==7 ? NULL : emi;')
    shim = shim.replace('    assert((u8 *)destination >= emi', '    if(native_mode==7) { event(12); return; }\n    assert((u8 *)destination >= emi')
    shim = shim.replace('    memcpy(destination, source, bytes);', '    memcpy(destination, source, bytes);\n    if(native_mode==8) drop=writes+1;')
    source += shim + EXTRA
    header = (tree / HEADER).read_text()
    begin = header.index('#define SET_ACCESS_PERMISSON(')
    source += '\n#undef SET_ACCESS_PERMISSON\n' + header[begin:header.index('\n\n', begin)] + '\n'
    if secure:
        source += '#define CONFIG_MTK_PSCI 1\n'
    low = (tree / MPU / 'emi_reg_rw.c').read_text()
    if changed:
        source += '#define ramoops_capture_append locked_append\n'
        source += function(low, 'emi_capture_protection')
        source += '#undef ramoops_capture_append\n'
        source += function(low, 'mt_emi_mpu_set_region_protection_capture')
    source += function(low, 'mt_emi_mpu_set_region_protection')
    high = (tree / MPU / 'mt6797/emi_mpu.c').read_text()
    if changed:
        source += function(high, 'emi_mpu_set_region_protection_capture')
    source += function(high, 'emi_mpu_set_region_protection')
    source += dma.without_includes((tree / HIF / 'hif_fw_capture.c').read_text())
    text = (image_sources / BASE / 'os/linux/gl_kal.c').read_text()
    begin = text.index('/* The selected MT6797 observer')
    source += text[begin:text.index('static WLAN_STATUS\nkalFirmwareLoadCapture', begin)]
    source += 'static WLAN_STATUS\n' + function(text, 'kalFirmwareLoadCapture')
    for name in ('kalFirmwareLoad', 'kalFirmwareSize', 'kalFirmwareImageMapping'):
        source += function(text, name)
    source += 'static WLAN_STATUS\n' + function((tree / BASE / 'common/wlan_lib.c').read_text(), 'wlanImageDividDownload')
    wrapper = image.WRAPPER
    wrapper = wrapper.replace('native_count=allocations=frees=hashes=0;', 'native_count=allocations=frees=hashes=0; lock_held=secure_calls=0;' +
                              ('wfc_emi_sections.counter=0;' if changed else ''))
    wrapper = wrapper.replace('    file.f_op=&operations;', '    if(native==6) put_unaligned_le32(0x100ffff0,buffer+24+2*16+12);\n    file.f_op=&operations;')
    wrapper = wrapper.replace('MAPPING_CALL', 'kalFirmwareImageMapping(&glue,&mapped,&bytes,&witness)')
    wrapper = wrapper.replace('LOADER_CALL', 'wlanImageDividDownload(&adapter,(void *)buffer,buffer,bytes,0,&witness)')
    source += wrapper
    if changed:
        source += r'''
void run_emi_guard(int fault) {
    setup(1,0,0,0,0);
    void *mapped=NULL; UINT_32 bytes=0;
    assert(kalFirmwareImageMapping(&glue,&mapped,&bytes,&witness)==buffer);
    struct wfc_fw_image capture;
    wfc_fw_image_begin(&capture,&glue.rHifInfo.capture,&witness,buffer,bytes,buffer);
    wfc_fw_image_section(&capture,0); wfc_fw_image_section(&capture,1); wfc_fw_image_section(&capture,2);
    if(fault==2) wfc_fw_emi_begin(&capture,1,gConEmiPhyBase);
    else if(fault==3) wfc_fw_emi_begin(&capture,4,gConEmiPhyBase);
    else if(fault==4) { capture.next=0; wfc_fw_emi_begin(&capture,2,gConEmiPhyBase); }
    else {
        assert(wfc_fw_emi_begin(&capture,2,gConEmiPhyBase)==1);
        if(fault==1) {
            assert(wfc_fw_emi_begin(&capture,2,gConEmiPhyBase)==2);
            assert(!wfc_fw_emi_begin(&capture,2,gConEmiPhyBase));
        } else {
            wfc_fw_emi_mapping(&capture,gConEmiPhyBase,sizeof(emi),fault==5 ? NULL : emi);
            const void *target=emi+0x3000, *input=buffer+120;
            u32 length=16, stage=1;
            if(fault==6) input=(void *)((uintptr_t)buffer-1);
            if(fault==7) target=(void *)((uintptr_t)emi-1);
            if(fault==8) target=emi+sizeof(emi);
            if(fault==9) input=buffer+sizeof(buffer);
            if(fault==10) length=0;
            if(fault==11) stage=3;
            wfc_fw_emi_copy(&capture,stage,target,input,length);
        }
    }
    assert(wfc_fw_image_return(&capture,0x1234)==0x1234);
    terminal();
}
'''
    source += '\nint lock_state(void) { return lock_held; }\nint secure_count(void) { return secure_calls; }\n'
    label = ('changed' if changed else 'parent') + ('-secure' if secure else '-stub')
    path = root / label
    path.with_suffix('.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-Wno-unused-parameter',
                    '-fPIC', '-shared', str(path.with_suffix('.c')), '-o', str(path.with_suffix('.so'))], check=True)
    library = ctypes.CDLL(str(path.with_suffix('.so')))
    library.run_case.restype = ctypes.c_uint32
    library.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    library.effects.restype = ctypes.POINTER(ctypes.c_uint64)
    return library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'changed', 'image_sources', 'dma_sources'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/emi-capture-sources.json').read_text())
    for section, tree in (('parents', args.parent), ('outputs', args.changed)):
        for name, digest in pins[section].items():
            assert hashlib.sha256((tree / name).read_bytes()).hexdigest() == digest, name
    pins = json.loads((HERE / 'results/firmware-image-capture-sources.json').read_text())
    name = BASE + 'os/linux/gl_kal.c'
    assert hashlib.sha256((args.image_sources / name).read_bytes()).hexdigest() == pins['outputs'][name]
    pins = json.loads((HERE / 'results/dma-capture-sources.json').read_text())['outputs']
    for name, digest in pins.items():
        if Path(name).name in ('hif_capture.h', 'hif_capture.c'):
            rel = ('include/' if name.endswith('.h') else '') + Path(name).name
            assert hashlib.sha256((args.dma_sources / rel).read_bytes()).hexdigest() == digest
    digests = []
    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p)
    def hash_buffer(data, size, out):
        digest = hashlib.sha256(ctypes.string_at(data, size)).digest()
        digests.append(digest)
        ctypes.memmove(out, digest, 32)
        return 0
    with tempfile.TemporaryDirectory(prefix='wifi-emi-capture-') as tmp:
        for secure in (False, True):
            parent = build(Path(tmp), args.parent, args.image_sources, args.dma_sources, False, secure)
            changed = build(Path(tmp), args.changed, args.image_sources, args.dma_sources, True, secure)
            parent.set_hash(hash_buffer)
            changed.set_hash(hash_buffer)
            for native in range(11):
                status = parent.run_case(0, 0, native, 0, 0, 0)
                expected = image.effects(parent)
                for enabled in (0, 1):
                    digests.clear()
                    assert changed.run_case(enabled, 0, native, 0, 0, 0) == status
                    assert image.effects(changed) == expected, (secure, native, enabled)
                    assert not changed.lock_state()
                    if not enabled:
                        assert not changed.store_count()
                        continue
                    data, decoded = dma.stream(changed)
                    rows = [row for row in decoded['records'] if row['kind'] == 8]
                    if secure and native in (0, 5):
                        assert len(rows) == 16
                        sections = [(88+i*16, 16, 0x10001000+i*0x1000, int(i<2), i) for i in range(4)]
                        assert r.check_image_read(data, dma.writer.CYCLE, digests[0], 411632, sections)['checked_read'] == 1
                        assert r.check_image_sections(data, dma.writer.CYCLE, digests[0], 411632, sections)['checked_emi_indices'] == [2, 3]
                    else:
                        try:
                            r.check_emi(data, dma.writer.CYCLE)
                        except ValueError:
                            pass
                        else:
                            # Persistent mutation affects image identity, not these copy records.
                            assert secure and native == 4
                    if native in (9, 10) and secure:
                        returns = [r.EMI_PROTECTION.unpack(row['payload'])[-1] for row in rows
                                   if int.from_bytes(row['payload'][:4], 'little') == 2 and
                                   int.from_bytes(row['payload'][8:12], 'little') == 2]
                        assert returns == [(-13 if native==9 else 7)] * 4
                        assert status == 0
            for fault in range(1, 12):
                changed.run_emi_guard(fault)
                _, result = dma.stream(changed)
                assert result['producer_status'] == 2, fault
                assert changed.allocation_count() == changed.free_count() == 1
                assert changed.secure_count() == 0
    print('emi-capture=pass native_paths=11 capture_states=2 secure_branches=2 guards=11')
    print('actual_lower_status_and_lock_context=verified image_read_and_emi_join=pass')
    print('no_real_mapping_secure_call_memory_protection_radio_or_device_execution')


if __name__ == '__main__':
    main()
