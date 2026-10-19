#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P1: separate sustained SSH, completed PID reuse and standard teardown verdicts."""
import importlib.util
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

BASE=load('connected_base',HERE/'classify-ccmp.py')
BASE.RX_MAX,BASE.NATIVE_MAX,BASE.BYTES_MAX=32768,8192,16*1024*1024
RELEASE=load('connected_release_protocol',HERE/'classify-ccmp-channel-release.py')
COUNTER=re.compile(rb'one-shot WLAN checked GTK counters: withheld_arp=(\d+) queued_ptk=(\d+) queued_gtk=(\d+) delivered_arp=(\d+)$')
START=re.compile(rb'one-shot WLAN connected data phase: teardown_margin_ms=5000 no_reuse=1$')
END=RELEASE.BASE.END
ALLOC=re.compile(rb'one-shot WLAN TX slot allocation: pid=(\d+) ordinal=(\d+) reserved=([01]) wraps=(\d+)$')
DONE=re.compile(rb'one-shot WLAN TX slot completion: pid=(\d+) ordinal=(\d+) wraps=(\d+)$')
UNOWNED=re.compile(rb'one-shot WLAN unowned TX completion: pid=(\d+) wlan=(\d+) status=(\d+) count=(\d+)$')
SUMMARY=re.compile(rb'one-shot WLAN TX slot summary: phase=(window|cleanup) allocations=(\d+) completions=(\d+) pending=(\d+) wraps=(\d+) unowned=(\d+)$')


def periodic_probes(raw):
    lines=raw.splitlines()
    matches=[m for line in lines if (m:=RELEASE.PROBE.fullmatch(line))]
    if len(matches)!=11 or sum(line.startswith(b'periodic_ping ') for line in lines)!=11 or any(
            line.startswith(b'periodic_refused ') for line in lines):
        return []
    probes=[]
    for ordinal,m in enumerate(matches,1):
        n,scheduled,start,end=map(int,m.groups()[:4])
        if n!=ordinal or scheduled!=ordinal*10**10 or not scheduled<=start<=end<120*10**9:
            return []
        probes.append({'ordinal':n,'scheduled_offset_ns':scheduled,'start_offset_ns':start,
                       'completion_offset_ns':end,'exit':0,'replies':1,'rtt_ms':float(m[5])})
    return probes


RELEASE.periodic_probes=periodic_probes
read_protocol=RELEASE.read_protocol


def pid_trace(kmsg):
    allocated=completed=reused=reserved=0
    pending=timing=None
    pm_clock=None
    snapshots={}
    tx=[]
    errors=[]
    data_ended=False
    unowned=[]
    def fail(reason):
        if not errors:errors.append(reason)
    for line in kmsg.splitlines():
        if m:=RELEASE.CLOCK.search(line):
            if pm_clock is not None:fail('duplicate PM clock')
            pm_clock=int(m[1])
        if END.search(line):data_ended=True
        if m:=ALLOC.search(line):
            pid,ordinal,is_reserved,wraps=map(int,m.groups())
            if pending or timing:fail('allocation overlaps outstanding completion')
            if is_reserved:
                if pid!=127 or ordinal!=0 or reserved or not data_ended or wraps!=allocated//126:
                    fail('invalid reserved allocation')
                reserved+=1
            else:
                if reserved or ordinal!=allocated+1 or pid!=(ordinal-1)%126+1 or wraps!=ordinal//126:
                    fail('ordinary allocation identity/order')
                allocated+=1
                pending=(pid,ordinal)
        elif m:=DONE.search(line):
            pid,ordinal,wraps=map(int,m.groups())
            if pending!=(pid,ordinal) or ordinal!=completed+1 or wraps!=allocated//126:
                fail('completion does not retire its single owner')
            pending=None
            completed+=1
            reused+=ordinal>126
            if pm_clock is not None:timing=(pid,ordinal)
        elif m:=SUMMARY.search(line):
            phase=m[1].decode();a,c,p,w,u=map(int,m.groups()[1:])
            if phase in snapshots or (a,c,p,w)!=(allocated,completed,pending[0] if pending else 0,allocated//126):
                fail('slot summary contradicts ownership trace')
            if phase=='cleanup' and ('window' not in snapshots or pending or timing):
                fail('cleanup lacks a whole ordinary slot ledger')
            if not 0<=u<=65536:fail('unowned counter exceeds lifetime packet bound')
            if u<len(unowned) or (u<=8 and u!=len(unowned)) or (u>8 and len(unowned)!=8):
                fail('unowned counter contradicts recorded first events')
            if phase=='cleanup' and 'window' in snapshots and u<snapshots['window']['unowned']:
                fail('unowned counter regressed')
            snapshots[phase]={'allocations':a,'completions':c,'pending':p,'wraps':w,'unowned':u}
        elif m:=UNOWNED.search(line):
            pid,wlan,status,count=map(int,m.groups())
            if count!=len(unowned)+1 or count>8 or any(x>255 for x in [pid,wlan,status]):
                fail('invalid unowned completion observation')
            if len(unowned)<8:unowned.append({'pid':pid,'wlan':wlan,'status':status,'count':count})
        elif m:=RELEASE.TX.search(line):
            pid,status,kind,now,offset=map(int,m.groups())
            if pm_clock is None or now-offset!=pm_clock or not 1<=pid<=127 or not (status<=7 or 32<=status<=34) or kind>3:
                fail('invalid TX timing')
            ordinal=None
            if kind in (0,1):
                if timing is None or timing[0]!=pid:fail('TX timing lacks a retired owner')
                else:ordinal=timing[1]
                timing=None
            elif pid!=127 or reserved!=1:
                fail('reserved timing aliases ordinary data')
            tx.append({'pid':pid,'ordinal':ordinal,'status':status,'class':kind,
                       'observed_ns':now,'pm_offset_ns':offset})
        else:
            for prefix,pattern in [(b'one-shot WLAN TX slot allocation:',ALLOC),
                                   (b'one-shot WLAN TX slot completion:',DONE),
                                   (b'one-shot WLAN TX slot summary:',SUMMARY),
                                   (b'one-shot WLAN TX completion timing:',RELEASE.TX),
                                   (b'one-shot WLAN unowned TX completion:',UNOWNED)]:
                if prefix in line and not pattern.search(line):fail('malformed slot/timing record')
    whole=bool(not errors and not pending and not timing and reserved==1 and
               set(snapshots)=={'window','cleanup'} and allocated==completed and
               snapshots['cleanup']['pending']==0)
    return {'trace_valid':not errors,'whole_after_cleanup':whole,'ordinary_allocations':allocated,
            'ordinary_completions':completed,'completed_reuses':reused,'reserved_allocations':reserved,
            'snapshots':snapshots,'tx_completions':tx,'unowned_first_events':unowned,'errors':errors}


def classify(kmsg,ssh_receipt,verified_boot,protocol=None):
    result=BASE.classify(kmsg,ssh_receipt,verified_boot,protocol)
    lines=kmsg.splitlines()
    starts=[m for line in lines if (m:=START.search(line))]
    ends=[m for line in lines if (m:=END.search(line))]
    gtk=[m for line in lines if (m:=COUNTER.search(line))]
    values=list(map(int,gtk[0].groups())) if len(gtk)==1 else None
    gtk_ok=bool(values and sum(b'one-shot WLAN checked GTK counters:' in l for l in lines)==1 and
                values[0]<=32768 and 0<=values[1]<=8192 and 0<=values[2]<=8192 and
                values[3]<=values[2] and values[1]+values[2]==result['ccmp_ethernet_queued'])
    gtk_first=[m for line in lines if (m:=RELEASE.BASE.GTK.search(line))]
    gtk_ok=bool(gtk_ok and len(gtk_first)==sum(b'one-shot WLAN checked GTK RX:' in l for l in lines)==int(values[2]>0) and
                (not gtk_first or 14<int(gtk_first[0][1])<=2352))
    submitted=[m for line in lines if (m:=RELEASE.SUBMIT.search(line))]
    credited=[m for line in lines if (m:=RELEASE.CREDIT.search(line))]
    clocks=[m for line in lines if (m:=RELEASE.CLOCK.search(line))]
    grants=[m for line in lines if (m:=RELEASE.GRANT.search(line))]
    release_ok=False
    if len(submitted)==len(credited)==len(clocks)==len(grants)==1:
        seq,status,now,offset,debt=map(int,submitted[0].groups())
        cseq,cnow,coffset=map(int,credited[0].groups());clock=int(clocks[0][1])
        release_ok=bool(1<=seq==cseq<=253 and status==0 and debt==1 and clock>0 and
                        now-offset==cnow-coffset==clock and 0<cnow-now<=100000000 and
                        0<=offset<coffset<9000000000 and int(grants[0][1])==9000 and
                        sum(b'one-shot WLAN connected channel release:' in l for l in lines)==2 and
                        sum(b'one-shot WLAN PM credit clock:' in l for l in lines)==1 and
                        sum(b'one-shot WLAN join grant:' in l for l in lines)==1)
    trace=pid_trace(kmsg)
    receipt=ssh_receipt or {};stream=receipt.get('p1_stream',{});control=receipt.get('p1_core_disconnect',{})
    remote=receipt.get('p1_remote_stream_quiescence',{})
    stream_ok=bool(stream.get('pass') is True and stream.get('required_stream_ms')==120000 and
                   stream.get('scheduled_stream_ms')==121000 and stream.get('receive_continuity_pass') is True and
                   isinstance(stream.get('host_receive_span_ns'),int) and stream['host_receive_span_ns']>=120000000000 and
                   isinstance(stream.get('host_receive_max_gap_ns'),int) and 0<=stream['host_receive_max_gap_ns']<=3000000000)
    before,after=control.get('before_pm_offset_ns'),control.get('after_pm_offset_ns')
    beacons=[m for line in lines if (m:=re.search(rb'one-shot WLAN data-end beacons: observed_ns=(\d+) count=\d+ known=[01] age_ns=\d+ since_pm_known=[01] since_pm=\d+ interval_tu=\d+$',line))]
    end_offset=int(beacons[0][1])-int(clocks[0][1]) if len(beacons)==len(clocks)==1 else None
    controlled=bool(len(starts)==len(ends)==1 and sum(b'one-shot WLAN connected data phase:' in l for l in lines)==1 and
                    not any(b'one-shot WLAN join data phase: budget_ms=' in l for l in lines) and
                    sum(b'one-shot WLAN join data phase end:' in l for l in lines)==1 and
                    sum(b'one-shot WLAN data-end beacons:' in l for l in lines)==1 and
                    ends[0][1]==b'disconnect' and control.get('kind')=='after_completed_stream' and
                    control.get('accepted') is True and isinstance(before,int) and isinstance(after,int) and isinstance(end_offset,int) and
                    120000000000<=before<=135000000000 and before<=end_offset<=after<=140000000000)
    probes=(protocol or {}).get('periodic_probes') or []
    data_completions=[t for t in trace['tx_completions'] if t['class']==1 and t['status']==0]
    periodic=bool(release_ok and len(probes)==11 and all(p['start_offset_ns']>coffset for p in probes) and
                  data_completions and max(t['pm_offset_ns'] for t in data_completions)>=120000000000)
    controlled=bool(controlled and receipt.get('driver_window_after_client',{}).get('driver_data_window')=='open')
    reserved_done=[t for t in trace['tx_completions'] if t['class']==2]
    ack=bool(sum(b'cleanup: stage=3 credits=returned slots=retired deauth=1' in l for l in lines)==1 and
             len(reserved_done)==1 and reserved_done[0]['pid']==127 and reserved_done[0]['status']==0)
    duration=bool(stream_ok and isinstance(stream.get('host_elapsed_ns'),int) and stream['host_elapsed_ns']>=121000000000)
    passed=bool(result['provisional_ccmp_compatibility_pass'] and gtk_ok and release_ok and periodic and
                duration and controlled and remote.get('quiesced') is True and receipt.get('all_pass') is True and
                trace['whole_after_cleanup'] and trace['completed_reuses']>0 and ack)
    result.update(connected_lifetime_trial_pass=passed,provisional_ccmp_compatibility_pass=passed,
                  duration_pass=duration,required_ssh_stream_ms=120000,scheduled_ssh_stream_ms=121000,
                  gtk_counters_consistent=gtk_ok,gtk_counters=({'withheld_arp':values[0],'queued_ptk':values[1],
                    'queued_gtk':values[2],'delivered_arp':values[3]} if values else None),
                  gtk_handoff_observed=bool(gtk_ok and values[2]>0),
                  connected_channel_release_credited=release_ok,periodic_after_release_pass=periodic,
                  periodic_probes=probes,pid_ownership=trace,ssh_stream=stream,core_disconnect=control,
                  core_disconnect_attributed=controlled,actual_stop_pm_offset_ns=end_offset,
                  actual_window_ms=int(ends[0][2]) if len(ends)==1 else None,
                  window_end_reason=ends[0][1].decode() if len(ends)==1 else None,
                  deauth_acked=ack,remote_stream_quiescence=remote,
                  monitor_loss_reported=any(b'connection loss report: source=monitor once=1' in l for l in lines),
                  hardware_replay_proven=False,key_deletion_proven=False,maintained_wifi_support=False,
                  ten_minute_ssh_proven=False,same_boot_reconnect_proven=False)
    return result
