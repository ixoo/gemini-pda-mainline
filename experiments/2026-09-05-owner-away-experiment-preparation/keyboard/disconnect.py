#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One harmless no-PTY disconnect proof and one independent evidence export."""
import base64
import json
import os
from pathlib import Path
import re
import runpy
import selectors
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE / 'capture.py'))
L, C, S, P = M['L'], M['C'], M['S'], M['P']
require, sha, encode = M['require'], M['sha'], M['encode']
ROOT = M['ROOT']
REMOTE = '/a53-keyboard-disconnect'
PROBE_PARENT = REMOTE + '/run'
ATTEMPT = PROBE_PARENT + '/keyboard-attempt'
FILES = M['FILES']
LIMITS = M['LIMITS']
MARKER = re.compile(rb'fixture-child=([1-9][0-9]*)\n')
ADMISSION_FIELDS = {'schema', 'id', 'boot_id', 'source_identity', 'dependency',
    'package_identity', 'package_revision', 'monitor_sha256', 'monitor_bytes',
    'probe_sha256', 'probe_bytes', 'custody'}


def execution_gate():
    raise ValueError('keyboard disconnect proof disabled pending exact protocol review')


def prepare(admission, package):
    """Verify the exact candidate/package closure without requiring its future receipt."""
    require(type(admission) is dict and set(admission) == ADMISSION_FIELDS and
        admission['schema'] == 'keyboard-disconnect-admission-v1', 'disconnect admission inventory')
    require(C['UUID'].fullmatch(admission['id']) and C['UUID'].fullmatch(admission['boot_id']), 'UUID')
    require(admission['source_identity'] == M['source_identity'](), 'source drift')
    custody = admission['custody']
    require(set(custody) == {'exclusive', 'no_other_device_operations', 'stable_power',
        'physical_selection', 'screen_readable', 'owner_ready'} and
        all(custody.values()), 'actual disconnect custody facts')
    dependency = L['completed_baseline'](admission['dependency'])
    candidate = dependency['prepared']['candidate']
    require(admission['boot_id'] not in (dependency['first_boot'], dependency['recovered_boot'],
        dependency['prepared']['recovery_id']), 'new admitted mainline boot')
    package = Path(package).absolute()
    runpy.run_path(str(HERE / '../baseline/scripts/buildbox_userspace.py'))['check_package'](
        package, admission['package_identity'], admission['package_revision'])
    manifest = json.loads(C['regular'](package/'manifest.json', 131072, private=False))
    require(manifest.get('production_entry') == 'enabled-admission-v1' and
        manifest.get('inputs', {}).get('monitor.c') == sha((HERE/'monitor.c').read_bytes()),
        'enabled reviewed build required')
    sums = C['regular'](package/'SHA256SUMS', 131072, private=False)
    require(sha(sums) == admission['package_identity'], 'package inventory drift')
    pins = dict((line.split('  ./', 1)[1], line.split('  ./', 1)[0])
                for line in sums.decode('ascii').splitlines())
    monitor = C['regular'](package/'keyboard-monitor', 131072, private=False)
    probe = C['regular'](package/'keyboard-disconnect-probe', 131072, private=False)
    for label, raw in (('monitor', monitor), ('probe', probe)):
        require(admission[label+'_sha256'] == sha(raw) ==
            pins['keyboard-' + ('monitor' if label == 'monitor' else 'disconnect-probe')] and
            admission[label+'_bytes'] == len(raw), 'exact enabled ' + label)
    return {'admission': admission, 'package': package, 'probe': probe, 'pins': pins,
            'dependency': dependency, 'candidate': candidate}


def first_script(context):
    """Deliver only the harmless probe, then retain its outer exit after client loss."""
    a, c, probe = context['admission'], context['candidate'], context['probe']
    text = S['identity_script'](c, a['boot_id']) + S['ram_guard_script']()
    for member in ('bin/dropbear', 'bin/admin-shell'):
        text += f'h=$($BB sha256sum /{member}); [ "${{h%% *}}" = {c["members"][member]["sha256"]} ]\n'
    text += "[ \"$($BB awk '$2 == \"/\" {n++; if (($3 == \"rootfs\" || $3 == \"ramfs\" || $3 == \"tmpfs\") && $4 !~ /(^|,)(ro|noexec)(,|$)/) ok++} END {print n+0 \":\" ok+0}' /proc/mounts)\" = 1:1 ]\n"
    text += f"[ \"$($BB awk '$2 == \"{REMOTE}\" || index($2, \"{REMOTE}/\") == 1 {{n++}} END {{print n+0}}' /proc/mounts)\" = 0 ]\n"
    text += f'[ ! -e {REMOTE} ] && [ ! -L {REMOTE} ]\numask 077\n$BB mkdir -m 700 {REMOTE}\n$BB mkdir -m 700 {PROBE_PARENT}\n'
    text += f"$BB base64 -d >{REMOTE}/probe <<'KEYBOARD_DISCONNECT_PROBE'\n{base64.b64encode(probe).decode()}\nKEYBOARD_DISCONNECT_PROBE\n"
    text += f'[ "$($BB stat -c %u:%g:%a:%s {REMOTE}/probe)" = 0:0:600:{len(probe)} ]\n'
    text += f'h=$($BB sha256sum {REMOTE}/probe); [ "${{h%% *}}" = {sha(probe)} ]\n'
    # The selected fixture child ignores TERM. A monitor-only cancellation is
    # therefore the already-verified bounded TERM/KILL branch; a process-group
    # HUP may instead produce the separately admitted signal-1 branch.
    text += f'$BB chmod 700 {REMOTE}/probe\ntrap \'\' HUP INT TERM\nset +e\n{REMOTE}/probe {PROBE_PARENT} ignore\nstatus=$?\nset -e\n'
    text += f'set -C\n$BB printf "%s\\n" "$status" >{ATTEMPT}/outer-exit\n[ "$status" = 2 ]\n'
    require(len(text.encode()) <= 262144, 'disconnect command ceiling')
    return text.encode()


def export_script(context):
    """Wait for terminal proof, scan all readers, then export four exact members."""
    a, c = context['admission'], context['candidate']
    text = S['identity_script'](c, a['boot_id']) + S['ram_guard_script']()
    text += f'[ -d {REMOTE} ] && [ ! -L {REMOTE} ]\n[ -d {PROBE_PARENT} ] && [ ! -L {PROBE_PARENT} ]\n[ -d {ATTEMPT} ] && [ ! -L {ATTEMPT} ]\n'
    text += f'i=0\nwhile [ ! -e {ATTEMPT}/outer-exit ] && [ ! -L {ATTEMPT}/outer-exit ]; do [ "$i" -lt 20 ]; $BB sleep 0.1; i=$((i+1)); done\n'
    text += f'[ "$($BB cat {ATTEMPT}/outer-exit)" = 2 ]\n'
    text += r'''processes=0
descriptors=0
for proc in /proc/[0-9]*; do
  processes=$((processes+1)); [ "$processes" -le 512 ]
  [ -r "$proc/cmdline" ]; command=$($BB tr '\000' ' ' <"$proc/cmdline")
  case "$command" in */a53-keyboard-disconnect/probe*|*/bin/keyboard-observe*) exit 1;; esac
  if [ -L "$proc/exe" ]; then
    executable=$($BB readlink "$proc/exe")
    case "$executable" in /a53-keyboard-disconnect/probe|/a53-keyboard-disconnect/probe\ \(deleted\)|/bin/keyboard-observe|/bin/keyboard-observe\ \(deleted\)) exit 1;; esac
  fi
  [ -d "$proc/fd" ]
  for fd in "$proc"/fd/*; do
    [ -L "$fd" ] || continue
    descriptors=$((descriptors+1)); [ "$descriptors" -le 4096 ]
    target=$($BB readlink "$fd")
    case "$target" in /dev/tty1|/dev/tty0|/dev/console|/dev/input/*) exit 1;; esac
    device=$($BB stat -Lc '%t:%T' "$fd")
    case "$device" in 4:0|4:1|5:0|5:1|d:*) exit 1;; esac
  done
done
$BB printf 'scan-processes=%s\nscan-descriptors=%s\n' "$processes" "$descriptors"
'''
    for name in FILES:
        path = f'{ATTEMPT}/{name}'
        text += f"$BB printf 'file={name}\\n'\n[ -f {path} ] && [ ! -L {path} ]\n"
        text += f'[ "$($BB stat -c %u:%g:%a:%h {path})" = 0:0:600:1 ]\n[ "$($BB stat -c %s {path})" -le {LIMITS[name]} ]\n'
        text += f"$BB base64 {path}; $BB printf 'end={name}\\n'\n"
    require(len(text.encode()) <= 65536, 'disconnect export command ceiling')
    return text.encode()


def deliberate_disconnect(command, script, directory, timeout=2):
    """Send one complete command, kill its SSH process group immediately on marker."""
    require(0 < timeout <= 2 and len(script) <= 262144, 'disconnect runner bounds')
    directory = Path(directory)
    outputs = {}
    selector = selectors.DefaultSelector()
    process = None
    sent = 0
    counts = {'stdout': 0, 'stderr': 0}
    marker_at = killed_at = None
    marker_stdin_complete = False
    streams_complete = True
    start = time.monotonic()
    try:
        for name in counts:
            fd = os.open(directory/(name+'.txt'), os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
            outputs[name] = os.fdopen(fd, 'wb', buffering=0)
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env={'PATH':'/usr/bin:/bin','LC_ALL':'C'}, start_new_session=True)
        for file, name, event in ((process.stdin,'stdin',selectors.EVENT_WRITE),
                (process.stdout,'stdout',selectors.EVENT_READ),(process.stderr,'stderr',selectors.EVENT_READ)):
            os.set_blocking(file.fileno(), False); selector.register(file,event,name)
        deadline = start + timeout
        stop = False
        while selector.get_map() and time.monotonic() < deadline and not stop:
            for key, _event in selector.select(min(0.02, max(0, deadline-time.monotonic()))):
                name, file = key.data, key.fileobj
                if name == 'stdin':
                    try: sent += os.write(file.fileno(), script[sent:sent+4096])
                    except BlockingIOError: continue
                    except (BrokenPipeError, ConnectionResetError):
                        selector.unregister(file); file.close(); continue
                    if sent == len(script): selector.unregister(file); file.close()
                    continue
                try: raw = os.read(file.fileno(), 4096)
                except BlockingIOError: continue
                if not raw:
                    selector.unregister(file); file.close(); continue
                allowed = max(0, 16384-counts[name])
                outputs[name].write(raw[:allowed]); counts[name] += min(len(raw),allowed)
                if len(raw) > allowed:
                    streams_complete = False
                    try: os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                    stop = True
                    break
                if name == 'stdout' and marker_at is None:
                    current = (directory/'stdout.txt').read_bytes()
                    if MARKER.fullmatch(current):
                        marker_at = time.monotonic()
                        marker_stdin_complete = sent == len(script)
                        # Freeze the command-complete fact at marker time. Do
                        # not let another ready event write stdin after kill.
                        for registered in list(selector.get_map().values()):
                            if registered.data == 'stdin':
                                selector.unregister(registered.fileobj)
                                registered.fileobj.close()
                        os.killpg(process.pid, signal.SIGKILL)
                        killed_at = time.monotonic()
                        stop = True
                        break
            if killed_at is not None and process.poll() is not None:
                break
        if killed_at is None:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        process.wait(timeout=1)
        # Drain bytes already delivered by the killed client.
        for file, name in ((process.stdout,'stdout'),(process.stderr,'stderr')):
            if file.closed: continue
            while True:
                raw = os.read(file.fileno(), 4096)
                if not raw: break
                allowed = max(0,16384-counts[name])
                outputs[name].write(raw[:allowed]); counts[name] += min(len(raw),allowed)
                if len(raw) > allowed: streams_complete = False
        stdout = (directory/'stdout.txt').read_bytes()
        stderr = (directory/'stderr.txt').read_bytes()
        elapsed = None if marker_at is None or killed_at is None else round((killed_at-marker_at)*1000)
        return {'schema':'keyboard-disconnect-transport-v1',
            'classification':'deliberate-client-disconnect' if killed_at is not None else 'inconclusive',
            'connections':1, 'no_pty':True, 'marker_seen':MARKER.fullmatch(stdout) is not None,
            'stdin_complete':marker_stdin_complete, 'client_signal':9 if process.returncode == -9 else 0,
            'elapsed_milliseconds':elapsed, '_stderr_empty':not stderr,
            '_streams_complete':streams_complete}
    finally:
        if process is not None:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            if process.poll() is None: process.wait(timeout=1)
            for file in (process.stdin, process.stdout, process.stderr):
                if file and not file.closed: file.close()
        selector.close()
        for stream in outputs.values():
            os.fsync(stream.fileno()); stream.close()


def parse_export(raw):
    require(len(raw) <= 278528, 'disconnect export bound')
    lines = iter(raw.splitlines())
    values = {}
    for key in ('scan-processes', 'scan-descriptors'):
        line = next(lines, b'').decode('ascii')
        name, sep, value = line.partition('=')
        require(name == key and sep and re.fullmatch(r'0|[1-9][0-9]*', value), 'scan framing')
        values[key] = int(value)
    files = {}
    for name in FILES:
        require(next(lines, None) == ('file='+name).encode(), 'file framing')
        body = []
        for line in lines:
            if line == ('end='+name).encode(): break
            body.append(line)
        else: raise ValueError('truncated disconnect export')
        value = base64.b64decode(b''.join(body), validate=True)
        require(len(value) <= LIMITS[name], 'disconnect member ceiling')
        files[name] = value
    require(next(lines, None) is None, 'disconnect export trailing data')
    require(values['scan-processes'] <= 512 and values['scan-descriptors'] <= 4096, 'scan bound')
    scan = {'schema':'keyboard-reader-release-v1','classification':'passed',
        'processes_scanned':values['scan-processes'],'descriptors_scanned':values['scan-descriptors'],
        'matches':[]}
    return files, scan


def receipt(context, evidence):
    a, c = context['admission'], context['candidate']
    return {'schema':'keyboard-disconnect-v1','classification':'passed','admission_id':a['id'],
        'boot_id':a['boot_id'],'candidate_sha256':c['files']['boot.img'],
        'server':{'binary_sha256':c['members']['bin/dropbear']['sha256'],
            'admin_shell_sha256':c['members']['bin/admin-shell']['sha256'],'no_pty':True,
            'authentication':'exact-candidate-ed25519'},
        'monitor':{'source_sha256':sha((HERE/'monitor.c').read_bytes()),
            'package_identity':a['package_identity'],'package_revision':a['package_revision'],
            'binary_sha256':a['monitor_sha256'],'probe_sha256':a['probe_sha256']},
        'claim':{'count':1,'retained':True},
        'transport':{'first_connection_no_pty':True,'deliberate_disconnect':True,
            'independent_export_connection':True},
        'process':{'monitor_terminal':True,'monitor_reaped':True,'observer_terminal':True,
            'observer_reaped':True,'late':False},
        'preservation':{'members':{name:sha(evidence[name]) for name in FILES},
            'complete_available_members':True,'source_retained':True},
        'reader_release':{'monitor_absent':True,'observer_absent':True,'tty1_reader_absent':True,
            'input_reader_absent':True,'inventory_complete':True},
        'evidence':{name:sha(raw) for name,raw in evidence.items()}}


def perform(context, execute=False):
    if not execute:
        return {'classification':'dry-run','execution':'disabled','connections':0}
    execution_gate()
    context = prepare(context['admission'], context['package'])
    runpy.run_path(str(HERE/'../emmc/mainline_host.py'))['require_ready']()
    root = ROOT/context['admission']['id']/'prerequisites'/'disconnect'
    C['private_root'](root.parent); root.mkdir(mode=0o700)
    C['write_new'](root/'admission.json', encode(context['admission']))
    first = first_script(context); export = export_script(context)
    C['write_new'](root/'disconnect-command.sh', first)
    C['write_new'](root/'export-command.sh', export)
    C['write_new'](root/'claim.json', encode({'claims':1,'connections':2,'retries':0,
        'disconnect_seconds':2,'export_seconds':30,'disconnect_command_sha256':sha(first),
        'export_command_sha256':sha(export)}))
    L['F']['sync_directory'](root); L['F']['sync_directory'](root.parent)
    prepared = context['dependency']['prepared']
    require(sha(C['regular'](prepared['keys']/'known_hosts',8192)) ==
        prepared['candidate']['known_hosts_sha256'], 'host pin drift')
    transport = deliberate_disconnect(C['ssh_command'](prepared['keys']), first, root, 2)
    public_transport = {k:v for k,v in transport.items() if not k.startswith('_')}
    C['write_new'](root/'disconnect-process.json', encode(public_transport))
    export_dir = root/'export-transport'; export_dir.mkdir(mode=0o700)
    process = C['run_once'](C['ssh_command'](prepared['keys']), export, export_dir, 30,
        stdout_limit=278528, stderr_limit=16384)
    C['write_new'](root/'export-process.json', encode(process))
    raw = C['regular'](export_dir/'stdout.txt',278528)
    err = C['regular'](export_dir/'stderr.txt',16384)
    L['process_ok'](raw,err,process,30,278528)
    files, scan = parse_export(raw)
    require(transport['_stderr_empty'] and transport['_streams_complete'] and public_transport == {
        'schema':'keyboard-disconnect-transport-v1','classification':'deliberate-client-disconnect',
        'connections':1,'no_pty':True,'marker_seen':True,'stdin_complete':True,'client_signal':9,
        'elapsed_milliseconds':public_transport['elapsed_milliseconds']} and
        type(public_transport['elapsed_milliseconds']) is int and
        0 <= public_transport['elapsed_milliseconds'] <= 100, 'deliberate disconnect incomplete')
    scan.update(admission_id=context['admission']['id'], boot_id=context['admission']['boot_id'])
    for name,value in files.items(): C['write_new'](root/name,value)
    C['write_new'](root/'reader-scan.json',encode(scan))
    evidence = {name:C['regular'](root/name,98304 if name.startswith('observer.') else 16384)
                for name in P['EVIDENCE']}
    result = receipt(context,evidence)
    raw_receipt = encode(result)
    P['disconnect'](raw_receipt,sha(raw_receipt),context['admission'],context['candidate'],
        context['pins'],root,C['regular'])
    C['write_new'](root/'receipt.json',raw_receipt)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission',type=Path,required=True)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args(); os.umask(0o077)
    try:
        admission = json.loads(C['regular'](args.admission.absolute(),65536))
        context = {'admission':admission,'package':args.package.absolute()}
        result = perform(context,args.execute)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        result = {'classification':'refused','reason':str(error)}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['classification'] in ('dry-run','passed') else 2


if __name__ == '__main__':
    raise SystemExit(main())
