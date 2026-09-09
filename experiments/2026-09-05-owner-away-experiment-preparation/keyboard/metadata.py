#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One read-only metadata connection after a verified same-boot disconnect proof."""
import argparse
import json
import os
from pathlib import Path
import re
import runpy

HERE = Path(__file__).resolve().parent
D = runpy.run_path(str(HERE/'disconnect.py'))
M, C, S, L, P = (D[name] for name in ('M', 'C', 'S', 'L', 'P'))
require, sha, encode = D['require'], D['sha'], D['encode']
CAPABILITIES = ('ev', 'key', 'rel', 'abs', 'msc', 'led', 'snd', 'ff', 'sw')
MATRIX = '/sys/devices/platform/keyboard-matrix'
MATRIX_DRIVER = '/sys/bus/platform/drivers/matrix-keypad'
PROVIDER_DRIVER = '/sys/bus/i2c/drivers/aw9523-pinctrl'
PROVIDER_NODE = '/sys/firmware/devicetree/base/i2c@1101c000/gpio-expander@5b'


def script(candidate, boot):
    text = S['identity_script'](candidate, boot) + S['ram_guard_script']()
    text += L['observer_guard'](candidate).decode() + M['console_guard'](candidate)
    text += M['reader_guard']()
    text += r'''
$BB awk '$1 >= 240 {exit 1}' /proc/uptime
matrix=0
scanned=0
event=
for item in /sys/class/input/event*; do
  [ -e "$item" ] || continue
  scanned=$((scanned+1)); [ "$scanned" -le 256 ]
  [ -r "$item/device/name" ]
  name=$($BB head -c 128 "$item/device/name")
  if [ "$name" = keyboard-matrix ]; then
    matrix=$((matrix+1)); event=${item##*/}
  fi
done
[ "$matrix" = 1 ]
input_path=$($BB readlink -f "/sys/class/input/$event/device")
case "$input_path" in /sys/devices/platform/keyboard-matrix/input/input[0-9]*) ;; *) exit 1;; esac
[ "$($BB readlink -f /sys/devices/platform/keyboard-matrix/driver)" = /sys/bus/platform/drivers/matrix-keypad ]
[ "$($BB readlink -f /sys/devices/platform/keyboard-matrix/of_node)" = /sys/firmware/devicetree/base/keyboard-matrix ]
dev=$($BB cat "/sys/class/input/$event/dev")
case "$dev" in 13:*) minor=${dev#13:};; *) exit 1;; esac
case "$minor" in ''|*[!0-9]*) exit 1;; esac
[ "${#minor}" -le 7 ] && [ "$minor" -le 1048575 ]
node="/dev/input/$event"
[ -c "$node" ] && [ ! -L "$node" ]
minor_hex=$($BB printf '%x' "$minor")
[ "$($BB stat -c '%t:%T' "$node")" = "d:$minor_hex" ]
providers=0
provider=
for item in /sys/bus/i2c/drivers/aw9523-pinctrl/*-005b; do
  [ -e "$item" ] || continue
  providers=$((providers+1)); [ "$providers" -le 256 ]
  [ "$($BB readlink -f "$item/of_node")" = /sys/firmware/devicetree/base/i2c@1101c000/gpio-expander@5b ]
  provider=${item##*/}
done
[ "$providers" = 1 ]
[ "$($BB readlink -f "/sys/bus/i2c/devices/$provider/driver")" = /sys/bus/i2c/drivers/aw9523-pinctrl ]
[ "$($BB readlink -f "/sys/bus/i2c/devices/$provider/of_node")" = /sys/firmware/devicetree/base/i2c@1101c000/gpio-expander@5b ]
$BB printf 'event=%s\nminor=%s\ninput_path=%s\nprovider=%s\n' "$event" "$minor" "$input_path" "$provider"
for capability in ev key rel abs msc led snd ff sw; do
  value=$($BB head -c 1025 "/sys/class/input/$event/device/capabilities/$capability")
  [ "${#value}" -le 1024 ]
  $BB printf 'cap_%s=%s\n' "$capability" "$value"
done
$BB awk '$1 >= 240 {exit 1} {printf "logger_age_seconds=%d\n", $1}' /proc/uptime
'''
    text += f'[ "$($BB cat /proc/sys/kernel/random/boot_id)" = {boot} ]\n'
    text += f"$BB printf 'boot_id={boot}\\n__KEYBOARD_METADATA_PASS__\\n'\n"
    return text.encode()


def parse(raw, stderr, process, admission, candidate):
    L['process_ok'](raw, stderr, process, 30, 16384)
    marker = b'__KEYBOARD_METADATA_PASS__\n'
    require(raw.endswith(marker), 'metadata completion marker')
    values = S['fields'](raw[:-len(marker)])
    require(set(values) == {'event', 'minor', 'input_path', 'provider', 'logger_age_seconds',
        'boot_id'} | {'cap_'+name for name in CAPABILITIES}, 'metadata field inventory')
    require(values['boot_id'] == admission['boot_id'], 'metadata boot binding')
    require(re.fullmatch(r'event(0|[1-9][0-9]{0,2})', values['event']) and
        int(values['event'][5:]) <= 255, 'metadata event')
    require(re.fullmatch(r'0|[1-9][0-9]{0,6}', values['minor']) and
        int(values['minor']) <= 1048575, 'metadata minor')
    require(re.fullmatch(re.escape(MATRIX)+r'/input/input(0|[1-9][0-9]{0,2})',
        values['input_path']), 'metadata matrix ancestry')
    require(re.fullmatch(r'(0|[1-9][0-9]{0,2})-005b', values['provider']), 'metadata provider')
    require(re.fullmatch(r'0|[1-9][0-9]{0,2}', values['logger_age_seconds']) and
        int(values['logger_age_seconds']) < 240, 'metadata logger age')
    capabilities, bits = {}, {}
    for name in CAPABILITIES:
        value = values['cap_'+name]
        require(len(value) <= 1024 and re.fullmatch(r'[0-9a-f]{1,16}( [0-9a-f]{1,16})*', value),
            'metadata capability bitmap')
        capabilities[name] = value+'\n'
        bits[name] = int(''.join(word.zfill(16) for word in value.split()), 16)
    require(bits['ev'] & (1 << 1) and bits['ev'] & (1 << 4) and bits['msc'] & (1 << 4),
        'metadata event/scan capabilities')
    require(all(bits['key'] & (1 << key) for key in M['K']['SCANS']), 'metadata protocol keys')
    provider = '/sys/bus/i2c/devices/'+values['provider']
    resources = {MATRIX+'/driver': MATRIX_DRIVER,
        MATRIX+'/of_node': '/sys/firmware/devicetree/base/keyboard-matrix',
        provider+'/driver': PROVIDER_DRIVER, provider+'/of_node': PROVIDER_NODE}
    runtime = {'event':values['event'], 'minor':int(values['minor']),
        'input_path':values['input_path'], 'capabilities':capabilities,
        'resource_paths':resources, 'logger_age_limit_seconds':240}
    receipt = {'schema':'keyboard-runtime-metadata-v1', 'classification':'passed',
        'admission_id':admission['id'], 'boot_id':admission['boot_id'],
        'candidate_sha256':candidate['files']['boot.img'], 'event':runtime['event'],
        'minor':runtime['minor'], 'input_path':runtime['input_path'],
        'capabilities_sha256':P['object_digest'](capabilities),
        'resource_paths_sha256':P['object_digest'](resources),
        'logger_age_seconds':int(values['logger_age_seconds']), 'map_verified':True,
        'console_logs_separated':True, 'console_status_exited':True, 'inventory_complete':True}
    runtime['metadata_receipt_sha256'] = sha(encode(receipt))
    return runtime, receipt


def perform(admission, package, execute=False):
    context = D['prepare'](admission, package)
    command = script(context['candidate'], admission['boot_id'])
    if not execute:
        return {'classification':'prepared-read-only-metadata', 'connections':0,
            'command_sha256':sha(command)}
    base = D['ROOT']/admission['id']/'prerequisites'
    proof = base/'disconnect'
    raw = C['regular'](proof/'receipt.json', 65536)
    P['disconnect'](raw, sha(raw), admission, context['candidate'], context['pins'], proof, C['regular'])
    runpy.run_path(str(HERE/'../emmc/mainline_host.py'))['require_ready']()
    directory = base/'metadata'; directory.mkdir(mode=0o700)
    C['write_new'](directory/'command.sh', command)
    C['write_new'](directory/'admission.json', encode(admission))
    C['write_new'](directory/'claim.json', encode({'count':1, 'connections':1, 'retries':0,
        'seconds':30, 'stdout_limit':16384, 'stderr_limit':16384, 'command_sha256':sha(command),
        'disconnect_receipt_sha256':sha(raw)}))
    L['F']['sync_directory'](directory)
    process = C['run_once'](C['ssh_command'](context['dependency']['prepared']['keys']), command,
        directory, 30, stdout_limit=16384, stderr_limit=16384)
    C['write_new'](directory/'process.json', encode(process))
    runtime, receipt = parse(C['regular'](directory/'stdout.txt',16384),
        C['regular'](directory/'stderr.txt',16384), process, admission, context['candidate'])
    C['write_new'](base/'runtime.json', encode(receipt))
    C['write_new'](directory/'runtime-contract.json', encode(runtime))
    return {'classification':'metadata-preserved', 'runtime':runtime}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission', required=True, type=Path)
    parser.add_argument('--package', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(); os.umask(0o077)
    admission = json.loads(C['regular'](args.admission,65536), object_pairs_hook=L['unique'])
    print(json.dumps(perform(admission,args.package,args.execute), sort_keys=True))
