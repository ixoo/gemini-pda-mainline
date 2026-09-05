#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the derived remote deployment gate on synthetic block metadata."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
from v4_installer_guard import derive

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location('guard_tests', REPO/'scripts/boot2-device-guard-test.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
source = (REPO/'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh').read_text()
derived = derive(source, (REPO/'scripts/boot2-device-guard.sh').read_bytes())
remote = derived.split("<<'REMOTE'\n")[1].split('\nREMOTE\n')[0]
# The only shell-condition adapter replaces the real block-node test. Metadata
# applets below are injected; all production guard and write-order logic runs.
anchor = '[[ -z "${mountpoint:-}" && -z "${extra:-}" && -b "$target" ]]'
assert remote.count(anchor) == 1
remote = remote.replace(anchor, '[[ -z "${mountpoint:-}" && -z "${extra:-}" ]] && fixture_block "$target"')
marker = '\nfor command in awk blockdev cat dd find findmnt id lsblk readlink sha256sum sleep '
assert remote.count(marker) == 1
mocks = shared.MOCKS.split('# Exercise callers')[0]
# Preserve shared metadata implementations while wrapping deployment applets.
mocks += r'''
eval "$(declare -f cat | sed '1s/^cat /guard_cat /')"
eval "$(declare -f readlink | sed '1s/^readlink /guard_readlink /')"
eval "$(declare -f stat | sed '1s/^stat /guard_stat /')"
fixture_block() { [[ "$1" == /dev/mmcblk0p31 ]]; }
id() { printf '0\n'; }
uname() { if [[ "$1" == -r ]]; then printf '3.18.41+\n'; else printf 'aarch64\n'; fi; }
lsblk() {
 case "$*" in
 '-brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT')
  if [[ "$CASE" == gpt-missing ]]; then return; fi
  printf '/dev/mmcblk0p31 boot2 part 16777216 0\n'
  if [[ "$CASE" == gpt-duplicate ]]; then printf '/dev/mmcblk0p30 boot2 part 16777216 0\n'; fi ;;
 '-dnro PKNAME /dev/mmcblk0p31') printf 'mmcblk0\n' ;;
 '-dnro MAJ:MIN /dev/mmcblk0p31') printf '179:31\n' ;;
 *) return 1 ;;
 esac
}
readlink() {
 if [[ "$*" == '-f /dev/disk/by-partlabel/boot2' ]]; then printf '/dev/mmcblk0p31\n'; else guard_readlink "$@"; fi
}
cat() {
 case "${@: -1}" in
 /proc/sys/kernel/random/boot_id) printf '%s\n' "$EXPECTED_BOOT_ID" ;;
 /sys/class/power_supply/battery/present) printf '1\n' ;;
 /sys/class/power_supply/battery/capacity)
  if [[ "$CASE" == low-power ]]; then printf '20\n'; else printf '100\n'; fi ;;
 /sys/class/power_supply/battery/health) printf 'Good\n' ;;
 *) guard_cat "$@" ;;
 esac
}
blockdev() {
 case "$1" in
 --getsize64) printf '16777216\n' ;;
 --getro) printf '0\n' ;;
 --flushbufs) printf 'flush\n' >>"$FIXTURE/actions" ;;
 *) return 1 ;;
 esac
}
stat() {
 if [[ "${@: -1}" == "$EXPECTED_STAGE" ]]; then
  printf 'gemini 600 16777216\n'
 else guard_stat "$@"; fi
}
sha256sum() {
 if [[ "$1" == "$EXPECTED_STAGE" ]]; then
  # A mount appearing after initial validation must block the following dd.
  if [[ "$CASE" == mounted-before-write ]]; then
   printf '38 36 179:31 / /hidden rw - ext4 /dev/root rw\n' >>"$FIXTURE/mountinfo"
  fi
  if [[ "$CASE" == root-before-write ]]; then
   printf '36 1 179:30 / / rw - ext4 /dev/root rw\n' >"$FIXTURE/mountinfo"
  fi
  if [[ "$CASE" == stage-corrupt ]]; then printf '%064d  stage\n' 0; else printf '%s  stage\n' "$EXPECTED_CANDIDATE"; fi
 elif [[ "$1" == /dev/mmcblk0p31 ]]; then
  if [[ -e "$FIXTURE/written" && "$CASE" != readback-corrupt ]]; then
   printf '%s  target\n' "$EXPECTED_CANDIDATE"
  else printf '%s  target\n' "$INITIAL_SHA"; fi
 else return 1; fi
}
dd() {
 [[ "$*" == "if=$EXPECTED_STAGE of=/dev/mmcblk0p31 bs=4M iflag=fullblock count=4 conv=fsync,notrunc status=none" ]] || return 1
 printf 'write\n' >>"$FIXTURE/actions"
 : >"$FIXTURE/written"
}
sync() { printf 'sync\n' >>"$FIXTURE/actions"; }
sleep() { [[ "$1" == 2 ]]; }
# Extra applets are required by the historical gate but must never be used.
findmnt() { return 99; }
swapon() { return 99; }
'''
remote = remote.replace(marker, '\n' + mocks + marker)
# Power external-source readability is synthetic too; no real /sys read occurs.
power_anchor = '[[ ! -r "$online" ]] || external=$((external + $(cat "$online")))'
assert remote.count(power_anchor) == 1
remote = remote.replace(power_anchor, ': # fixture has no external supply')
# Stage exists only in the managed temp tree, never the device home directory.
stage_anchor = next(line.strip().removesuffix(" ||") for line in remote.splitlines() if line.strip().startswith('[[ "$EXPECTED_STAGE" =~'))
assert remote.count(stage_anchor) == 1
remote = remote.replace(stage_anchor, '[[ "$EXPECTED_STAGE" == "$FIXTURE/stage" ]]')

cases = ('probe-pass', 'probe-current', 'post-pass', 'write-pass', 'gpt-missing', 'gpt-duplicate',
         'mounted', 'root-target', 'root-unknown', 'holder', 'swap', 'low-power',
         'root-stage-change', 'target-stage-change', 'predecessor-change', 'stage-corrupt',
         'mounted-before-write', 'root-before-write', 'readback-corrupt')
with tempfile.TemporaryDirectory(prefix='gemini-v4-deploy-shell-', dir='/tmp') as temporary:
 for case in cases:
  root = Path(temporary)/case
  root.mkdir()
  defaults = {
   'target-stat': 'block special file|b3:1f\n', 'root-stat': 'block special file|b3:1d\n',
   'target-sys-path': '/sys/devices/platform/mmc/block/mmcblk0/mmcblk0p31\n',
   'root-sys-path': '/sys/devices/platform/mmc/block/mmcblk0/mmcblk0p29\n',
   'target-dev': '179:31\n', 'partition': '31\n', 'mountinfo': shared.ROOT+shared.PROC,
   'namespace': 'mnt:[4026531840]\n', 'swaps': shared.SWAP_HEADER,
   'holders': '', 'parent-holders': '', 'actions': '', 'stage': 'synthetic, no image data\n',
  }
  if case == 'mounted': defaults['mountinfo'] += '38 36 179:31 / /hidden rw - ext4 /dev/root rw\n'
  if case == 'root-target': defaults['mountinfo'] = shared.ROOT.replace('179:29', '179:31')
  if case == 'root-unknown': defaults['mountinfo'] = shared.ROOT.replace('179:29', '0:7')
  if case == 'holder': defaults['holders'] = '/sys/dev/block/179:31/holders/dm-0\n'
  if case == 'swap': defaults['swaps'] += '/dev/disk/by-uuid/target partition 1024 0 -1\n'
  for name, value in defaults.items(): (root/name).write_text(value)
  candidate = 'c'*64
  initial = candidate if case in ('probe-current', 'post-pass') else 'a'*64
  mode = 'probe' if case.startswith('probe-') else 'post' if case == 'post-pass' else 'write'
  env = dict(os.environ, FIXTURE=str(root), CASE=case, INITIAL_SHA=initial,
             GATE_MODE=mode, EXPECTED_BOOT_ID='11111111-1111-4111-8111-111111111111',
             EXPECTED_SIZE='16777216', EXPECTED_PREDECESSOR='none' if mode=='probe' else 'b'*64 if case=='predecessor-change' else initial,
             EXPECTED_CANDIDATE=candidate, EXPECTED_STAGE=str(root/'stage') if mode=='write' else 'none',
             EXPECTED_ROOT_NUMBER='179:28' if case=='root-stage-change' else '',
             EXPECTED_TARGET_NUMBER='179:30' if case=='target-stage-change' else '')
  result = subprocess.run(['bash','-c',remote], env=env, capture_output=True, text=True, timeout=10)
  actions = (root/'actions').read_text().splitlines()
  passed = case in ('probe-pass','probe-current','post-pass','write-pass')
  assert (result.returncode==0)==passed, (case,result.stdout,result.stderr)
  writes = actions.count('write')
  assert writes == (1 if case in ('write-pass','readback-corrupt') else 0), (case,actions)
  if writes: assert actions == ['write','sync','flush','sync'], (case,actions)
  if passed:
   assert 'root_major_minor=179:29\n' in result.stdout and 'target_major_minor=179:31\n' in result.stdout
  else: assert 'gate=passed\n' not in result.stdout
print(f'deployment_shell_cases={len(cases)} pre_write_refusals=pass write_budget=pass real_device_access=none')
