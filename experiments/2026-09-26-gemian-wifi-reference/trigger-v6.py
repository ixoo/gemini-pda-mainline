#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One guarded, single-use Gemian Wi-Fi DMA capture trigger."""

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import time


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRIVATE = REPO / 'artifacts/gemian-wifi-reference'
COLLECTOR = PRIVATE / 'runtime-v6-return-1'
OUTPUT = PRIVATE / 'trigger-v6-1'
DEPLOYMENT = REPO / 'artifacts/device-install-evidence/gemian-wifi-reference-deployment-6'
IDENTITY = REPO / 'artifacts/credentials/gemini_ed25519'
TRUST = REPO / 'artifacts/credentials/a53-recovery-known_hosts'
TRUST_SHA256 = 'd43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f'
CANDIDATE_SHA256 = 'f6218df7bc55b00218d2b9ac3e2cac61a1903486b753ff90bf51dcd1687eee7b'
PREVIOUS_BOOT = '767b1414-855e-4060-ba19-a3458cad1268'
RELEASE = '3.18.41-gemini-wifi-ref6+'
BOOT_ID = re.compile(r'^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$')
ZERO_REPLY_SHA256 = hashlib.sha256(bytes(4096)).hexdigest()
SSH = [
    'ssh', '-o', 'UserKnownHostsFile=' + str(TRUST),
    '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
    '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=6',
    '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none',
    '-o', 'StrictHostKeyChecking=yes', '-i', str(IDENTITY),
    'gemini@192.168.1.50',
]

REMOTE = r'''set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "${MODE:-}" == probe || "${MODE:-}" == trigger ]] || fail 'invalid mode'
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 &&
   "$(uname -r)" == 3.18.41-gemini-wifi-ref6+ ]] || fail 'wrong diagnostic release'
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || fail 'boot ID changed'
[[ "$(cat /sys/class/net/wlan0/carrier)" == 1 ]] || fail 'Wi-Fi carrier is absent'
shopt -s nullglob
paths=(/sys/module/*/parameters/gemini_wifi_ref_capture)
[[ "${#paths[@]}" == 1 && -f "${paths[0]}" && ! -L "${paths[0]}" ]] ||
    fail 'diagnostic parameter is missing or ambiguous'
path=${paths[0]}
read -r mode owner <<<"$(stat -c '%a %U' "$path")"
[[ "$mode" == 600 && "$owner" == root ]] || fail 'diagnostic parameter is not root-only'
value=$(cat "$path") || fail 'cannot read diagnostic parameter'
[[ "$value" == N || "$value" == 0 ]] || fail 'diagnostic trigger was already used'
log=$(dmesg) || fail 'cannot inspect existing diagnostic records'
[[ "$log" != *'gemini-wifi-ref-v6: dma-'* ]] || fail 'diagnostic record already exists'
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" &&
   "$(cat /sys/class/net/wlan0/carrier)" == 1 ]] || fail 'identity or carrier changed'
if [[ "$MODE" == probe ]]; then
    printf 'gate=passed\nboot_id=%s\nrelease=%s\ncarrier=1\nparameter_mode=600\nparameter_initial=off\n' \
        "$EXPECTED_BOOT_ID" "$(uname -r)"
    exit 0
fi
printf '1\n' >"$path" || fail 'diagnostic trigger write failed'
value=$(cat "$path") || fail 'diagnostic trigger readback failed'
[[ "$value" == Y || "$value" == 1 ]] || fail 'diagnostic trigger did not read back'
dd if=/dev/zero bs=4096 count=1 status=none
'''


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit('refused: ' + message)


def deployment_values():
    summary = DEPLOYMENT / 'deployment-summary.txt'
    manifest = DEPLOYMENT / 'SHA256SUMS'
    require(summary.is_file() and not summary.is_symlink() and
            manifest.is_file() and not manifest.is_symlink(),
            'verified boot2 deployment evidence missing')
    subprocess.run(['sha256sum', '--check', '--strict', 'SHA256SUMS'], cwd=DEPLOYMENT,
                   check=True, stdout=subprocess.DEVNULL)
    values = {}
    for line in summary.read_text().splitlines():
        key, separator, value = line.partition('=')
        require(separator and key not in values, 'deployment summary malformed')
        values[key] = value
    return values


def capture(name, command, timeout=30):
    try:
        result = subprocess.run(SSH + [command], capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        (OUTPUT / (name + '.out')).write_bytes(exc.stdout or b'')
        (OUTPUT / (name + '.err')).write_bytes(exc.stderr or b'')
        raise
    (OUTPUT / (name + '.out')).write_bytes(result.stdout)
    (OUTPUT / (name + '.err')).write_bytes(result.stderr)
    return result.returncode


def remote(mode, boot_id):
    command = 'sudo -n env MODE=' + mode + ' EXPECTED_BOOT_ID=' + shlex.quote(boot_id) + ' /bin/bash -s'
    try:
        result = subprocess.run(SSH + [command], input=REMOTE.encode(),
                                capture_output=True, timeout=45)
    except subprocess.TimeoutExpired as exc:
        (OUTPUT / (mode + '.out')).write_bytes(exc.stdout or b'')
        (OUTPUT / (mode + '.err')).write_bytes(exc.stderr or b'')
        raise
    (OUTPUT / (mode + '.out')).write_bytes(result.stdout)
    (OUTPUT / (mode + '.err')).write_bytes(result.stderr)
    return result.returncode, result.stdout


def main():
    os.umask(0o077)
    require(IDENTITY.is_file() and not IDENTITY.is_symlink(), 'SSH identity missing')
    require(stat.S_IMODE(IDENTITY.stat().st_mode) == 0o600, 'SSH identity mode changed')
    require(TRUST.is_file() and not TRUST.is_symlink() and sha256(TRUST) == TRUST_SHA256,
            'SSH host trust changed')
    deployed = deployment_values()
    require(deployed.get('result') == 'write-synced-flushed-full-readback-verified' and
            deployed.get('target_logical_name') == 'boot2' and
            deployed.get('boot2_device_guard') == 'passed' and
            deployed.get('candidate_sha256') == CANDIDATE_SHA256 and
            deployed.get('readback_sha256') == CANDIDATE_SHA256 and
            deployed.get('boot_id') == PREVIOUS_BOOT and
            deployed.get('post_shutdown_reachability') == 'unreachable',
            'boot2 deployment identity mismatch')
    require((COLLECTOR / 'result.json').is_file() and
            not (COLLECTOR / 'result.json').is_symlink(), 'collector receipt missing')
    first = json.loads((COLLECTOR / 'result.json').read_text())
    boot_id = first['observed_boot']
    require(isinstance(boot_id, str) and BOOT_ID.fullmatch(boot_id) and
            boot_id != PREVIOUS_BOOT, 'collector did not observe a changed boot')
    require(first['previous_boot'] == PREVIOUS_BOOT, 'collector predecessor mismatch')
    require(first['kernel_release'] == RELEASE and first['diagnostic_kernel'] is True,
            'collector release mismatch')
    require(first['early_dmesg_rc'] == first['late_dmesg_rc'] == 0 and
            first['carrier_early_rc'] == first['carrier_late_rc'] == 0,
            'collector capture incomplete')
    require((COLLECTOR / 'carrier-early.out').read_text().strip() == '1' and
            (COLLECTOR / 'carrier-late.out').read_text().strip() == '1',
            'collector did not observe stable Wi-Fi carrier')
    require(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'trigger already attempted')
    OUTPUT.mkdir(mode=0o700)
    result = {'candidate_sha256': CANDIDATE_SHA256, 'boot_id': boot_id,
              'kernel_release': RELEASE, 'effect_budget': 'one flag write and one 4096-byte reply'}
    phase = 'probe'
    try:
        result['probe_rc'], _ = remote('probe', boot_id)
        if result['probe_rc'] != 0:
            result['status'] = 'preflight-refused'
            return
        phase = 'trigger'
        result['trigger_rc'], reply = remote('trigger', boot_id)
        result['reply_bytes'] = len(reply)
        result['reply_sha256'] = hashlib.sha256(reply).hexdigest()
        result['reply_matches_zero_4096'] = len(reply) == 4096 and result['reply_sha256'] == ZERO_REPLY_SHA256
        result['early_dmesg_rc'] = capture('dmesg-early', 'sudo -n dmesg')
        result['carrier_early_rc'] = capture('carrier-early', 'cat /sys/class/net/wlan0/carrier')
        time.sleep(25)
        result['late_dmesg_rc'] = capture('dmesg-late', 'sudo -n dmesg')
        result['carrier_late_rc'] = capture('carrier-late', 'cat /sys/class/net/wlan0/carrier')
        result['status'] = 'complete' if (result['trigger_rc'] == 0 and
                                         result['reply_matches_zero_4096'] and
                                         all(result[name] == 0 for name in (
                                             'early_dmesg_rc', 'late_dmesg_rc',
                                             'carrier_early_rc', 'carrier_late_rc'))) else 'incomplete'
    except subprocess.TimeoutExpired as exc:
        result['status'] = 'timeout-no-retry'
        result['timeout_phase'] = phase
        result['timeout_seconds'] = exc.timeout
        if phase == 'trigger':
            read_only = ('sudo -n sh -c ' + shlex.quote(
                'test "$(cat /proc/sys/kernel/random/boot_id)" = ' +
                shlex.quote(boot_id) + ' && dmesg'))
            try:
                result['timeout_dmesg_rc'] = capture('dmesg-timeout', read_only)
            except subprocess.TimeoutExpired:
                result['timeout_dmesg_rc'] = 'timeout'
    finally:
        (OUTPUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print('trigger_status=' + result['status'], flush=True)


if __name__ == '__main__':
    main()
