#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Source-pinned cooperative cancellation for the inherited finite workers."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'experiments/2026-09-02-mainline-dual-a72-concurrent-multiline/scripts/device-concurrent-multiline.sh'
SOURCE_SHA='c6bc8a26f2f79487d1bbfd9c8a294e589afd02ba17acf31647736dff7f100316'
CANCEL='/run/.gemini-a72-concurrent-cancel'
STOP=r'''pid8=
pid9=
reader_pid8=
reader_pid9=
spawn_in_progress=0
pending_exit=0

# shellcheck disable=SC2329,SC2317 # Invoked with a status by signal traps.
request_exit()
{
	if [ "$spawn_in_progress" = 1 ]; then
		pending_exit=$1
	else
		exit "$1"
	fi
}

stop_workers()
{
	# Only our workers inspect this RAM flag. Never signal a numeric PID.
	[ -n "$pid8$pid9$reader_pid8$reader_pid9" ] || return 0
	cancel_status=0
	$BB touch "$CANCEL" || cancel_status=1
	# wait targets are unreleased child handles; statuses may indicate cancel.
	if [ -n "$pid8" ]; then wait "$pid8" || :; pid8=; fi
	if [ -n "$pid9" ]; then wait "$pid9" || :; pid9=; fi
	if [ -n "$reader_pid8" ]; then wait "$reader_pid8" || :; reader_pid8=; fi
	if [ -n "$reader_pid9" ]; then wait "$reader_pid9" || :; reader_pid9=; fi
	return "$cancel_status"
}

'''


def replace_exact(text,old,new,count=1):
    if text.count(old)!=count:raise ValueError('worker cleanup source anchor changed')
    return text.replace(old,new)


def transform(source):
    if hashlib.sha256(source.encode()).hexdigest()!=SOURCE_SHA:
        raise ValueError('inherited worker source changed')
    result=replace_exact(source,'START_READ=/run/.gemini-a72-concurrent-start-read\n',
                         'START_READ=/run/.gemini-a72-concurrent-start-read\nCANCEL='+CANCEL+'\n\n'+STOP)
    result=replace_exact(result,'cleanup()\n{\n',
                         'cleanup()\n{\n\ttrap "" HUP INT TERM PIPE\n\tstop_workers || return 1\n')
    result=replace_exact(result,'"$START_WRITE" "$START_READ"','"$START_WRITE" "$START_READ" "$CANCEL"',2)
    result=replace_exact(result,"\tfor output in",'\tstop_workers || exit 3\n\tfor output in')
    result=replace_exact(result,'trap cleanup EXIT HUP INT TERM',
                         "trap cleanup EXIT\ntrap 'request_exit 129' HUP\ntrap 'request_exit 130' INT\ntrap 'request_exit 143' TERM\ntrap 'request_exit 141' PIPE")
    result=replace_exact(result,'trap - EXIT HUP INT TERM','trap - EXIT HUP INT TERM PIPE')
    # Defer caught signals across fork/$! registration; cleanup must own every child.
    for mask in ('100','200'):
        result=replace_exact(result,f"$BB taskset {mask} $BB sh -c '",
                             f"spawn_in_progress=1\n$BB taskset {mask} $BB sh -c '",2)
    for pid in ('pid8','pid9','reader_pid8','reader_pid9'):
        result=replace_exact(result,f'\n{pid}=$!\n',
                             f'\n{pid}=$!\nspawn_in_progress=0\n[ "$pending_exit" = 0 ] || exit "$pending_exit"\n')
    # Failure cancellation is the only change inside the four bounded bodies.
    result=replace_exact(result,'BB=/bin/busybox\nprefix=$1',
                         'BB=/bin/busybox\ncancel='+CANCEL+'\nprefix=$1',4)
    result=replace_exact(result,'while [ ! -e "$start" ]; do\n',
                         'while [ ! -e "$start" ]; do\n\t[ ! -e "$cancel" ] || exit 24\n',4)
    result=replace_exact(result,'while [ "$done_rounds" -lt "$rounds" ]; do\n',
                         'while [ "$done_rounds" -lt "$rounds" ]; do\n\t[ ! -e "$cancel" ] || exit 24\n',4)
    for pid,status in (('pid8','writer8_status'),('pid9','writer9_status'),('reader_pid8','reader8_status'),('reader_pid9','reader9_status')):
        result=replace_exact(result,f'wait "${pid}"; {status}=$?\n',f'wait "${pid}"; {status}=$?; {pid}=\n')
    for gate in (
        '[ -d /run ] && [ -w /run ] || finish_failure run-not-writable',
        '[ "$writer8_status" = 0 ] && [ "$writer9_status" = 0 ] || finish_failure writer-child-failed',
        '[ "$reader8_status" = 0 ] && [ "$reader9_status" = 0 ] || finish_failure reader-child-failed',
    ):
        result=replace_exact(result,gate,'# shellcheck disable=SC2015 # Either failed condition must reject.\n'+gate)
    return result


def materialize():
    if SOURCE.is_symlink():raise ValueError('unsafe source')
    return transform(SOURCE.read_text())

if __name__=='__main__':print(materialize(),end='')
