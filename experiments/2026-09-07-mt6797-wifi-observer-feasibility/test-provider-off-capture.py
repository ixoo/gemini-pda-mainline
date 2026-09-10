#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native provider/CONN/protection execution with injected register and lock effects."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dma_fixture', HERE / 'test-dma-capture.py')
dma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dma)
r = dma.r
BASE = 'drivers/clk/mediatek/'
SHIM = r'''
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include <sys/time.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define STA_POWER_DOWN 0
#define STA_POWER_ON 1
#define SUBSYS_PWR_DOWN 0
#define SUBSYS_PWR_ON 1
#define CHECK_PWR_ST 1
#define CONTROL_LIMIT 1
#define MT_CCF_DEBUG 0
#define TOPAXI_PROTECT_LOCK
#define _TOPAXI_TIMEOUT_CNT_ 20000
#define SPM_PROJECT_CODE 0x0b16
#define CONN_PROT_MASK 0x60000
#define CONN_PWR_STA_MASK 2
#define PWR_ISO 2
#define PWR_CLK_DIS 16
#define PWR_RST_B 1
#define PWR_ON 4
#define PWR_ON_2ND 8
#define POWERON_CONFIG_EN 1
#define INFRA_TOPAXI_PROTECTEN 2
#define INFRA_TOPAXI_PROTECTSTA1 3
#define CONN_PWR_CON 4
#define PWR_STATUS 5
#define PWR_STATUS_2ND 6
#define INFRA_TOPAXI_PROTECTSTA0 7
#define INFRA_BUS_IDLE_STA5 8
static u32 registers[9];
static unsigned int mode, power_writes, primary_reads, secondary_reads, protect_reads;
static unsigned int outer_lock, protection_lock, times, callback_calls;
static u32 native_events[300000];
static unsigned int native_count, append_count, loss_site;
static jmp_buf fault_jump;
static void event(u32 value) { assert(native_count<ARRAY_SIZE(native_events)); native_events[native_count++]=value; }
static u32 read_register(u32 address) {
    u32 value=registers[address];
    if(address==PWR_STATUS || address==PWR_STATUS_2ND) {
        if(power_writes<5) value=(mode==1 || (mode==2 && address==PWR_STATUS_2ND)) ? 0 : 2;
        else if(address==PWR_STATUS) value=primary_reads++<2 ? 2 : 0x100;
        else value=secondary_reads++<1 ? 2 : 0x200;
    }
    if(address==CONN_PWR_CON) value |= 0x1000 * (power_writes+1);
    if(address==INFRA_TOPAXI_PROTECTEN && registers[address]&CONN_PROT_MASK && mode==3) value&=~0x20000;
    if(address==INFRA_TOPAXI_PROTECTSTA1) value=(mode==4 || protect_reads++<2) ? 0 : CONN_PROT_MASK;
    event(0x100|address); event(value); return value;
}
static void write_register(u32 address,u32 value) {
    event(0x200|address); event(value); registers[address]=value;
    if(address==CONN_PWR_CON) power_writes++;
}
#define spm_read(a) read_register(a)
#define clk_readl(a) read_register(a)
#define spm_write(a,v) write_register(a,v)
#define spm_mtcmos_noncpu_lock(f) do { assert(!protection_lock); (f)=1; protection_lock=1; event(0x301); } while(0)
#define spm_mtcmos_noncpu_unlock(f) do { assert(protection_lock && (f)==1); event(0x302); protection_lock=0; } while(0)
#define mtk_clk_lock(f) do { assert(!outer_lock); (f)=2; outer_lock=1; event(0x303); } while(0)
#define mtk_clk_unlock(f) do { assert(outer_lock && (f)==2); event(0x304); outer_lock=0; } while(0)
#define BUG() do { event(0x400); longjmp(fault_jump,1); } while(0)
#define BUG_ON(p) do { if(p) BUG(); } while(0)
#define WARN_ON(p) do { if(p) event(0x401); } while(0)
static void do_gettimeofday(struct timeval *t) { t->tv_sec=0;t->tv_usec=times++;event(0x500); }
static void pr_err(const char *text,...) { (void)text;event(0x501); }
#define pr_debug(...) ((void)0)
void aee_rr_rec_clk(int id,u32 value) { event(0x600|id);event(value); }
static void aee_clk_data_rest(void) { event(0x604); }
static int spm_mtcmos_ctrl_md1(int state) { (void)state;return 0; }
static int spm_mtcmos_ctrl_c2k(int state) { (void)state;return 0; }
'''
WRAPPER = r'''
static void callback(enum subsys_id id) { assert(id==SYS_CONN);callback_calls++;event(0x700); }
static struct pg_callbacks callbacks={ .before_off=callback };
static int fake_disable(FAKE_ARGUMENTS) { (void)sys;FAKE_IGNORE event(0x701);return -5; }
int run_case(int enabled,int native,int lost) {
    mode=native;power_writes=primary_reads=secondary_reads=protect_reads=0;
    outer_lock=protection_lock=times=callback_calls=native_count=append_count=0;loss_site=lost;
    memset(registers,0,sizeof(registers));registers[CONN_PWR_CON]=13;registers[INFRA_TOPAXI_PROTECTEN]=0x80;
    memset(memory,0,sizeof(memory));memset(&state,0,sizeof(state));
    reads=writes=barriers=trace_length=cut=drop=fault_read=0;
    RESET_CAPTURE
    for(unsigned int i=0;i<NR_SYSS;i++) allow[i]=1;
    if(mode==6) allow[SYS_CONN]=0;
    g_pgcb=mode==5 ? &callbacks : NULL;
    CONN_sys_ops.disable=mode==7 ? fake_disable : CONN_sys_disable_op;
    if(enabled) {
        u8 cycle[16],identity[80];
        for(unsigned int i=0;i<16;i++) cycle[i]=i;
        for(unsigned int i=0;i<80;i++) identity[i]=i;
        assert(!wfc_writer_begin(&state,memory,sizeof(memory),cycle,identity));
    }
    if(setjmp(fault_jump)) return -999;
    int result=disable_subsys(SYS_CONN);
    if(ramoops_capture_active()) { u8 done[4]={1,0,0,0};ramoops_capture_append(255,0,done,4); }
    return result;
}
u8 *data(void) { return memory; }
u32 *effects(void) { return native_events; }
unsigned int effect_count(void) { return native_count; }
unsigned int outer_state(void) { return outer_lock; }
unsigned int protect_state(void) { return protection_lock; }
unsigned int store_count(void) { return writes; }
'''


def fn(text, name):
    # Ignore braces in comments and literals without shifting source offsets.
    masked = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                    lambda match: ''.join('\n' if c == '\n' else ' ' for c in match[0]),
                    text, flags=re.S)
    match = re.search(r'\b' + re.escape(name) + r'\([^;{}]*\)\s*\{', masked)
    assert match, name
    begin = masked.rfind('\n', 0, match.start()) + 1
    end, depth = match.end(), 1
    while depth:
        depth += (masked[end] == '{') - (masked[end] == '}')
        end += 1
    return text[begin:end] + '\n'



def build(root, tree, changed, console, skip_ack, bringup):
    source = dma.writer.SHIM + dma.without_includes((HERE / 'capture-slot-writer.h').read_text())
    source += SHIM
    extra = dma.EXTRA
    marker = 'return wfc_slot_write(&state, kind, tx, p, n);'
    assert marker in extra
    extra = extra.replace(marker, '''if(kind==9) {
        append_count++;
        u32 subtype=get_unaligned_le32(p);
        assert(subtype==3 || outer_lock);
        if(append_count==loss_site) drop=writes+1;
    }
    '''+marker)
    source += extra
    source += dma.without_includes((tree / BASE / 'clk-mt6797-pg.h').read_text())
    text = (tree / BASE / 'clk-mt6797-pg.c').read_text()
    a = text.index('\tstruct subsys;')
    b = text.index('/*static struct subsys_ops general_sys_ops;*/', a)
    source += text[a:b]
    source += '#define MT_CCF_BRINGUP '+str(int(bringup))+'\n'
    if console:
        source += '#define CONFIG_MTK_RAM_CONSOLE 1\n'
    if skip_ack:
        source += '#define IGNORE_PWR_ACK 1\n'
    if changed:
        source += dma.without_includes((tree / BASE / 'clk-mt6797-wfc.h').read_text())
        source += fn(text, 'spm_topaxi_protect_capture')
    source += fn(text, 'spm_topaxi_protect')
    if changed:
        source += fn(text, 'spm_mtcmos_ctrl_conn_capture')
    source += fn(text, 'spm_mtcmos_ctrl_conn')
    source += fn(text, 'CONN_sys_disable_op')
    source += fn(text, 'sys_get_state_op')
    source += '''static struct subsys_ops CONN_sys_ops={.disable=CONN_sys_disable_op,.get_state=sys_get_state_op};
static struct subsys syss[NR_SYSS]={[SYS_CONN]={.name="SYS_CONN",.sta_mask=2,.ops=&CONN_sys_ops}};
static struct pg_callbacks *g_pgcb;
static int allow[NR_SYSS];
'''
    source += fn(text, 'id_to_sys') + fn(text, 'disable_subsys')
    source += WRAPPER.replace('FAKE_ARGUMENTS', 'struct subsys *sys'+(', struct wfc_off_trace *capture' if changed else '')) .replace('FAKE_IGNORE', '(void)capture;' if changed else '').replace('RESET_CAPTURE', 'wfc_off_attempts.counter=0;' if changed else '')
    if changed:
        source += r'''
void run_guard(int fault) {
    memset(memory,0,sizeof(memory));memset(&state,0,sizeof(state));
    reads=writes=barriers=trace_length=cut=drop=fault_read=0;
    append_count=loss_site=0;outer_lock=1;protection_lock=0;
    native_count=power_writes=mode=0;wfc_off_attempts.counter=0;
    u8 cycle[16],identity[80];
    for(unsigned int i=0;i<16;i++) cycle[i]=i;
    for(unsigned int i=0;i<80;i++) identity[i]=i;
    assert(!wfc_writer_begin(&state,memory,sizeof(memory),cycle,identity));
    struct wfc_off_trace capture;
    wfc_off_init(&capture,SYS_CONN);
    if(fault==3) wfc_off_init(&capture,SYS_CONN);
    else {
        capture.primary_count=~(u64)0;
        if(fault==2) capture.secondary_count=~(u64)0;
        assert(wfc_off_condition(&capture,fault==2)==2);
    }
    assert(!capture.transaction);
}
'''
    path = root / ('changed' if changed else 'parent')
    path.with_suffix('.c').write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-Wno-unused-parameter', '-fPIC', '-shared', str(path.with_suffix('.c')),
                    '-o', str(path.with_suffix('.so'))], check=True)
    library = ctypes.CDLL(str(path.with_suffix('.so')))
    library.data.restype = ctypes.POINTER(ctypes.c_ubyte)
    library.effects.restype = ctypes.POINTER(ctypes.c_uint32)
    return library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('changed', type=Path)
    args = parser.parse_args()
    pins = json.loads((HERE / 'results/provider-off-capture-sources.json').read_text())
    for section, tree in (('parents', args.parent), ('outputs', args.changed)):
        for name, digest in pins[section].items():
            assert hashlib.sha256((tree / name).read_bytes()).hexdigest()==digest, name
    with tempfile.TemporaryDirectory(prefix='wifi-off-capture-') as tmp:
        for console, skip_ack, bringup in ((False,False,False),(True,False,False),(False,True,False),(False,False,True)):
            directory=Path(tmp)/str((console,skip_ack,bringup));directory.mkdir()
            parent=build(directory,args.parent,False,console,skip_ack,bringup)
            child=build(directory,args.changed,True,console,skip_ack,bringup)
            for native in range(8):
                expected=parent.run_case(0,native,0)
                effects=list(parent.effects()[:parent.effect_count()])
                for enabled in (0,1):
                    assert child.run_case(enabled,native,0)==expected,(console,skip_ack,bringup,native)
                    assert list(child.effects()[:child.effect_count()])==effects
                    assert (child.outer_state(),child.protect_state())==(parent.outer_state(),parent.protect_state())
                    if not enabled:
                        assert child.store_count()==0
                        continue
                    data,decoded=dma.stream(child)
                    if native in (0,5) and not skip_ack and not bringup:
                        assert r.check_provider_off(data,dma.writer.CYCLE)['checked_provider_operations']==[1]
                        rows=[row for row in decoded['records'] if row['kind']==9]
                        poll=r.OFF_POLL.unpack(rows[-2]['payload'])
                        assert poll[3]>poll[4]>0
                    else:
                        try:r.check_provider_off(data,dma.writer.CYCLE)
                        except ValueError:pass
                        else:raise AssertionError('accepted incomplete or nonnormal provider')
            if not skip_ack and not bringup:
                expected=parent.run_case(0,0,0)
                effects=list(parent.effects()[:parent.effect_count()])
                for lost in range(1,10):
                    assert child.run_case(1,0,lost)==expected
                    assert list(child.effects()[:child.effect_count()])==effects
                    _,decoded=dma.stream(child)
                    assert decoded['framing']=='incomplete',lost
            for fault in (1,2,3):
                child.run_guard(fault)
                _,decoded=dma.stream(child)
                assert decoded['producer_status']==2
                if fault!=3:
                    row=next(row for row in decoded['records'] if row['kind']==9)
                    assert r.OFF_POLL.unpack(row['payload'])[2]==3
    print('provider-off-capture=pass native_paths=8 capture_states=2 configurations=4 lost_records=9 guards=3')
    print('native_register_lock_callback_effects_and_returns=preserved')
    print('no_real_hardware_provider_power_or_device_execution')


if __name__=='__main__':
    main()
