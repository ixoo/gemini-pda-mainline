#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native provider/common scope with injected clock dispatch and task identity."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

provider = module('provider_fixture', HERE / 'test-provider-off-capture.py')
core = module('core_fixture', HERE / 'test-common-off-errors.py')
dma, r = provider.dma, provider.r
BASE = provider.BASE
SHIM = r'''
#include <stddef.h>
struct task_struct { int id; };
static struct task_struct main_task, other_task;
static struct task_struct *current;
struct clk_hw { int unused; };
struct clk { struct clk_hw *hw; };
static unsigned int common_lock, scope_fault;
#define DEFINE_RAW_SPINLOCK(name) unsigned int name
#define raw_spin_lock_irqsave(p,f) do { assert(!*(p));*(p)=1;(f)=1;common_lock=1; } while(0)
#define raw_spin_unlock_irqrestore(p,f) do { assert(*(p) && (f)==1);*(p)=0;common_lock=0; } while(0)
#define IS_ERR_OR_NULL(p) (!(p) || (p)==(void *)-1)
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
static struct clk_hw *__clk_get_hw(struct clk *clk) { return clk->hw; }
static void clk_disable_unprepare(struct clk *clk);
void set_scope_fault(unsigned int fault) { scope_fault=fault; }
'''
NO_SCOPE = r'''
void mt6797_wfc_common_off_begin(unsigned int type,int result) { (void)type;(void)result; }
void mt6797_wfc_common_off_end(int power,int result) { (void)power;(void)result; }
static void mt6797_wfc_clock_off_begin(struct clk *clk) { (void)clk; }
static void mt6797_wfc_clock_off_end(void) {}
'''
CLOCK = r'''
static struct mt_power_gate primary_gate={.pd_id=SYS_CONN}, other_gate={.pd_id=SYS_CONN};
static struct clk common_clk={.hw=&primary_gate.hw};
static void clk_disable_unprepare(struct clk *clk) {
    event(0x800);
    if(!clk || scope_fault==1) return;
    if(scope_fault==3) current=&other_task;
    if(scope_fault==9) disable_subsys(SYS_CONN);
    else pg_unprepare(scope_fault==2 ? &other_gate.hw : clk->hw);
    if(scope_fault==4) pg_unprepare(clk->hw);
    current=&main_task;
}
static void common_cycle(void) {
    struct clk *clk=scope_fault==8 ? NULL : &common_clk;
    if(scope_fault!=5) mt6797_wfc_common_off_begin(scope_fault==10 ? 2 : 3,scope_fault==11 ? -5 : 0);
    if(scope_fault==7) mt6797_wfc_common_off_begin(3,0);
    if(scope_fault!=6) mt6797_wfc_clock_off_begin(clk);
    clk_disable_unprepare(clk);
    if(scope_fault!=12) mt6797_wfc_clock_off_end();
    if(scope_fault==15) current=&other_task;
    if(scope_fault!=13) mt6797_wfc_common_off_end(0,scope_fault==11 ? -5 : 0);
    current=&main_task;
    if(scope_fault==14) mt6797_wfc_common_off_begin(3,0);
}
'''


def build(root, tree, linked):
    source = dma.writer.SHIM + dma.without_includes((HERE / 'capture-slot-writer.h').read_text())
    source += provider.SHIM + SHIM
    extra = dma.EXTRA.replace('return wfc_slot_write(&state, kind, tx, p, n);', '''if(kind==9 || kind==10) {
        append_count++;
        if(kind==10) assert(common_lock);
        if(append_count==loss_site) drop=writes+1;
    }
    return wfc_slot_write(&state, kind, tx, p, n);''')
    source += extra
    source += dma.without_includes((tree / BASE / 'clk-mt6797-pg.h').read_text())
    text = (tree / BASE / 'clk-mt6797-pg.c').read_text()
    a = text.index('\tstruct subsys;')
    source += text[a:text.index('/*static struct subsys_ops general_sys_ops;*/', a)]
    source += '#define MT_CCF_BRINGUP 0\n'
    if linked:
        source += dma.without_includes((tree / BASE / 'clk-mt6797-wfc-common.h').read_text())
    else:
        source += NO_SCOPE
    source += dma.without_includes((tree / BASE / 'clk-mt6797-wfc.h').read_text())
    for name in ('spm_topaxi_protect_capture', 'spm_topaxi_protect',
                 'spm_mtcmos_ctrl_conn_capture', 'spm_mtcmos_ctrl_conn',
                 'CONN_sys_disable_op', 'sys_get_state_op'):
        source += provider.fn(text, name)
    source += '''static struct subsys_ops CONN_sys_ops={.disable=CONN_sys_disable_op,.get_state=sys_get_state_op};
static struct subsys syss[NR_SYSS]={[SYS_CONN]={.name="SYS_CONN",.sta_mask=2,.ops=&CONN_sys_ops}};
static struct pg_callbacks *g_pgcb;
static int allow[NR_SYSS];
'''
    source += provider.fn(text, 'id_to_sys') + provider.fn(text, 'disable_subsys')
    a = text.index('struct mt_power_gate {')
    source += text[a:text.index('static int pg_enable', a)]
    source += provider.fn(text, 'pg_disable') + provider.fn(text, 'pg_unprepare') + CLOCK
    reset = 'wfc_off_attempts.counter=0; current=&main_task; common_lock=0;'
    if linked:
        reset += 'wfc_common_lock=0;wfc_common_stage=WFC_COMMON_UNUSED;wfc_common_task=NULL;wfc_common_hw=NULL;'
    source += provider.WRAPPER.replace('FAKE_ARGUMENTS', 'struct subsys *sys, struct wfc_off_trace *capture').replace('FAKE_IGNORE', '(void)capture;').replace('RESET_CAPTURE', reset).replace('int result=disable_subsys(SYS_CONN);', 'common_cycle();int result=0;')
    path = root / 'fixture'
    path.with_suffix('.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-Wno-unused-parameter', '-shared', '-fPIC', str(path.with_suffix('.c')),
                    '-o', str(path.with_suffix('.so'))], check=True)
    lib = ctypes.CDLL(str(path.with_suffix('.so')))
    lib.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    lib.effects.restype = ctypes.POINTER(ctypes.c_uint32)
    return lib


def core_calls(parent, changed, root):
    saved = core.SHIM
    core.SHIM += r'''
static int scope_count, observed_type, observed_callback, observed_power, observed_result;
void mt6797_wfc_common_off_begin(unsigned int type,int result) {
    assert(!scope_count);scope_count=1;observed_type=type;observed_callback=result;
}
void mt6797_wfc_common_off_end(int power,int result) {
    assert(scope_count==1);scope_count=2;observed_power=power;observed_result=result;
}
void reset_scope(void) { scope_count=0; }
int scopes(void) { return scope_count; }
int scope_result(void) { return observed_result; }
int scope_type(void) { return observed_type; }
int scope_callback(void) { return observed_callback; }
int scope_power(void) { return observed_power; }
'''
    libs = [core.build((tree / core.SOURCE).read_text(), root, name)
            for tree, name in ((parent, 'core_parent'), (changed, 'core_changed'))]
    core.SHIM = saved
    before, after = libs
    for mode in range(11):
        for callback in (0, -5, 7):
            for stp in (0, -6, 8):
                for hardware in (0, -7, 9):
                    args = (mode, callback, stp, hardware)
                    after.reset_scope()
                    expected = before.run_case(*args)
                    assert after.run_case(*args) == expected == core.expected(*args, True)
                    assert list(before.get_effects()[:before.effect_count()]) == list(after.get_effects()[:after.effect_count()])
                    assert list(before.get_status()[:11]) == list(after.get_status()[:11])
                    assert after.scopes() == (0 if mode in (1, 3, 7, 8) else 2)
                    if after.scopes():
                        assert after.scope_result() == expected
                        assert after.scope_type() == (9 if mode==10 else 3)
                        assert after.scope_callback() == (-3 if mode==2 else 0 if mode==10 else callback)
                        power = -1 if mode==4 else -2 if mode==5 else hardware if mode==6 else stp or hardware
                        assert after.scope_power() == power


def decoder_refusals(data):
    records = r.decode(data, dma.writer.CYCLE)

    def rejected(rows):
        stream = b''.join(r.encode(row['kind'], i, dma.writer.CYCLE, row['transaction'], row['payload'])
                          for i, row in enumerate(rows))
        try:
            r.check_common_off(stream, dma.writer.CYCLE)
        except ValueError:
            return
        raise AssertionError('accepted mutated common/provider join')

    for index, row in enumerate(records):
        if row['kind'] != 10:
            continue
        for offset in range(0, len(row['payload']), 4):
            payload = bytearray(row['payload'])
            payload[offset] ^= 1
            rejected(records[:index] + [dict(row, payload=bytes(payload))] + records[index+1:])
        rejected(records[:index] + records[index+1:])
        rejected(records[:index] + [dict(row, payload=row['payload']+bytes(4))] + records[index+1:])
    # The provider can be independently valid yet belong to a different scope.
    renamed = []
    for row in records:
        if row['kind'] == 9:
            payload = row['payload'][:4] + (2).to_bytes(4, 'little') + row['payload'][8:]
            row = dict(row, transaction=2, payload=payload)
        renamed.append(row)
    rejected(renamed)
    outside = [records[0]] + [row for row in records if row['kind']==9] + [row for row in records if row['kind']==10] + [records[-1]]
    rejected(outside)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('changed', type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/common-off-capture-sources.json').read_text())
    for key, tree in (('parents', args.parent), ('outputs', args.changed)):
        for name, digest in pins[key].items():
            assert hashlib.sha256((tree / name).read_bytes()).hexdigest() == digest, name
    with tempfile.TemporaryDirectory(prefix='wifi-common-off-') as tmp:
        root = Path(tmp)
        (root/'parent').mkdir();(root/'changed').mkdir()
        parent = build(root/'parent', args.parent, False)
        child = build(root/'changed', args.changed, True)
        for fault in range(16):
            for native in (range(8) if fault==0 else (0,)):
                parent.set_scope_fault(fault);child.set_scope_fault(fault)
                expected = parent.run_case(0,native,0)
                effects = list(parent.effects()[:parent.effect_count()])
                for enabled in (0,1):
                    assert child.run_case(enabled,native,0) == expected
                    assert list(child.effects()[:child.effect_count()]) == effects
                    if not enabled:
                        assert child.store_count()==0
                        continue
                    data, _ = dma.stream(child)
                    if fault==0 and native in (0,5):
                        assert r.check_common_off(data,dma.writer.CYCLE)['checked_common_operation']==1
                        if native==0:
                            decoder_refusals(data)
                    else:
                        try:r.check_common_off(data,dma.writer.CYCLE)
                        except ValueError:pass
                        else:raise AssertionError(('accepted',fault,native))
        parent.set_scope_fault(0);child.set_scope_fault(0)
        expected = parent.run_case(0,0,0)
        effects = list(parent.effects()[:parent.effect_count()])
        for lost in range(1,16):
            assert child.run_case(1,0,lost)==expected
            assert list(child.effects()[:child.effect_count()])==effects
            _, decoded = dma.stream(child)
            assert decoded['framing']=='incomplete'
        core_calls(args.parent,args.changed,root)
    print('common-off-capture=pass provider_paths=8 scope_faults=15 lost_records=15 core_cases=297 decoder_refusals=pass')
    print('native_effects_and_return_values=preserved; real_hardware_clock_or_task_execution=none')


if __name__ == '__main__':
    main()
