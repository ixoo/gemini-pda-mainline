#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One admitted keyboard capture and separate complete private export."""
import base64
import json
from pathlib import Path
import re
import runpy
import shlex

HERE = Path(__file__).resolve().parent
L = runpy.run_path(str(HERE / '../emmc/collect-emmc.py'))
C, S = L['C'], L['S']
K = runpy.run_path(str(HERE / 'classify.py'))
require = L['require']
sha = L['sha']
encode = L['json_bytes']
ROOT = L['REPO'] / 'artifacts/a53-authenticated/keyboard-capture'
FILES = ('observer.stdout', 'observer.stderr', 'monitor.status', 'outer-exit')
LIMITS = {'observer.stdout': 98304, 'observer.stderr': 98304, 'monitor.status': 4096, 'outer-exit': 16}


def execution_gate():
    raise ValueError('keyboard capture/export disabled pending complete source and target review')


def source_identity():
    launcher = L['source_identity']()  # Checks the exact selected eMMC closure.
    members = json.loads(C['regular'](HERE/'../emmc/source-pins.json',16384,private=False),object_pairs_hook=L['unique'])
    closure = {'experiments/2026-09-05-owner-away-experiment-preparation/'+name: value
               for name,value in members.items()}
    closure.update(dict(L['V']['SOURCE_PINS']))
    for name,value in closure.items():
        require(sha(C['regular'](L['REPO']/name,262144,private=False)) == value, 'imported closure drift')
    direct = ('capture.py','monitor.c','delivery.py','classify.py','protocol.json',
              '../emmc/mainline_host.py','../baseline/scripts/buildbox_userspace.py')
    return {'local_and_direct':{name:sha(C['regular'](HERE/name,262144,private=False)) for name in direct},
            'emmc_launcher':launcher,'pinned_members':closure}


def prepare(admission, package):
    """Admitted values are exact pins; unknown runtime facts cannot be defaults."""
    require(set(admission) == {'id', 'source_identity', 'dependency', 'boot_id', 'expected',
        'package_identity', 'package_revision', 'monitor_sha256', 'monitor_bytes', 'runtime',
        'custody', 'full_duration_receipt_sha256', 'disconnect_receipt_sha256'}, 'admission inventory')
    require(C['UUID'].fullmatch(admission['id']) and C['UUID'].fullmatch(admission['boot_id']), 'UUID')
    require(admission['source_identity'] == source_identity(), 'source drift')
    for key in ('package_identity', 'monitor_sha256', 'full_duration_receipt_sha256', 'disconnect_receipt_sha256'):
        require(type(admission[key]) is str and C['SHA'].fullmatch(admission[key]), 'missing reviewed ' + key)
    custody = admission['custody']
    require(set(custody) == {'exclusive', 'no_other_device_operations', 'stable_power', 'physical_selection',
        'screen_readable', 'owner_ready', 'receipt_sha256'} and
        all(custody[k] is True for k in custody if k != 'receipt_sha256') and
        C['SHA'].fullmatch(custody['receipt_sha256']), 'actual owner/custody facts')
    dependency = L['completed_baseline'](admission['dependency'])
    require(admission['boot_id'] not in (dependency['first_boot'], dependency['recovered_boot'],
        dependency['prepared']['recovery_id']), 'new admitted mainline boot')
    candidate = dependency['prepared']['candidate']
    package = Path(package).absolute()
    runpy.run_path(str(HERE / '../baseline/scripts/buildbox_userspace.py'))['check_package'](
        package, admission['package_identity'], admission['package_revision'])
    manifest = json.loads((package / 'manifest.json').read_bytes())
    require(manifest.get('production_entry') == 'enabled-admission-v1' and
        manifest.get('inputs', {}).get('monitor.c') == sha((HERE/'monitor.c').read_bytes()), 'enabled reviewed build required')
    require(manifest.get('capture_source_identity') == admission['source_identity'], 'producer/runtime source closure')
    for name,field in (('full-duration.json','full_duration_receipt_sha256'),('disconnect.json','disconnect_receipt_sha256')):
        raw = (package/name).read_bytes()
        require(len(raw)<=16384 and sha(raw)==admission[field], 'packaged lifecycle proof identity')
        proof=json.loads(raw,object_pairs_hook=L['unique'])
        require(proof.get('monitor_source_sha256') == manifest['inputs']['monitor.c'] and
            proof.get('fixture_source_sha256') == manifest['inputs']['monitor-fixture.c'], 'lifecycle proof source identity')
        if name=='full-duration.json':
            require(proof.get('classification')=='harmless-full-duration-lifecycle-observed' and
                proof.get('deadline_contract_met') is True and proof.get('status',{}).get('reaped')=='1', 'full-duration proof incomplete')
        else:
            require(proof.get('classification')=='exact-dropbear-disconnect-private-capture-and-reap-pass' and
                proof.get('monitor_exit')==2 and proof.get('monitor_status',{}).get('reaped')=='1', 'disconnect proof incomplete')
    binary = (package / 'keyboard-monitor').read_bytes()
    require(type(admission['monitor_bytes']) is int and 0 < len(binary) == admission['monitor_bytes'] <= 131072
        and sha(binary) == admission['monitor_sha256'], 'exact enabled binary')
    sums = (package/'SHA256SUMS').read_bytes()
    require(sha(sums) == admission['package_identity'], 'package inventory drift')
    package_pins = dict((line.split('  ./',1)[1],line.split('  ./',1)[0]) for line in sums.decode().splitlines())
    delivery_files = {'keyboard-monitor':binary}
    for name in ('licenses/musl-COPYRIGHT','licenses/repository-LICENSE','licenses/GCC-copyright'):
        raw = (package/name).read_bytes()
        require(0 < len(raw) <= 131072 and sha(raw) == package_pins.get(name), 'license bytes changed')
        delivery_files[name] = raw
    expected = admission['expected']
    binding = {'candidate_sha256': candidate['files']['boot.img'], 'image_sha256': candidate['files']['Image.gz'],
        'dtb_sha256': candidate['files']['board.dtb'], 'config_sha256': candidate['files']['kernel.config'],
        'initramfs_sha256': candidate['files']['initramfs.img'],
        'helper_sha256': candidate['members']['bin/keyboard-observe']['sha256'],
        'launcher_sha256': sha(Path(__file__).read_bytes()), 'protocol_sha256': sha((HERE/'protocol.json').read_bytes())}
    require(all(expected.get(k) == v for k, v in binding.items()), 'classifier candidate/source binding')
    archive = L['REPO']/'artifacts/a53-authenticated'
    baseline_id = admission['dependency']['baseline_admission_id']
    require(expected.get('baseline_first_boot_result_sha256') == sha(C['regular'](archive/'attempts'/baseline_id/'result.json',131072))
        and expected.get('baseline_recovery_result_sha256') == sha(C['regular'](archive/'sessions'/baseline_id/'confirm-recovery/result.json',131072)), 'baseline result pins')
    runtime = admission['runtime']
    require(set(runtime) == {'event', 'minor', 'input_path', 'capabilities', 'resource_paths',
        'logger_age_limit_seconds', 'metadata_receipt_sha256'}, 'runtime contract inventory')
    require(re.fullmatch(r'event(?:0|[1-9][0-9]{0,2})', runtime['event']) and int(runtime['event'][5:]) <= 255
        and type(runtime['minor']) is int and 0 <= runtime['minor'] <= 1048575, 'input identity')
    require(runtime['input_path'] == expected['input_sysfs_realpath'] and
        re.fullmatch(r'/sys/devices/platform/[A-Za-z0-9_./:@+-]+/input/input[0-9]+', runtime['input_path'])
        and '..' not in Path(runtime['input_path']).parts, 'input ancestry')
    require(type(runtime['logger_age_limit_seconds']) is int and 0 < runtime['logger_age_limit_seconds'] <= 240,
        'original logger budget')
    require(C['SHA'].fullmatch(runtime['metadata_receipt_sha256']), 'reviewed metadata receipt')
    require(set(runtime['capabilities']) == {'ev','key','rel','abs','msc','led','snd','ff','sw'} and
        all(re.fullmatch(r'[0-9a-f ]+\n', v) for v in runtime['capabilities'].values()), 'capability bytes')
    require(sha(b''.join(k.encode()+b'='+runtime['capabilities'][k].encode() for k in
        ('ev','key','rel','abs','msc','led','snd','ff','sw'))) == expected['input_capabilities_sha256'], 'capability identity')
    require(type(runtime['resource_paths']) is dict and 1 <= len(runtime['resource_paths']) <= 12, 'resource contract')
    for key, value in runtime['resource_paths'].items():
        require(all(re.fullmatch(r'/sys/[A-Za-z0-9_./:@+-]+', p) and '..' not in Path(p).parts
                    for p in (key, value)), 'exact resource link')
    return {'admission': admission, 'package': package, 'binary': binary, 'delivery_files':delivery_files,'dependency': dependency}


def delivery_script(context):
    """Deliver only the separately frozen enabled package; preserve every notice."""
    text = guard(context, True)
    text += "[ \"$($BB awk '$2 == \"/\" {n++; if (($3 == \"rootfs\" || $3 == \"ramfs\" || $3 == \"tmpfs\") && $4 !~ /(^|,)(ro|noexec)(,|$)/) ok++} END {print n+0 \":\" ok+0}' /proc/mounts)\" = 1:1 ]\n"
    text += "[ \"$($BB awk '$2 == \"/a53-keyboard-delivery\" || index($2, \"/a53-keyboard-delivery/\") == 1 {n++} END {print n+0}' /proc/mounts)\" = 0 ]\n"
    text += '[ ! -e /a53-keyboard-delivery ] && [ ! -L /a53-keyboard-delivery ]\numask 077\n$BB mkdir -m 700 /a53-keyboard-delivery\n$BB mkdir -m 700 /a53-keyboard-delivery/licenses\n'
    for i,name in enumerate(('keyboard-monitor','licenses/musl-COPYRIGHT','licenses/repository-LICENSE','licenses/GCC-copyright')):
        raw = context['delivery_files'][name]
        require(0 < len(raw) <= 131072, 'delivery file ceiling')
        path = '/a53-keyboard-delivery/'+name
        text += f"$BB base64 -d >{path} <<'KEYBOARD_FILE_{i}'\n{base64.b64encode(raw).decode()}\nKEYBOARD_FILE_{i}\n"
        text += f'[ "$($BB stat -c %s {path})" = {len(raw)} ]\nh=$($BB sha256sum {path}); [ "${{h%% *}}" = {sha(raw)} ]\n'
    text += '$BB chmod 700 /a53-keyboard-delivery/keyboard-monitor\n'
    text += "$BB printf '__KEYBOARD_DELIVERY_PASS__\\n'\n"
    require(len(text.encode()) <= 262144, 'delivery command ceiling')
    return text.encode()


def guard(context, initial):
    a = context['admission']; r = a['runtime']; c = context['dependency']['prepared']['candidate']
    script = S['identity_script'](c, a['boot_id']) + S['ram_guard_script']()
    script += L['observer_guard'](c).decode()
    script += f'[ "$($BB readlink -f /sys/class/input/{r["event"]}/device)" = {shlex.quote(r["input_path"])} ]\n'
    script += f'[ "$($BB cat /sys/class/input/{r["event"]}/dev)" = 13:{r["minor"]} ]\n'
    script += f'[ "$($BB cat /sys/class/input/{r["event"]}/device/name)" = keyboard-matrix ]\n'
    for name, value in sorted(r['capabilities'].items()):
        script += f'[ "$($BB cat /sys/class/input/{r["event"]}/device/capabilities/{name})" = {shlex.quote(value.rstrip())} ]\n'
    for path, target in sorted(r['resource_paths'].items()):
        script += f'[ "$($BB readlink -f {shlex.quote(path)})" = {shlex.quote(target)} ]\n'
    for member in ('bin/console-keymap-verify','etc/gemini-us.bkeymap','bin/keyboard-observe'):
        script += f'h=$($BB sha256sum /{member}); [ "${{h%% *}}" = {c["members"][member]["sha256"]} ]\n'
    script += f'map=$(/bin/console-keymap-verify --verify /etc/gemini-us.bkeymap); [ "$map" = {shlex.quote(C["MAP_RESULT"])} ]\n'
    script += '[ "$($BB cat /sys/class/tty/tty0/active)" = tty1 ]\n'
    script += '[ "$($BB awk \'$1 ~ /^tty[01]$/ {n++} END {print n+0}\' /proc/consoles)" = 0 ]\n'
    if initial:
        script += f'$BB awk \'$1 >= {r["logger_age_limit_seconds"]} {{exit 1}}\' /proc/uptime\n'
    # Any inaccessible/changing process inventory refuses; never assume absence.
    script += r'''
processes=0
descriptors=0
for proc in /proc/[0-9]*; do
  processes=$((processes+1)); [ "$processes" -le 512 ]
  [ -r "$proc/cmdline" ]; command=$($BB tr '\000' ' ' <"$proc/cmdline")
  case "$command" in *console-status*|*keyboard-observe*|*input-event-capture*|*getty*|*local-shell*) exit 1;; esac
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
'''
    return script


def capture_script(context):
    a = context['admission']; r = a['runtime']
    # Delivery directory was exclusively admitted separately and its byte receipt pinned.
    text = guard(context, True)
    text += '[ -d /a53-keyboard-delivery ] && [ ! -L /a53-keyboard-delivery ]\n'
    text += '[ "$($BB stat -c %u:%a /a53-keyboard-delivery)" = 0:700 ]\n'
    text += f'h=$($BB sha256sum /a53-keyboard-delivery/keyboard-monitor); [ "${{h%% *}}" = {a["monitor_sha256"]} ]\n'
    text += 'set +e\n'
    text += f'/a53-keyboard-delivery/keyboard-monitor {r["event"]} {r["minor"]}\nstatus=$?\nset -e\n'
    text += 'umask 077\nset -C\n$BB printf "%s\\n" "$status" >/a53-keyboard-delivery/keyboard-attempt/outer-exit\n'
    text += '[ "$status" = 0 ]\n' + guard(context, False)
    text += "$BB printf '__KEYBOARD_POSTFLIGHT_PASS__\\n'\n"
    return text.encode()


def export_script(context):
    # Export does not require a live logger or successful capture; retain failures too.
    text = S['identity_script'](context['dependency']['prepared']['candidate'], context['admission']['boot_id'])
    text += S['ram_guard_script']()
    text += '[ -d /a53-keyboard-delivery ] && [ ! -L /a53-keyboard-delivery ]\n'
    text += '[ -d /a53-keyboard-delivery/keyboard-attempt ] && [ ! -L /a53-keyboard-delivery/keyboard-attempt ]\n'
    text += '[ "$($BB stat -c %u:%a /a53-keyboard-delivery/keyboard-attempt)" = 0:700 ]\n'
    text += "[ \"$($BB awk '$2 == \"/a53-keyboard-delivery\" || index($2, \"/a53-keyboard-delivery/\") == 1 {n++} END {print n+0}' /proc/mounts)\" = 0 ]\n"
    for name in FILES:
        path = '/a53-keyboard-delivery/keyboard-attempt/' + name
        text += f"$BB printf 'file={name}\\n'\n"
        text += f"if [ ! -e {path} ] && [ ! -L {path} ]; then $BB printf 'missing\\nend={name}\\n'; else\n"
        text += f'[ -f {path} ] && [ ! -L {path} ]\n'
        text += f'[ "$($BB stat -c %u:%a:%h {path})" = 0:600:1 ]\n'
        text += f'[ "$($BB stat -c %s {path})" -le {LIMITS[name]} ]\n'
        text += f"$BB base64 {path}; $BB printf 'end={name}\\n'\nfi\n"
    return text.encode()


def perform(context, action, execute=False):
    require(action in ('delivery', 'capture', 'export'), 'action')
    if not execute:
        return {'classification':'dry-run', 'action':action, 'execution':'disabled'}
    execution_gate()
    require(context['admission']['source_identity'] == source_identity(), 'source changed')
    context = prepare(context['admission'], context['package'])
    runpy.run_path(str(HERE/'../emmc/mainline_host.py'))['require_ready']()
    root = ROOT / context['admission']['id']
    C['private_root'](root)
    if action == 'capture':
        require(json.loads(C['regular'](root/'delivery/admission.json',65536)) == context['admission'], 'delivery admission binding')
        delivery_process = json.loads(C['regular'](root/'delivery/process.json',16384))
        L['process_ok'](C['regular'](root/'delivery/stdout.txt',4096),C['regular'](root/'delivery/stderr.txt',16384),delivery_process,30,4096)
        require(C['regular'](root/'delivery/stdout.txt',4096) == b'__KEYBOARD_DELIVERY_PASS__\n', 'delivery witness')
    if action == 'export':
        require((root/'capture/claim.json').is_file(), 'no capture attempt')
        require(json.loads(C['regular'](root/'capture/admission.json',65536)) == context['admission'], 'capture binding')
    directory = root / action
    directory.mkdir(mode=0o700)
    script = {'delivery':delivery_script, 'capture':capture_script, 'export':export_script}[action](context)
    seconds, cap = {'delivery':(30,4096),'capture':(240,131072),'export':(30,278528)}[action]
    C['write_new'](directory/'admission.json',encode(context['admission']))
    C['write_new'](directory/'command.sh',script)
    C['write_new'](directory/'claim.json',encode({'action':action,'connections':1,'seconds':seconds,'command_sha256':sha(script)}))
    L['F']['sync_directory'](directory); L['F']['sync_directory'](root)
    prepared = context['dependency']['prepared']
    require(sha(C['regular'](prepared['keys']/'known_hosts',8192)) == prepared['candidate']['known_hosts_sha256'], 'host pin drift')
    process = C['run_once'](C['ssh_command'](prepared['keys']),script,directory,seconds,stdout_limit=cap,stderr_limit=16384)
    C['write_new'](directory/'process.json',encode(process))
    return {'classification':'raw-'+action+'-retained','process':process}


def parse_export(raw):
    require(len(raw) <= 278528, 'export bound')
    lines = iter(raw.splitlines())
    files = {}
    for name in FILES:
        require(next(lines,None) == ('file='+name).encode(), 'export order')
        body = []
        for line in lines:
            if line == ('end='+name).encode(): break
            body.append(line)
        else: raise ValueError('truncated export')
        if body == [b'missing']:
            files[name] = None
        else:
            value = base64.b64decode(b''.join(body),validate=True)
            require(len(value) <= LIMITS[name], 'export member ceiling')
            files[name] = value
    require(next(lines,None) is None, 'export trailing data')
    return files


def assess(context, owner_record):
    """Reparse retained bytes. Never infer owner completion or final recovery."""
    context = prepare(context['admission'],context['package'])
    a = context['admission']; root = ROOT/a['id']
    for action in ('capture','export'):
        require(json.loads(C['regular'](root/action/'admission.json',65536)) == a, 'phase admission drift')
        expected_script = capture_script(context) if action == 'capture' else export_script(context)
        require(C['regular'](root/action/'command.sh',262144) == expected_script, 'phase command drift')
    raw = C['regular'](root/'export/stdout.txt',278528)
    export_process = json.loads(C['regular'](root/'export/process.json',16384))
    L['process_ok'](raw,C['regular'](root/'export/stderr.txt',16384),export_process,30,278528)
    files = parse_export(raw)
    # Persist all available private bytes even when required members are missing.
    saved = root/'preserved-keyboard-files'
    C['private_root'](saved)
    for name, value in files.items():
        if value is not None:
            if (saved/name).exists():
                require(C['regular'](saved/name,LIMITS[name]) == value, 'preserved file drift')
            else: C['write_new'](saved/name,value)
    L['F']['sync_directory'](saved); L['F']['sync_directory'](root)
    require(all(v is not None for v in files.values()), 'partial keyboard files preserved; no acceptance')
    output = C['regular'](root/'capture/stdout.txt',131072)
    capture_process = json.loads(C['regular'](root/'capture/process.json',16384))
    L['process_ok'](output,C['regular'](root/'capture/stderr.txt',16384),capture_process,240,131072)
    require(output == files['observer.stdout'] + b'__KEYBOARD_POSTFLIGHT_PASS__\n', 'forwarded/retained/postflight binding')
    require(files['observer.stderr'] == b'' and files['outer-exit'] == b'0\n', 'observer process failure')
    status = S['fields'](files['monitor.status'])
    wanted = {'schema':'keyboard-monitor-v1','reason':'normal-lifecycle-only','reaped':'1','identity_lost':'0',
        'exit':'0','signal':'0','cancel':'0','term_ms':'-1','kill_ms':'-1','term_errno':'0','kill_errno':'0','late':'0',
        'stdout_bytes':str(len(files['observer.stdout'])),'stderr_bytes':'0','forwarded_bytes':str(len(files['observer.stdout']))}
    require(set(status) == set(wanted)|{'reap_ms'} and all(status[k]==v for k,v in wanted.items())
        and status['reap_ms'].isdigit() and 202000 <= int(status['reap_ms']) < 210000, 'monitor lifecycle refusal')
    require(set(owner_record) == {'admission_id','sequence_complete','screen_readable','source'} and
        owner_record['admission_id']==a['id'] and owner_record['sequence_complete'] is True and
        owner_record['screen_readable'] is True and type(owner_record['source']) is str and
        0 < len(owner_record['source']) <= 1024, 'actual owner completion required')
    C['write_new'](saved/'owner.json',encode(owner_record))
    receipt = {**a['expected'],'deployment_receipt_sha256':a['dependency']['deployment_receipt_sha256'],
        'recovery_reference_sha256':a['dependency']['confirmation_manifest_sha256'],
        'boot_id_before':a['boot_id'],'boot_id_after':a['boot_id'],
        'known_good_boot_id':context['dependency']['recovered_boot'],'cpu_online_before':'0-7','cpu_online_after':'0-7',
        'map_sha256':K['PROTOCOL']['map_sha256'],'capture_exit_status':0,'capture_sha256':sha(files['observer.stdout']),
        'event':a['runtime']['event'],'event_minor':a['runtime']['minor'],
        **{k:True for k in ('map_verify_before','map_verify_after','baseline_dependencies_verified','console_logs_separated',
            'tty1_exclusive','owner_sequence_complete','owner_screen_readable','post_capture_usb_pass','budget_claimed_once')}}
    result = K['classify'](a['expected'],receipt,files['observer.stdout'])
    C['write_new'](saved/'receipt.json',encode(receipt))
    C['write_new'](saved/'result.json',encode({'packet_result':result,'final_keyboard_acceptance':False,
        'requires':'separately preserved complete logger and attributable recovery'}))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','delivery','capture','export','assess'))
    parser.add_argument('--admission',required=True,type=Path)
    parser.add_argument('--package',required=True,type=Path)
    parser.add_argument('--owner',type=Path)
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    if args.execute: execution_gate()  # Refuse before even reading paths.
    context = prepare(json.loads(C['regular'](args.admission,65536),object_pairs_hook=L['unique']),args.package)
    if args.action == 'prepare':
        result = {'classification':'prepared','execution':'disabled'}
    elif args.action == 'assess':
        require(args.owner is not None, 'owner record required')
        result = assess(context,json.loads(C['regular'](args.owner,8192),object_pairs_hook=L['unique']))
    else: result = perform(context,args.action,args.execute)
    print(json.dumps(result,sort_keys=True))
