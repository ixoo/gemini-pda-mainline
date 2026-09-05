#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the generated remote gate against injected Linux block/tmpfs metadata."""
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from installer import REPO, derive, pinned_sources

SHARED = runpy.run_path(str(REPO / 'scripts/boot2-device-guard-test.py'))
MOCKS = SHARED['MOCKS'].split('# Exercise callers')[0] + r'''
eval "$(declare -f cat | sed '1s/^cat /guard_cat /')"
eval "$(declare -f readlink | sed '1s/^readlink /guard_readlink /')"
eval "$(declare -f stat | sed '1s/^stat /guard_stat /')"
fixture_block() { [[ "$1" == /dev/mmcblk0p31 ]]; }
id() { if [[ "$*" == '-u gemini' ]]; then printf '1000\n'; else printf '0\n'; fi; }
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
 case "${@: -1}" in
 /dev/disk/by-partlabel/boot2) printf '/dev/mmcblk0p31\n' ;;
 /dev/shm) if [[ "$CASE" == tmpfs-alias ]]; then printf '/elsewhere\n'; else printf '/dev/shm\n'; fi ;;
 *) guard_readlink "$@" ;;
 esac
}
cat() {
 case "${@: -1}" in
 /proc/sys/kernel/random/boot_id) printf '%s\n' "$EXPECTED_BOOT_ID" ;;
 /sys/class/power_supply/battery/present) printf '1\n' ;;
 /sys/class/power_supply/battery/capacity) if [[ "$CASE" == low-power ]]; then printf '20\n'; else printf '100\n'; fi ;;
 /sys/class/power_supply/battery/health) printf 'Good\n' ;;
 *) guard_cat "$@" ;;
 esac
}
blockdev() {
 case "$1" in
 --getsize64) printf '16777216\n' ;;
 --getro) printf '0\n' ;;
 --flushbufs) printf 'flush\n' >>"$FIXTURE/actions"; [[ "$CASE" != flush-failed ]] ;;
 *) return 1 ;;
 esac
}
findmnt() {
 [[ "$*" == '-rn -o TARGET,FSTYPE --target /dev/shm' ]] || return 99
 if [[ "$CASE" == persistent-stage || "$CASE" == mount-before-write && -f "$FIXTURE/stage-hashed" ]]; then
  printf '/dev/shm ext4\n'
 elif [[ "$CASE" == tmpfs-parent ]]; then printf '/ tmpfs\n'
 else printf '/dev/shm tmpfs\n'; fi
}
stat() {
 local path=${@: -1}
 if [[ "$path" == /dev/shm ]]; then
  if [[ "$CASE" == tmpfs-owner ]]; then printf '1000 1777\n'
  elif [[ "$CASE" == tmpfs-mode ]]; then printf '0 777\n'
  else printf '0 1777\n'; fi
 elif [[ "$path" == "$EXPECTED_STAGE" ]]; then
  if [[ "$*" == "-c %s -- $EXPECTED_STAGE" ]]; then
   if [[ "$CASE" == stage-short ]]; then printf '512\n'; else printf '16777216\n'; fi
  else
   if [[ "$CASE" == stage-owner ]]; then printf '0 600 16777216 1\n'
   elif [[ "$CASE" == stage-mode || "$CASE" == mode-before-write && -f "$FIXTURE/stage-hashed" ]]; then printf '1000 644 16777216 1\n'
   elif [[ "$CASE" == stage-links ]]; then printf '1000 600 16777216 2\n'
   else printf '1000 600 16777216 1\n'; fi
  fi
 else guard_stat "$@"; fi
}
sha256sum() {
 if [[ "$1" == "$EXPECTED_STAGE" ]]; then
  : >"$FIXTURE/stage-hashed"
  if [[ "$CASE" == mounted-before-write ]]; then printf '38 36 179:31 / /hidden rw - ext4 /dev/root rw\n' >>"$FIXTURE/mountinfo"; fi
  if [[ "$CASE" == root-before-write ]]; then printf '36 1 179:30 / / rw - ext4 /dev/root rw\n' >"$FIXTURE/mountinfo"; fi
  if [[ "$CASE" == swap-before-write ]]; then printf '/dev/mmcblk0p30 partition 100 0 -1\n' >>"$FIXTURE/swaps"; fi
  if [[ "$CASE" == stage-corrupt ]]; then printf '%064d  stage\n' 0; else printf '%s  stage\n' "$EXPECTED_CANDIDATE"; fi
 elif [[ "$1" == /dev/mmcblk0p31 ]]; then
  if [[ -e "$FIXTURE/written" && "$CASE" != readback-corrupt ]]; then printf '%s  target\n' "$EXPECTED_CANDIDATE"
  else printf '%s  target\n' "$INITIAL_SHA"; fi
 else return 1; fi
}
dd() {
 [[ "$*" == "if=$EXPECTED_STAGE of=/dev/mmcblk0p31 bs=4M iflag=fullblock count=4 conv=fsync,notrunc status=none" ]] || return 1
 printf 'write\n' >>"$FIXTURE/actions"
 [[ "$CASE" != write-failed ]] || return 2
 : >"$FIXTURE/written"
}
sync() { printf 'sync\n' >>"$FIXTURE/actions"; [[ "$CASE" != sync-failed ]]; }
sleep() { [[ "$1" == 2 ]]; }
swapon() { return 99; }
'''


class RemoteTests(unittest.TestCase):
    def test_actual_stage_prepare_upload_cleanup(self):
        with tempfile.TemporaryDirectory(prefix='a53-stage-fixture-', dir='/private/tmp' if Path('/private/tmp').is_dir() else '/tmp') as temporary:
            root = Path(temporary)
            candidate = root / ('candidate-' + '1' * 64)
            candidate.mkdir()
            (candidate / 'candidate.json').write_text('{}')
            (candidate / 'boot2-padded.img').write_bytes(b'inert')
            source = derive(pinned_sources(), REPO, candidate, candidate, candidate)
            preparation = source.split("<<'A53_STAGE'\n")[1].split('\nA53_STAGE\n')[0]
            assignment = source.split('\tupload_command=')[1].split('\n\t"${ssh_command[@]}"')[0]
            command = subprocess.check_output(['bash', '-c', 'upload_command=' + assignment + '\nprintf "%s" "$upload_command"'], text=True)
            upload = shlex.split(command)[2]
            mocks = r'''
readlink() { printf '%s\n' "$STAGE_ROOT"; }
findmnt() { printf '%s %s\n' "$STAGE_ROOT" "${FILESYSTEM:-tmpfs}"; }
id() { printf '%s\n' "$FIXTURE_UID"; }
df() { printf 'Filesystem 1-blocks Used Available Capacity Mounted\ntmpfs 99999999 0 %s 0%% %s\n' "${AVAILABLE:-99999999}" "$STAGE_ROOT"; }
stat() {
 if [[ "${@: -1}" == "$STAGE_ROOT" ]]; then printf '0 1777\n'; return; fi
 python3 -c 'import os,stat,sys; s=os.lstat(sys.argv[1]); print(s.st_size if sys.argv[2]=="%s" else "%s %s %s %s" % (s.st_uid,format(stat.S_IMODE(s.st_mode),"o"),s.st_size,s.st_nlink))' "${@: -1}" "$2"
}
'''
            cases = ('pass', 'stale-pass', 'stale-mode', 'stale-symlink', 'stale-hardlink',
                     'multiple-stale', 'active-swap', 'bad-swap-table', 'persistent', 'low-space')
            for case in cases:
                with self.subTest(case=case):
                    work = root / case
                    work.mkdir()
                    shm = work / 'shm'
                    shm.mkdir()
                    swaps = work / 'swaps'
                    swaps.write_text(SHARED['SWAP_HEADER'] + ('/dev/mmcblk0p30 partition 100 0 -1\n' if case == 'active-swap' else ''))
                    if case == 'bad-swap-table': swaps.write_text('invalid\n')
                    sha = 'c' * 64
                    stale = shm / ('.gemini-a53-' + sha + '.old00001')
                    if case.startswith('stale-') or case == 'multiple-stale':
                        stale.write_bytes(b'old')
                        stale.chmod(0o600)
                        if case == 'stale-mode': stale.chmod(0o644)
                        if case == 'stale-symlink':
                            stale.unlink(); stale.symlink_to(swaps)
                        if case == 'stale-hardlink': os.link(stale, work / 'linked')
                        if case == 'multiple-stale':
                            (shm / ('.gemini-a53-' + sha + '.old00002')).write_bytes(b'old')
                    text = preparation.replace('/dev/shm', str(shm)).replace('/proc/swaps', str(swaps))
                    # All production stage branches execute. Only platform
                    # metadata and filesystem paths are replaced in fixtures.
                    text = text.replace('umask 077\n', 'umask 077\n' + mocks)
                    env = dict(os.environ, STAGE_ROOT=str(shm), FIXTURE_UID=str(os.getuid()),
                               EXPECTED_STAGE='none', EXPECTED_CANDIDATE=sha, EXPECTED_SIZE='4', STAGE_ACTION='prepare',
                               AVAILABLE='0' if case == 'low-space' else '99999999', FILESYSTEM='ext4' if case == 'persistent' else 'tmpfs')
                    result = subprocess.run(['bash', '-c', text], env=env, text=True, capture_output=True, timeout=5)
                    admitted = case in ('pass', 'stale-pass')
                    self.assertEqual(result.returncode == 0, admitted, result.stderr)
                    if not admitted:
                        if case.startswith('stale-') or case == 'multiple-stale':
                            self.assertTrue(stale.exists() or stale.is_symlink())
                        continue
                    path = Path(result.stdout.strip())
                    self.assertEqual(path.parent, shm)
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(path.stat().st_size, 0)
                    upload_text = mocks + upload.replace('/dev/shm', str(shm)).replace('/proc/swaps', str(swaps))
                    for payload, expected in ((b'ab', False), (b'abcd', True)):
                        path.write_bytes(b'')
                        sent = subprocess.run(['bash', '-c', upload_text, 'a53-fixture', str(path), sha, '4'],
                                              env=env, input=payload, capture_output=True, timeout=5)
                        self.assertEqual(sent.returncode == 0, expected, sent.stderr)
                        self.assertEqual(path.read_bytes(), payload)
                    # A nonempty file cannot be silently overwritten.
                    blocked = subprocess.run(['bash', '-c', upload_text, 'a53-fixture', str(path), sha, '4'],
                                             env=env, input=b'XXXX', capture_output=True, timeout=5)
                    self.assertNotEqual(blocked.returncode, 0)
                    self.assertEqual(path.read_bytes(), b'abcd')
                    cleaned = subprocess.run(['bash', '-c', text], env=dict(env, STAGE_ACTION='cleanup', EXPECTED_STAGE=str(path)),
                                             text=True, capture_output=True, timeout=5)
                    self.assertEqual(cleaned.returncode, 0, cleaned.stderr)
                    self.assertFalse(path.exists())
            print('generated_stage_cases=' + str(len(cases)) + ' device_access=none')

    def test_actual_remote_gate(self):
        with tempfile.TemporaryDirectory(prefix='a53-remote-fixture-', dir='/private/tmp' if Path('/private/tmp').is_dir() else '/tmp') as temporary:
            root = Path(temporary)
            candidate = root / ('candidate-' + '1' * 64)
            candidate.mkdir()
            (candidate / 'candidate.json').write_text('{}')
            (candidate / 'boot2-padded.img').write_bytes(b'inert')
            derived = derive(pinned_sources(), REPO, candidate, candidate, candidate)
            remote = derived.split("<<'REMOTE'\n")[1].split('\nREMOTE\n')[0]
            substitutions = {
                '[[ -z "${mountpoint:-}" && -z "${extra:-}" && -b "$target" ]]':
                    '[[ -z "${mountpoint:-}" && -z "${extra:-}" ]] && fixture_block "$target"',
                '[[ ! -r "$online" ]] || external=$((external + $(cat "$online")))': ': # no external fixture supply',
                '[[ -d /dev/shm && ! -L /dev/shm ]]': '[[ -d "$FIXTURE/shm" && ! -L "$FIXTURE/shm" ]]',
                '[[ -f "$stage" && ! -L "$stage" ]]': '[[ -f "$FIXTURE/stage" && ! -L "$FIXTURE/stage" ]]',
                "' /proc/swaps\n": "' \"$FIXTURE/swaps\"\n",
                '\nfor command in awk blockdev cat dd find findmnt id lsblk readlink sha256sum sleep ':
                    '\n' + MOCKS + '\nfor command in awk blockdev cat dd find findmnt id lsblk readlink sha256sum sleep ',
            }
            for old, new in substitutions.items():
                self.assertEqual(remote.count(old), 1, old)
                remote = remote.replace(old, new)
            cases = ('probe-pass', 'probe-current', 'post-pass', 'write-pass', 'gpt-missing', 'gpt-duplicate',
                     'mounted', 'root-target', 'root-unknown', 'holder', 'swap', 'low-power',
                     'root-stage-change', 'target-stage-change', 'predecessor-change', 'stage-corrupt',
                     'mounted-before-write', 'root-before-write', 'readback-corrupt', 'persistent-stage',
                     'tmpfs-parent', 'tmpfs-alias', 'tmpfs-owner', 'tmpfs-mode', 'tmpfs-symlink',
                     'stage-owner', 'stage-mode', 'stage-links', 'stage-short', 'stage-symlink', 'unsafe-stage',
                     'other-swap', 'mount-before-write', 'swap-before-write', 'mode-before-write',
                     'write-failed', 'sync-failed', 'flush-failed')
            for case in cases:
                with self.subTest(case=case):
                    work = root / case
                    work.mkdir()
                    (work / 'shm').mkdir()
                    values = {'target-stat': 'block special file|b3:1f\n', 'root-stat': 'block special file|b3:1d\n',
                        'target-sys-path': '/sys/devices/platform/mmc/block/mmcblk0/mmcblk0p31\n',
                        'root-sys-path': '/sys/devices/platform/mmc/block/mmcblk0/mmcblk0p29\n',
                        'target-dev': '179:31\n', 'partition': '31\n', 'mountinfo': SHARED['ROOT'] + SHARED['PROC'],
                        'namespace': 'mnt:[4026531840]\n', 'swaps': SHARED['SWAP_HEADER'],
                        'holders': '', 'parent-holders': '', 'actions': '', 'stage': 'synthetic bytes\n'}
                    if case == 'mounted': values['mountinfo'] += '38 36 179:31 / /hidden rw - ext4 /dev/root rw\n'
                    if case == 'root-target': values['mountinfo'] = SHARED['ROOT'].replace('179:29', '179:31')
                    if case == 'root-unknown': values['mountinfo'] = SHARED['ROOT'].replace('179:29', '0:7')
                    if case == 'holder': values['holders'] = '/sys/dev/block/179:31/holders/dm-0\n'
                    if case == 'swap': values['swaps'] += '/dev/disk/by-uuid/target partition 1024 0 -1\n'
                    if case == 'other-swap': values['swaps'] += '/dev/mmcblk0p30 partition 1024 0 -1\n'
                    for name, value in values.items(): (work / name).write_text(value)
                    if case == 'tmpfs-symlink':
                        (work / 'shm').rmdir(); (work / 'shm').symlink_to(work)
                    if case == 'stage-symlink':
                        (work / 'stage').unlink(); (work / 'stage').symlink_to(work / 'actions')
                    candidate_sha = 'c' * 64
                    initial = candidate_sha if case in ('probe-current', 'post-pass') else 'a' * 64
                    mode = 'probe' if case.startswith('probe-') else 'post' if case == 'post-pass' else 'write'
                    stage = '/dev/shm/.gemini-a53-' + candidate_sha + '.abcd1234'
                    if case == 'unsafe-stage': stage = '/persistent-fixture/old-stage'
                    env = dict(os.environ, FIXTURE=str(work), CASE=case, INITIAL_SHA=initial, GATE_MODE=mode,
                        EXPECTED_BOOT_ID='11111111-1111-4111-8111-111111111111', EXPECTED_SIZE='16777216',
                        EXPECTED_PREDECESSOR='none' if mode == 'probe' else 'b' * 64 if case == 'predecessor-change' else initial,
                        EXPECTED_CANDIDATE=candidate_sha, EXPECTED_STAGE=stage if mode == 'write' else 'none',
                        EXPECTED_ROOT_NUMBER='179:28' if case == 'root-stage-change' else '',
                        EXPECTED_TARGET_NUMBER='179:30' if case == 'target-stage-change' else '')
                    result = subprocess.run(['bash', '-c', remote], env=env, text=True, capture_output=True, timeout=10)
                    actions = (work / 'actions').read_text().splitlines()
                    passed = case in ('probe-pass', 'probe-current', 'post-pass', 'write-pass')
                    self.assertEqual(result.returncode == 0, passed, (result.stdout, result.stderr))
                    written = case in ('write-pass', 'readback-corrupt', 'write-failed', 'sync-failed', 'flush-failed')
                    self.assertEqual(actions.count('write'), int(written), actions)
                    expected_actions = [] if not written else ['write'] if case == 'write-failed' else ['write', 'sync'] if case == 'sync-failed' else ['write', 'sync', 'flush'] if case == 'flush-failed' else ['write', 'sync', 'flush', 'sync']
                    self.assertEqual(actions, expected_actions)
                    self.assertEqual('gate=passed\n' in result.stdout, passed)
            print('generated_remote_gate_cases=' + str(len(cases)) + ' device_access=none')


if __name__ == '__main__':
    unittest.main(verbosity=2)
