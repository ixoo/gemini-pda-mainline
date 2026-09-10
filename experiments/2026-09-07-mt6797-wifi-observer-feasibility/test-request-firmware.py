#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual request/read/image/EMI functions with injected tasks, file, crypto and I/O."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


emi = module('request_fw_emi', 'test-emi-capture.py')
request = module('request_fw_base', 'test-request-capture.py')
r = request.r
CYCLE = request.CYCLE


def build(root, tree):
    extra=request.SHIM.replace('operations[2]','request_operations[2]').replace('static unsigned int attempts, loss_site;', '')
    extra+=request.dma.without_includes((tree/request.HEADER).read_text())
    extra+=r'''
    static int request_fault;
    void set_request_loss(unsigned int loss) { request_loss=loss; }
    void set_request_fault(int fault) { request_fault=fault; }
    static void request_boot(void) {
        request_appends=0;
        memset(tasks,0,sizeof(tasks));memset(request_operations,0,sizeof(request_operations));
        wfc_request_lock=0;wfc_request_phase=WFC_REQ_UNUSED;
        wfc_request_root=wfc_request_worker=NULL;wfc_request_op=NULL;
        wfc_request_id=wfc_request_common=wfc_request_firmware_stage=0;
        wfc_request_firmware_device=wfc_request_firmware_image=0;
        current=&tasks[0];mt6797_wfc_request_begin(0x80000003UL);
        request_operations[0].op.opId=3;request_operations[0].op.au4OpData[0]=3;
        mt6797_wfc_request_bind(&request_operations[0],3,3,4000);
        wfc_request_submit(&request_operations[0]);current=&tasks[1];
        wfc_request_worker_begin(&request_operations[0]);
        if(request_fault==1) current=&tasks[2];
        if(request_fault==8) mt6797_wfc_request_firmware(0,1,1,0);
        if(request_fault==9) mt6797_wfc_request_firmware(4,1,1,0);
    }
    static void request_finish_on(u32 status) {
        if(request_fault==7) mt6797_wfc_request_firmware(3,1,1,0);
        wfc_request_worker_end(&request_operations[0],status);
        current=&tasks[0];wfc_request_wait(&request_operations[0],10,true,status,!status);
        mt6797_wfc_request_end(status ? -14 : 0);
    }
    void request_finish_off(void) {
        current=&tasks[0];mt6797_wfc_request_begin(3);
        request_operations[0].op.opId=4;
        mt6797_wfc_request_bind(&request_operations[0],4,3,4000);
        wfc_request_submit(&request_operations[0]);current=&tasks[1];
        wfc_request_worker_begin(&request_operations[0]);
        mt6797_wfc_request_common_begin();mt6797_wfc_request_common_end();
        wfc_request_worker_end(&request_operations[0],0);
        current=&tasks[0];wfc_request_wait(&request_operations[0],10,true,0,1);
        mt6797_wfc_request_end(0);
    }
    unsigned int request_pins(void) { return tasks[0].pins+tasks[1].pins+tasks[2].pins; }
    void request_other_task(void) { current=&tasks[2]; }
    '''
    saved_extra, saved_wrapper, saved_dma = emi.EXTRA, emi.image.WRAPPER, emi.dma.EXTRA
    emi.EXTRA+=extra
    emi.dma.EXTRA = 'static unsigned int request_loss, request_appends;\n' + emi.dma.EXTRA.replace(
        'return wfc_slot_write(&state, kind, tx, p, n);',
        'if(kind==10 && get_unaligned_le32(p)>=25 && get_unaligned_le32(p)<=27 && ++request_appends==request_loss) drop=writes+1;\n'
        'return wfc_slot_write(&state, kind, tx, p, n);')
    emi.image.WRAPPER=emi.image.WRAPPER.replace('    wfc_dma_bind(', '    request_boot();\n    wfc_dma_bind(')
    emi.image.WRAPPER=emi.image.WRAPPER.replace('    u32 status=LOADER_CALL;', '''
        if(request_fault==2) current=&tasks[2];
        if(request_fault==3) witness.read_id++;
        if(request_fault==4) { witness.device++;glue.rHifInfo.capture.device++; }
        if(request_fault==5) mt6797_wfc_request_firmware(1,1,1,0);
        if(request_fault==6) mt6797_wfc_request_firmware(3,1,1,0);
        u32 status=LOADER_CALL;
        request_finish_on(status);''')
    emi.image.WRAPPER=emi.image.WRAPPER.replace('if(ramoops_capture_active()) ramoops_capture_append(255,0,status,4);','(void)status;')
    emi.image.WRAPPER += r'''
void request_no_image(void) {
    setup(1,0,0,0,0);
    request_finish_on(0);request_finish_off();
}
'''
    try:
        return emi.build(root, tree, tree, tree / emi.HIF, True, True)
    finally:
        emi.EXTRA, emi.image.WRAPPER, emi.dma.EXTRA = saved_extra, saved_wrapper, saved_dma


def composed(lib):
    """Only the request/read/image/EMI portion executes in the C fixture.

    Insert synthetic DMA, stop, release and common/provider records to exercise
    the decoder's cross-family joins; these are not native execution evidence.
    """
    _, dma, stop, unbind = request.fixtures.RecordsTests().shutdown_parts()
    rows = []
    for kind, transaction, payload in request.merged(lib):
        subtype = int.from_bytes(payload[:4], 'little')
        if kind == 10 and subtype == 22:
            rows.extend(stop + unbind)
        rows.append((kind, transaction, payload))
        if kind == 7 and subtype == 6 and r.FW_SECTION.unpack(payload)[3] == 0:
            rows.extend(dma)
    return rows


def check(rows, digest):
    sections = [(88 + i * 16, 16, 0x10001000 + i * 0x1000, int(i < 2), i)
                for i in range(4)]
    return r.check_request_firmware(request.pack(rows), CYCLE, digest, 411632, sections)


def tests(lib):
    digests = []
    change_return_task = False

    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p)
    def hash_buffer(data, size, out):
        digest = hashlib.sha256(ctypes.string_at(data, size)).digest()
        digests.append(digest)
        ctypes.memmove(out, digest, 32)
        if change_return_task and len(digests) == 2:
            lib.request_other_task()
        return 0

    lib.set_hash(hash_buffer)

    def run(enabled=1, native=0, io=0, crypto=0, loss=0, fault=0, witness=0):
        digests.clear()
        lib.set_request_fault(fault)
        lib.set_request_loss(loss)
        status = lib.run_case(enabled, io, native, crypto, 0, witness)
        lib.request_finish_off()
        assert lib.request_pins() <= 2
        return status

    def reject():
        try:
            check(composed(lib), digests[0] if digests else bytes(range(32)))
        except ValueError:
            return
        raise AssertionError('invalid request/firmware scope accepted')

    # Preserve native returns and effects for all existing injected EMI paths.
    for native in range(11):
        expected_status = run(enabled=0, native=native)
        expected_effects = emi.image.effects(lib)
        assert not lib.store_count() and not lib.request_pins()
        assert run(native=native) == expected_status
        assert emi.image.effects(lib) == expected_effects
        if native in (0, 5):
            assert check(composed(lib), digests[0])['checked_image'] == 1
            assert lib.request_pins() == 0
        else:
            reject()
    # Restored mutation remains accepted: boundary hashes do not establish
    # which bytes were submitted between the two hashes.
    for io in (1, 2, 3):
        run(io=io); reject()
    for crypto in range(1, 7):
        run(crypto=crypto); reject()
    for loss in (1, 2, 3):
        run(loss=loss); reject()
    for fault in range(1, 10):
        expected_status = run(enabled=0, fault=fault)
        expected_effects = emi.image.effects(lib)
        assert run(fault=fault) == expected_status
        assert emi.image.effects(lib) == expected_effects
        reject()
    for witness in (1, 2, 3, 4):
        run(witness=witness); reject()
    change_return_task = True
    run(); reject()
    change_return_task = False
    lib.set_request_fault(0);lib.request_no_image();reject()
    assert run() == 0
    rows, digest = composed(lib), digests[0]

    def refuse(changed):
        try:
            check(changed, digest)
        except ValueError:
            return
        raise AssertionError('CRC-valid firmware/request mutation accepted')

    for index, (kind, transaction, payload) in enumerate(rows):
        subtype = int.from_bytes(payload[:4], 'little')
        if kind != 10 or subtype not in (25, 26, 27):
            continue
        refuse(rows[:index] + rows[index+1:])
        refuse(rows[:index] + [rows[index]] + rows[index:])
        refuse(rows[:index] + [(kind, transaction+1, payload)] + rows[index+1:])
        refuse(rows[:index] + [(kind, transaction, payload[:-1])] + rows[index+1:])
        layout = r.REQUEST_LAYOUTS[subtype]
        for field in range(1, len(layout.unpack(payload))):
            values = list(layout.unpack(payload)); values[field] += 1
            refuse(rows[:index] + [(kind, transaction, layout.pack(*values))] + rows[index+1:])
    # Each relocated family remains individually well framed and ordered.
    # Move firmware/teardown evidence outside its causal worker interval.
    for selected in ((7, (8, 9, 10, 11)), (7, (5, 6, 7)), (2, (1,)),
                     (2, (2,)), (7, (1, 2, 3, 4)), (10, (25, 26, 27))):
        kind, subtypes = selected
        moved = [row for row in rows if row[0] == kind and
                 int.from_bytes(row[2][:4], 'little') in subtypes]
        rest = [row for row in rows if row not in moved]
        refuse(rest + moved)
    dma = [row for row in rows if row[0] in (3, 4, 5, 6)]
    rest = [row for row in rows if row not in dma]
    off = next(i for i, row in enumerate(rest) if row[0:2] == (10, 2))
    refuse(rest[:off] + dma + rest[off:])
    print('request firmware: 11 native paths preserve effects; task/identity/loss/crypto/read faults and decoder joins passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    args = parser.parse_args()
    required = json.loads((HERE / 'results/emi-capture-sources.json').read_text())['outputs']
    required.update(json.loads((HERE / 'results/request-firmware-sources.json').read_text())['outputs'])
    dma_pins = json.loads((HERE / 'results/dma-capture-sources.json').read_text())['outputs']
    required.update({name: digest for name, digest in dma_pins.items()
                     if Path(name).name in ('hif_capture.c', 'hif_capture.h')})
    for name, digest in required.items():
        assert hashlib.sha256((args.tree / name).read_bytes()).hexdigest() == digest, name
    with tempfile.TemporaryDirectory(prefix='request-firmware-') as directory:
        tests(build(Path(directory), args.tree))


if __name__ == '__main__':
    main()
