#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a prospective recovery program offline; no transport or admission."""
import argparse
import hashlib
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT_SHA = 'ab9d08ec8307e249d4ca45840ff7c31377136a07d51d62aa3a3d4d227fd6fe84'
CLOSED = '056703de-bf29-4956-891e-ff69d19fdd68'


def parent():
    path = HERE / 'build-attribution-runtime.py'
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA:
        raise ValueError('attribution builder changed')
    spec = importlib.util.spec_from_file_location('attribution_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECOVERY = r'''# Re-arm caught signals after the successful cleanup join.
trap 'request_exit 129' HUP
trap 'request_exit 130' INT
trap 'request_exit 143' TERM
trap 'request_exit 141' PIPE
recovery_quiescent()
{
	[ -z "$pid8$pid9$reader_pid8$reader_pid9" ] || finish_failure recovery-unreaped-worker
	[ "$spawn_in_progress" = 0 ] || finish_failure recovery-pending-spawn
	[ "$pending_exit" = 0 ] || finish_failure recovery-pending-exit
	for item in "$FILE8" "$FILE9" "$OUT8" "$OUT9" "$READ8" "$READ9" \
		"$START_WRITE" "$START_READ" "$CANCEL"; do
		# shellcheck disable=SC2015 # Both absence checks are required.
		[ ! -e "$item" ] && [ ! -L "$item" ] || finish_failure recovery-cleanup-residue
	done
}
recovery_quiescent
$BB printf '%s\n' recovery_workers_before=quiescent recovery_files_before=absent
$BB printf '%s\n' recovery_sleep_requested_seconds=2
$BB sleep 2 || finish_failure recovery-sleep-failed
recovery_quiescent
$BB printf '%s\n' recovery_workers_after=quiescent recovery_files_after=absent
recovery_snapshot recovery
$BB printf '%s\n' "$snapshot_record" | $BB awk -v previous="$completion_end_ns" '
NR == 1 {
	split($9,a,"="); gap=a[2]-previous
	if (gap<2000000000 || gap>3000000000) exit 3
}' || finish_failure recovery-timing
$BB printf '%s\n' recovery_timing=within-declared-window
'''


def build(boot):
    base = parent()
    if boot == CLOSED:
        raise ValueError('consumed attribution boot')
    out = base.build(boot)
    replace = base.replace_exact
    fragment = base.checked(HERE / 'attribution-observer.sh', base.OBSERVER_SHA)
    replacement = replace(fragment, 'attribution_observe()', 'recovery_snapshot()')
    replacement = replace(replacement,
        'case "$label" in before) attempt=1;; during) attempt=2;; after) attempt=3;; *) frequency_reject snapshot-stage;; esac',
        'case "$label" in before) attempt=1;; after) attempt=2;; recovery) attempt=3;; *) frequency_reject snapshot-stage;; esac')
    frequency = '\tobservation=$($BB cat "$FREQUENCY_OBSERVER" 2>/dev/null) || frequency_reject "frequency-${label}"\n\t$BB printf \'frequency_%s=%s\\n\' "$label" "$observation"\n'
    replacement = replace(replacement, frequency, '')
    replacement = replacement.replace('__THERMAL_ATTRIBUTION_', '__THERMAL_RECOVERY_')
    replacement = replace(replacement, 'if (value<0 || value>58500) bad=1',
                          'if (value<0 || value>58500 || value%100!=0) bad=1')
    replacement += '''\nrecovery_frequency()
{
	label=$1
	case "$label" in before|during|after) ;; *) frequency_reject frequency-stage;; esac
	observation=$($BB cat "$FREQUENCY_OBSERVER" 2>/dev/null) || frequency_reject "frequency-${label}"
	$BB printf 'frequency_%s=%s\\n' "$label" "$observation"
}
'''
    out = replace(out, fragment, replacement)
    out = replace(out, 'attribution_observe before', 'recovery_frequency before\nrecovery_snapshot before')
    out = replace(out, 'attribution_observe during', 'recovery_frequency during')
    out = replace(out, 'attribution_observe after', '''recovery_frequency after
recovery_snapshot after
completion_end_ns=$($BB printf '%s\\n' "$snapshot_record" | $BB awk 'NR==1 {split($10,a,"="); print a[2]}')''')
    # Insert only on the successful main path, never inside failure cleanup.
    anchor = '''cleanup
$BB printf 'cleanup_file8=%s\\n' "$(file_state "$FILE8")"'''
    out = replace(out, anchor, 'cleanup || finish_failure recovery-cleanup-failed\n' + RECOVERY +
                  '$BB printf \'cleanup_file8=%s\\n\' "$(file_state "$FILE8")"')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boot-id', required=True)
    print(build(parser.parse_args().boot_id), end='')


if __name__ == '__main__':
    main()
