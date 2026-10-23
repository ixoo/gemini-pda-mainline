#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One owned, bounded, two-direction measurement; no driver/firmware changes."""
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import socket
import subprocess
import sys
import threading
import time

DURATION = 1
CHUNKS = 5
MAX_BYTES = 1024 * 1024
SSH_IDLE_SECONDS = 30


class Endpoint:
    def __init__(self, address, port, peer, sending, duration=DURATION, maximum=MAX_BYTES, chunks=1):
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((address, port))
        self.socket.listen(1)
        self.socket.settimeout(0.2)
        self.peer, self.sending = peer, sending
        self.duration, self.maximum = duration, maximum
        self.chunks = chunks
        self.result = {'bytes': 0, 'errors': 0, 'completed': False, 'chunks': []}
        self.cancel = threading.Event()
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def work(self):
        start = None
        try:
            for ordinal in range(1,self.chunks+1):
                deadline = time.monotonic() + 80
                connection = None
                while not self.cancel.is_set() and time.monotonic() < deadline:
                    try:
                        connection = self.socket.accept()[0]
                        break
                    except socket.timeout:
                        continue
                if connection is None:
                    if self.cancel.is_set(): return
                    raise TimeoutError('measurement accept deadline')
                with connection:
                    if connection.getpeername()[0] != self.peer:
                        raise ValueError('unexpected measurement peer')
                    chunk_start = time.monotonic_ns()
                    if start is None: start = chunk_start
                    end = chunk_start + int(self.duration * 1e9)
                    count = 0
                    reason = 'duration'
                    block = bytes(65536)
                    while not self.cancel.is_set() and time.monotonic_ns() < end:
                        if count >= self.maximum: break
                        try:
                            connection.settimeout(max(0.001,min(0.05,(end-time.monotonic_ns())/1e9)))
                            if self.sending:
                                amount = connection.send(block[:min(len(block), self.maximum-count)])
                            else:
                                data = connection.recv(min(len(block), self.maximum-count))
                                amount = len(data)
                                if any(data): raise ValueError('nonzero measurement payload')
                            if not amount:
                                reason = 'peer_eof'
                                break
                            count += amount
                            self.result['bytes'] += amount
                        except socket.timeout:
                            continue
                        except (BrokenPipeError,ConnectionResetError) as error:
                            # The other end has its own bounded nc lifetime.
                            # Its SSH progress/status must independently agree.
                            reason = type(error).__name__
                            break
                    elapsed = time.monotonic_ns()-chunk_start
                    self.result['chunks'].append({'ordinal':ordinal,'bytes':count,
                        'elapsed_ns':elapsed,'Mbit_s':count*8000/elapsed,
                        'ended_by':'byte_cap' if count>=self.maximum else reason})
                    self.result['known_size_complete'] = count==self.maximum
                    if self.cancel.is_set(): return
                    if not count: raise ValueError('empty chunk; later traffic withheld')
            self.result['completed'] = True
        except Exception as error:
            if not self.cancel.is_set():
                self.result.update(errors=1, error=type(error).__name__)
        finally:
            if start is not None:
                elapsed = time.monotonic_ns() - start
                self.result['elapsed_ns'] = elapsed
                self.result['Mbit_s'] = self.result['bytes'] * 8000 / elapsed if elapsed else None
            self.socket.close()

    def close(self):
        self.cancel.set()
        self.socket.close()
        self.thread.join(1)
        if self.thread.is_alive():
            self.result['owner_quiescent'] = False
        else:
            self.result['owner_quiescent'] = True


def remote_script(boot, host):
    # One PTY process group; the existing owner scanner checks this exact tag.
    script = r'''
# shellcheck disable=SC2016 # awk programs intentionally use literal field references
BB=/bin/busybox
[ -t 0 ] && [ -t 1 ] && [ -t 2 ] || exit 30
owner=$$
# shellcheck disable=SC2046 # split the trusted kernel proc-stat field tail
set -- $($BB sed 's/^.*) //' /proc/$$/stat)
[ "$3" = "$owner" ] && [ "$4" = "$owner" ] && [ "$6" = "$owner" ] || exit 31
trap 'trap - HUP TERM; kill -TERM 0; exit 32' HUP TERM
printf 'TP1_OWNER_PID=%s\n' "$owner"
[ "$(cat /proc/sys/kernel/random/boot_id)" = BOOT ] || exit 33
p=$(dmesg | $BB awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); c++}} END {if(c==1) print v; else exit 1}') || exit 36
n=$($BB awk '{printf "%.0f\n", $1*1000000000}' /proc/uptime)
[ "$n" -ge "$p" ] && [ "$((n-p))" -le 5000000000 ] || exit 37
cpu() { $BB head -n 1 /proc/stat; }
stats() { for k in rx_packets tx_packets rx_errors tx_errors rx_dropped tx_dropped; do printf '%s=' "$k"; $BB cat /sys/class/net/wlan0/statistics/$k | $BB tr '\n' ' '; done; printf '\n'; }
clock() { $BB awk '{printf "%.0f\n", $1*1000000000}' /proc/uptime; }
trap 'printf "TP1_END_NS="; clock' EXIT
for dir in TX RX; do
    printf 'TP1_%s_CPU_BEFORE ' "$dir"; cpu
    printf 'TP1_%s_STATS_BEFORE ' "$dir"; stats
    printf 'TP1_%s_START_NS=' "$dir"; clock
    i=1; total=0; rc=0
    while [ "$i" -le 5 ]; do
        printf 'TP2_PROGRESS direction=%s chunk=%s phase=start ns=' "$dir" "$i"; clock
        rc=0; n=unknown
        if [ "$dir" = TX ]; then
            $BB dd if=/dev/zero bs=65536 count=16 2>/tmp/tp2-dd.log | $BB timeout 1 $BB nc HOST 48001 || rc=$?
        else
            # shellcheck disable=SC3040 # pinned BusyBox ash supports pipefail
            n=$(set -o pipefail; $BB timeout 1 $BB nc HOST 48002 | $BB wc -c) || rc=$?
            n=$((n+0))
            total=$((total+n))
            [ "$n" -gt 0 ] || exit 39
        fi
        printf 'TP2_PROGRESS direction=%s chunk=%s phase=end rc=%s bytes=%s ns=' "$dir" "$i" "$rc" "$n"; clock
        case "$rc" in 0|124|143) ;; *) exit 38;; esac
        d=$(dmesg)
        if printf '%s' "$d" | $BB grep -Eq 'one-shot WLAN join (stopped:|rearm refused:|rearm wrap:|data phase end:)'; then exit 34; fi
        [ "$i" = 5 ] || $BB sleep 0.1
        i=$((i+1))
    done
    [ "$dir" != RX ] || printf 'TP1_RX_BYTES=%s\n' "$total"
    printf 'TP1_%s_RC=%s\n' "$dir" "$rc"
    printf 'TP1_%s_CPU_AFTER ' "$dir"; cpu
    printf 'TP1_%s_STATS_AFTER ' "$dir"; stats
    printf 'TP1_%s_END_NS=' "$dir"; clock
    [ "$(cat /proc/sys/kernel/random/boot_id)" = BOOT ] || exit 35
done
'''.replace('BOOT', shlex.quote(boot)).replace('HOST', shlex.quote(host))
    return script


def validate_idle_safety(script, idle=SSH_IDLE_SECONDS):
    """Validate this concrete chunk loop before submitting it, not arbitrary shell."""
    bounds = [int(n) for n in re.findall(r'\$BB timeout ([0-9]+)',script)]
    if (len(bounds)!=2 or max(bounds)+2>=idle or
        script.count('TP2_PROGRESS direction=%s chunk=%s phase=start')!=1 or
        script.count('TP2_PROGRESS direction=%s chunk=%s phase=end')!=1 or
        'while [ "$i" -le 5 ]' not in script):
        raise ValueError('planned command can exceed SSH idle policy without progress')
    return {'idle_seconds':idle,'maximum_transfer_silence_seconds':max(bounds),
            'progress_margin_seconds':2,'server_alive_interval_seconds':5}


def validate_receive_safety(script, regular_file_limit=131072):
    # This is the concrete planned nc command, not a general shell validator.
    sinks = re.findall(r'\bnc [^\n|]*>\s*(\S+)',script)
    if MAX_BYTES>regular_file_limit and any(s!='/dev/null' for s in sinks):
        raise ValueError('planned RX payload write exceeds inherited file limit')
    return {'maximum_chunk_bytes':MAX_BYTES,'regular_file_limit_bytes':regular_file_limit,
            'regular_payload_file':bool(sinks)}


def cpu_result(output, direction):
    result = {}
    rows = []
    for phase in ('BEFORE', 'AFTER'):
        match = re.search(rb'^TP1_' + direction.encode() + b'_CPU_' + phase.encode() + rb' cpu +([0-9 ]+)\r?$', output, re.M)
        if not match:
            return {'valid': False}
        rows.append([int(x) for x in match[1].split()][:8])
    if len(rows[0]) != 8 or len(rows[1]) != 8:
        return {'valid': False}
    delta = [b-a for a,b in zip(*rows)]
    total = sum(delta)
    if min(delta) < 0 or total <= 0:
        return {'valid': False}
    result.update(valid=True, total_ticks=total, idle_ticks=delta[3], iowait_ticks=delta[4],
                  idle_percent=100*delta[3]/total, iowait_percent=100*delta[4]/total)
    return result


def device_chunks(output, direction):
    starts, ends = {}, {}
    prefix=rb'^TP2_PROGRESS direction='+direction.encode()+rb' chunk=([1-5]) '
    for match in re.finditer(prefix+rb'phase=start ns=([0-9]+)\r?$',output,re.M):
        ordinal=int(match[1])
        if ordinal in starts: return {}
        starts[ordinal]=int(match[2])
    for match in re.finditer(prefix+rb'phase=end rc=([0-9]+) bytes=(unknown|[0-9]+) ns=([0-9]+)\r?$',output,re.M):
        ordinal=int(match[1])
        if ordinal in ends or ordinal not in starts: return {}
        elapsed=int(match[4])-starts[ordinal]
        count=None if match[3]==b'unknown' else int(match[3])
        ends[ordinal]={'device_elapsed_ns':elapsed,'device_exit':int(match[2]),
                       'device_received_bytes':count,
                       'device_Mbit_s':count*8000/elapsed if count is not None and elapsed>0 else None}
    return ends


def execute(root, keys, boot, cycles, poll):
    if cycles != 1 or poll != 710:
        raise ValueError('measurement requires one cycle and retained host bounds')
    cohort = Path(os.environ['TP_SOURCE_ROOT'])
    origin = runpy.run_path(str(cohort/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe/laptop-wifi-ssh-connected-p2e.py'))
    g = origin['run'].__globals__
    M, R = g['M'], g['R']
    started = time.monotonic()
    endpoints = []
    measured = {}
    captured = {}
    original_command = M.COMMAND

    def invoke(argv, **kwargs):
        if not any(x.startswith('HostKeyAlias=') for x in argv):
            if 'DATA_ENDED=' in argv[-1]:
                suffix = "; printf 'P2_PM_NS=%s\\n' \"$(printf '%s\\n' \"$d\" | /bin/busybox awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}')\"; printf 'P2_NOW_NS=%s\\n' \"$(/bin/busybox awk '{printf \"%.0f\\n\",$1*1000000000}' /proc/uptime)\""
                argv = [*argv[:-1],argv[-1]+suffix]
                kwargs = {**kwargs, 'timeout': 15}
                response = subprocess.run(argv,**kwargs)
                captured.update(fields=M.parse_block(response.stdout.decode('ascii','replace')),returned=time.monotonic())
                return response
            return subprocess.run(argv, **kwargs)
        if endpoints:
            raise ValueError('measurement Wi-Fi acquisition already consumed')
        peer = argv[-2].removeprefix('root@')
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.connect((peer, 9))  # local route selection; sends no datagram
            host = route.getsockname()[0]
        endpoints.append(Endpoint(host,48001,peer,False,chunks=CHUNKS))
        endpoints.append(Endpoint(host,48002,peer,True,chunks=CHUNKS))
        script = remote_script(boot, host)
        validate_idle_safety(script)
        validate_receive_safety(script)
        tag = 'TP1_OWNER_'+boot
        addition = '; exec /bin/busybox timeout 135 /bin/busybox sh -c ' + shlex.quote(script) + ' ' + shlex.quote(tag)
        command = argv[-1] + addition
        if len(command.encode()) > 4096:
            raise ValueError('measurement exceeds retained owner-observation bound')
        argv = [argv[0],'-o','ServerAliveInterval=5','-o','ServerAliveCountMax=3',*['-tt' if x == '-T' else x for x in argv[1:-1]],command]
        return g['held_stdin_runner'](argv, **kwargs)

    try:
        result = R.run(root,keys,boot,cycles,poll,runner=invoke)
    finally:
        M.COMMAND = original_command
        for endpoint in endpoints:
            endpoint.close()
    output = (root/'stdout.bin').read_bytes() if (root/'stdout.bin').exists() else b''
    for label, endpoint in zip(('TX','RX'),endpoints):
        measured[label] = {**endpoint.result, 'device_cpu':cpu_result(output,label)}
        progress=device_chunks(output,label)
        measured[label]['chunk_progress_valid']=len(progress)==CHUNKS
        for chunk in measured[label].get('chunks',[]):
            chunk.update(progress.get(chunk['ordinal'],{}))
            if label=='RX':
                chunk.update(host_sent_bytes=chunk.pop('bytes'),
                             host_elapsed_ns=chunk.pop('elapsed_ns'),
                             host_Mbit_s=chunk.pop('Mbit_s'),host_ended_by=chunk.pop('ended_by'))
                chunk.update(bytes=chunk.get('device_received_bytes'),
                             elapsed_ns=chunk.get('device_elapsed_ns'),
                             Mbit_s=chunk.get('device_Mbit_s'),
                             ended_by='device_timeout' if chunk.get('device_exit') in (124,143) else
                                      'byte_cap' if chunk.get('device_received_bytes')==MAX_BYTES else 'peer_eof')
        counters = []
        for phase in ('BEFORE','AFTER'):
            stats = re.search(rb'^TP1_'+label.encode()+b'_STATS_'+phase.encode()+rb' ([^\r\n]+)',output,re.M)
            counters.append({k.decode():int(v) for k,v in re.findall(rb'([a-z_]+)=([0-9]+)',stats[1])} if stats else {})
        if counters[0] and counters[0].keys()==counters[1].keys():
            measured[label]['netdev_delta'] = {k:counters[1][k]-v for k,v in counters[0].items()}
        for phase in ('START','END'):
            stamp = re.search(rb'^TP1_'+label.encode()+b'_'+phase.encode()+rb'_NS=([0-9]+)\r?$',output,re.M)
            measured[label]['device_'+phase.lower()+'_ns'] = int(stamp[1]) if stamp else None
        rc = re.search(rb'^TP1_'+label.encode()+rb'_RC=([0-9]+)\r?$',output,re.M)
        measured[label]['device_pipeline_exit'] = int(rc[1]) if rc else None
        measured[label]['expected_termination'] = measured[label]['device_pipeline_exit'] in (0,124,143)
        measured[label]['host_count_scope'] = 'received' if label=='TX' else 'sent'
        if label=='RX':
            count = re.search(rb'^TP1_RX_BYTES=([0-9]+)\r?$',output,re.M)
            delivered = int(count[1]) if count else None
            measured[label]['device_received_bytes'] = delivered
            start_ns,end_ns = measured[label].get('device_start_ns'),measured[label].get('device_end_ns')
            measured[label]['device_Mbit_s'] = delivered*8000/(end_ns-start_ns) if delivered is not None and start_ns is not None and end_ns is not None and end_ns>start_ns else None
            measured[label].update(host_sent_bytes=measured[label]['bytes'],
                                   host_elapsed_ns=measured[label].get('elapsed_ns'),
                                   host_Mbit_s=measured[label].get('Mbit_s'),bytes=delivered,
                                   elapsed_ns=end_ns-start_ns if end_ns is not None and start_ns is not None else None,
                                   Mbit_s=measured[label]['device_Mbit_s'])
    # Reuse the finite read-only owner check; never infer quiescence from SSH exit.
    original_argument = g['remote_quiescence_argument']
    owner = re.search(rb'^TP1_OWNER_PID=([1-9][0-9]*)\r?$',output,re.M)
    def argument(b):
        script = original_argument(b).replace('P2_STREAM_OWNER_', 'TP1_OWNER_')
        if owner is None:
            return script.replace('owners=0', 'owners=1')
        group_check = r'''nstat=0
for f in /proc/[0-9]*/stat; do
    [ -e "$f" ] || continue
    nstat=$((nstat+1)); [ "$nstat" -le 512 ] || exit 67
    v=$($BB cat "$f" 2>/dev/null) || { [ ! -e "$f" ] && continue; exit 68; }
    v=${v##*) }
    set -- $v
    [ "$#" -ge 4 ] || exit 69
    if [ "$3" = OWNER_PID ] || [ "$4" = OWNER_PID ]; then owners=$((owners+1)); fi
done
'''.replace('OWNER_PID',str(int(owner[1])))
        return script.replace("printf 'P2_REMOTE",group_check+"printf 'P2_REMOTE")
    g['remote_quiescence_argument'] = argument
    remote = g['remote_quiescence'](root,keys,boot,result,captured,started+poll,subprocess.run,time.monotonic,time.sleep)
    if any(not endpoint.result.get('owner_quiescent') for endpoint in endpoints):
        remote.update(quiesced=False, reason='local measurement endpoint not quiescent')
    remote['scope'] = 'exact tagged owner and observed PTY process group/session absent; bounded proc scans'
    result['p2_remote_stream_quiescence'] = remote
    control = {'attempted':False,'accepted':False}
    if remote['quiesced'] and result.get('driver_window_after_client',{}).get('driver_data_window') == 'open':
        fields = captured.get('fields',{})
        end = re.search(rb'^TP1_END_NS=([0-9]+)\r?$',output,re.M)
        latest = remote.get('queries',[{}])[-1]
        if re.fullmatch(r'[1-9][0-9]*',fields.get('P2_PM_NS','')) and latest.get('pm_offset_ns') is not None:
            pm = int(fields['P2_PM_NS'])
            now = pm+int(latest['pm_offset_ns'])
            # Observed EOS: all tagged owners/endpoints are already absent.
            # This USB observation also permits prompt cleanup after SSH fails.
            eos = int(end[1]) if end else now
            control['eos_source'] = 'remote_end' if end else 'quiescence_observed'
            lower, upper = eos-pm, eos-pm+30_000_000_000
            if 0 < pm <= eos <= now <= eos+15_000_000_000:
                command = g['disconnect_argument'](boot,pm,True).replace('6000000000',str(lower)).replace('608000000000',str(upper))
                control.update(attempted=True,interval_ns=[lower,upper])
                response = subprocess.run(M.usb_command(keys,command),capture_output=True,timeout=15)
                (root.parent/'core-disconnect.stdout').write_bytes(response.stdout)
                (root.parent/'core-disconnect.stderr').write_bytes(response.stderr)
                before = re.search(rb'before_pm_offset_ns=([0-9]+)',response.stdout)
                after = re.search(rb'after_pm_offset_ns=([0-9]+) reply_ok=1',response.stdout)
                control.update(exit=response.returncode,accepted=bool(response.returncode==0 and before and after and lower<=int(before[1])<=upper and int(before[1])<=int(after[1])<=upper+5_000_000_000))
    result['throughput_measurement'] = {'directions':measured,'seconds_each':DURATION*CHUNKS,'seconds_per_chunk':DURATION,'gap_seconds':0.1,'chunks_each':CHUNKS,'maximum_bytes_each':MAX_BYTES*CHUNKS,'core_disconnect':control,'new_build':True,'data_path':'plain nc TCP; SSH control/progress only'}
    counter_names = {'rx_packets','tx_packets','rx_errors','tx_errors','rx_dropped','tx_dropped'}
    directions_ok = bool(len(measured)==2 and
                         (measured.get('RX',{}).get('device_received_bytes') or 0)>0)
    for direction in measured.values():
        directions_ok = bool(directions_ok and direction.get('completed') and
                             not direction['errors'] and direction['expected_termination'] and
                             direction['device_cpu']['valid'] and direction['bytes']>0 and len(direction.get('chunks',[]))==CHUNKS and
                             direction['chunk_progress_valid'] and
                             all(c.get('device_exit') in (0,124,143) for c in direction['chunks']) and
                             set(direction.get('netdev_delta',{}))==counter_names and
                             min(direction['netdev_delta'].values())>=0)
    result['all_pass'] = bool(result['all_pass'] and remote['quiesced'] and
                              control['accepted'] and directions_ok)
    return result


def main():
    # Retain the reviewed CLI/key/receipt/owned-helper exception machinery.
    cohort = Path(os.environ['TP_SOURCE_ROOT'])
    module = runpy.run_path(str(cohort/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe/laptop-wifi-ssh-connected-p2e.py'))
    module['main'].__globals__['SESSION'] = 'session-throughput-pump-1'
    module['main'].__globals__['run'] = execute
    return module['main']()


if __name__ == '__main__':
    raise SystemExit(main())
