#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the request observer with injected tasks and retained I/O, without hardware."""
import argparse
import ctypes
import hashlib
import json
import importlib.util
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
HEADER = Path('drivers/misc/mediatek/connectivity/common/common_main/core/wmt-request-capture.h')


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


dma = module('request_dma', 'test-dma-capture.py')
fixtures = module('request_records', 'test-capture-records.py')
r = dma.r
CYCLE = dma.writer.CYCLE
SHIM = r'''
#include <assert.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define WMT_OPID_FUNC_ON 3
#define WMT_OPID_FUNC_OFF 4
#define WMTDRV_TYPE_WIFI 3
struct task_struct { unsigned int pins; };
static struct task_struct tasks[3], *current;
static void get_task_struct(struct task_struct *task) { assert(task==current);task->pins++; }
static void put_task_struct(struct task_struct *task) { assert(task==current && task->pins);task->pins--; }
#define DEFINE_RAW_SPINLOCK(name) unsigned int name
#define raw_spin_lock_irqsave(p,f) do { assert(!*(p));*(p)=1;(f)=1; } while(0)
#define raw_spin_unlock_irqrestore(p,f) do { assert(*(p) && (f)==1);*(p)=0; } while(0)
typedef struct { struct { unsigned int opId, au4OpData[1]; } op; } OSAL_OP, *P_OSAL_OP;
static OSAL_OP operations[2];
static unsigned int attempts, loss_site;
'''
WRAPPER = r'''
void fresh(int active, unsigned int loss) {
    /* Fixture initialization models a new boot, not a production reset. */
    memset(memory,0,sizeof(memory));memset(&state,0,sizeof(state));
    memset(tasks,0,sizeof(tasks));memset(operations,0,sizeof(operations));
    reads=writes=barriers=trace_length=cut=drop=fault_read=0;
    wfc_request_lock=0;wfc_request_phase=WFC_REQ_UNUSED;
    wfc_request_root=wfc_request_worker=NULL;wfc_request_op=NULL;
    wfc_request_id=wfc_request_common=attempts=0;loss_site=loss;
    if(active) {
        u8 cycle[16], identity[80];
        for(unsigned int i=0;i<16;i++) cycle[i]=i;
        for(unsigned int i=0;i<80;i++) identity[i]=i;
        assert(!wfc_writer_begin(&state,memory,sizeof(memory),cycle,identity));
    }
}
void event(int kind, unsigned int task, unsigned int op, long long a, int b, int c, int d) {
    assert(task<3 && op<2);current=&tasks[task];
    switch(kind) {
    case 16: mt6797_wfc_request_begin((unsigned long)a);break;
    case 17:
        operations[op].op.opId=a;operations[op].op.au4OpData[0]=b;
        mt6797_wfc_request_bind(&operations[op],a,b,c);break;
    case 18: wfc_request_submit(&operations[op]);break;
    case 19: wfc_request_worker_begin(&operations[op]);break;
    case 20: wfc_request_worker_end(&operations[op],a);break;
    case 21: wfc_request_wait(&operations[op],a,b,c,d);break;
    case 22: mt6797_wfc_request_common_begin();break;
    case 23: mt6797_wfc_request_common_end();break;
    case 24: mt6797_wfc_request_end(a);break;
    case 98: wfc_request_release(&operations[op]);break;
    case 99: wfc_request_reset();break;
    default: assert(0);
    }
}
u8 *data(void) { return memory; }
int phase(void) { return wfc_request_phase; }
unsigned int pins(void) { return tasks[0].pins+tasks[1].pins+tasks[2].pins; }
int bound(void) { return wfc_request_op!=NULL; }
unsigned int store_count(void) { return writes; }
'''


def build(root, tree):
    source = dma.writer.SHIM + SHIM
    source += dma.without_includes((HERE / 'capture-slot-writer.h').read_text())
    source += dma.EXTRA.replace('return wfc_slot_write(&state, kind, tx, p, n);',
                               'if(kind==10 && ++attempts==loss_site) drop=writes+1;\n'
                               'return wfc_slot_write(&state, kind, tx, p, n);')
    source += dma.without_includes((tree / HEADER).read_text()) + WRAPPER
    path = root / 'request.c'
    path.write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-shared', '-fPIC', str(path), '-o', str(root / 'request.so')], check=True)
    lib = ctypes.CDLL(str(root / 'request.so'))
    lib.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    lib.event.argtypes = [ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_longlong,
                          ctypes.c_int, ctypes.c_int, ctypes.c_int]
    return lib


def events():
    rows = []
    for request in (1, 2):
        rows += [(16, 0, 0, 0x80000003 if request == 1 else 3, 0, 0, 0),
                 (17, 0, 0, 3 if request == 1 else 4, 3, 4000, 0),
                 (18, 0, 0, 0, 0, 0, 0), (19, 1, 0, 0, 0, 0, 0)]
        if request == 2:
            rows += [(22, 1, 0, 0, 0, 0, 0), (23, 1, 0, 0, 0, 0, 0)]
        rows += [(20, 1, 0, 0, 0, 0, 0), (21, 0, 0, 10, 1, 0, 1),
                 (24, 0, 0, 0, 0, 0, 0)]
    return rows


def merged(lib):
    # The provider fixture is synthetic: this tests decoder composition, not
    # execution of native ioctl/queue/CCF code or concurrent scheduling.
    lower = []
    common = {1: (1, 1, 3, 0), 2: (2, 1, 1), 3: (3, 1, 1, 1),
              4: (4, 1), 5: (5, 1), 6: (6, 1, 0, 0)}
    for subtype in (1, 2, 3):
        lower.append((10, 1, r.COMMON_OFF_LAYOUTS[subtype].pack(*common[subtype])))
    for layout, values in fixtures.RecordsTests().provider_payloads():
        values[1] = 1
        lower.append((9, 1, layout.pack(*values)))
    for subtype in (4, 5, 6):
        lower.append((10, 1, r.COMMON_OFF_LAYOUTS[subtype].pack(*common[subtype])))
    rows = []
    for row in r.decode_pmsg(bytes(lib.data()[:r.ZONE_PAYLOAD_BYTES]), CYCLE, bytes(range(80)))['records']:
        if row['kind'] == 10 and int.from_bytes(row['payload'][:4], 'little') == 23:
            rows.extend(lower)
        rows.append((row['kind'], row['transaction'], row['payload']))
    return rows


def pack(rows):
    return b''.join(r.encode(kind, seq, CYCLE, tx, payload)
                    for seq, (kind, tx, payload) in enumerate(rows))


def run(lib, sequence, active=True, loss=0):
    lib.fresh(active, loss)
    for row in sequence:
        lib.event(*row)
    assert lib.pins() <= 2


def rejected(lib, sequence, loss=0):
    run(lib, sequence, loss=loss)
    try:
        r.check_request_cycle(pack(merged(lib)), CYCLE)
    except ValueError:
        return
    raise AssertionError('bad request sequence accepted')


def tests(lib):
    good = events()
    run(lib, good)
    assert lib.phase() == 8 and lib.pins() == 0 and not lib.bound()
    rows = merged(lib)
    assert r.check_request_cycle(pack(rows), CYCLE)['checked_requests'] == [1, 2]
    run(lib, good, active=False)
    assert lib.phase() == 0 and not lib.pins() and not lib.store_count()
    # Missing/repeated event and reset at every boundary, including after OFF.
    for index in range(len(good)):
        rejected(lib, good[:index] + good[index+1:])
        rejected(lib, good[:index] + [good[index]] + good[index:])
        rejected(lib, good, loss=index+1)
    for index in range(len(good)+1):
        rejected(lib, good[:index] + [(99, 0, 0, 0, 0, 0, 0)] + good[index:])
    # Final pool release after bind but before waiter completion must invalidate
    # the scope and clear its pointer before native reuse (including PSM failure).
    for index in (2, 3, 4, 5, 9, 10, 11, 12, 13, 14):
        rejected(lib, good[:index] + [(98, 0, 0, 0, 0, 0, 0)] + good[index:])
        assert not lib.bound()
    # Every task-bearing event rejects an unrelated task; all operation-bearing
    # events reject a different operation (zero op ID models an auxiliary op).
    for index, row in enumerate(good):
        changed = list(row);changed[1] = 2
        rejected(lib, good[:index] + [changed] + good[index+1:])
        if row[0] in (17, 18, 19, 20, 21):
            changed = list(row);changed[2] = 1
            rejected(lib, good[:index] + [changed] + good[index+1:])
    for index, field, value in [(0, 3, 3), (0, 3, 0x180000003), (7, 3, 0x100000003),
                                (1, 3, 4), (1, 4, 2), (1, 5, 3999),
                                (4, 3, -5), (5, 3, 0), (5, 3, -1),
                                (5, 4, 0), (5, 5, -5), (5, 6, 0), (6, 3, -14)]:
        changed = list(good[index]);changed[field] = value
        rejected(lib, good[:index] + [changed] + good[index+1:])
    # CRC-valid decoder faults: remove or duplicate every retained scope row,
    # change each request scalar, envelope identity, or payload length.
    def refuse(changed):
        try:
            r.check_request_cycle(pack(changed), CYCLE)
        except ValueError:
            return
        raise AssertionError('CRC-valid mutated stream accepted')
    for index in range(1, len(rows)):
        refuse(rows[:index] + rows[index+1:])
        refuse(rows[:index] + [rows[index]] + rows[index:])
        kind, tx, payload = rows[index]
        subtype = int.from_bytes(payload[:4], 'little')
        if kind == 10 and subtype in r.REQUEST_LAYOUTS:
            refuse(rows[:index] + [(kind, tx+1, payload)] + rows[index+1:])
            refuse(rows[:index] + [(kind, tx, payload+b'\0')] + rows[index+1:])
            layout = r.REQUEST_LAYOUTS[subtype]
            for field in range(1, len(layout.unpack(payload))):
                values = list(layout.unpack(payload))
                values[field] = 0 if subtype == 21 and field == 2 else values[field]+1
                refuse(rows[:index] + [(kind, tx, layout.pack(*values))] + rows[index+1:])
    print('request capture: task/operation identity, event/reset/loss boundaries and typed decoder mutations passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/request-capture-sources.json').read_text())
    for name, expected in pins['outputs'].items():
        assert hashlib.sha256((args.tree / name).read_bytes()).hexdigest() == expected, name
    with tempfile.TemporaryDirectory(prefix='wfc-request-') as directory:
        tests(build(Path(directory), args.tree))


if __name__ == '__main__':
    main()
