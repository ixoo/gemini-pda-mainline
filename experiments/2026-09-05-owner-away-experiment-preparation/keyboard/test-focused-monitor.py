#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ARM64 focused entry wiring and full deadline checks, using harmless children."""
import argparse
import os
from pathlib import Path
import runpy
import signal
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ENTRY = r'''
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static int parent_fd = -1;
static int fake_open(const char *path, int flags, ...)
{
    if (!strcmp(path, "/a53-keyboard-focused"))
        return parent_fd = open(getenv("FOCUSED_FIXTURE_PARENT"), flags);
    return open(path, flags);
}
static int fake_fstat(int fd, struct stat *st)
{
    if (fstat(fd, st)) return -1;
    if (fd == parent_fd) st->st_uid = 0;
    return 0;
}
static int fake_execl(const char *path, const char *name, ...)
{
    if (strcmp(path, "/a53-keyboard-focused/keyboard-observe") ||
        strcmp(name, "keyboard-observe")) _exit(120);
    const char *const expected[] = { "--diagnose", "event0", "13", "64" };
    va_list args;
    va_start(args, name);
    for (unsigned int i = 0; i < 4; i++) {
        const char *arg = va_arg(args, const char *);
        if (!arg || strcmp(arg, expected[i])) _exit(121);
    }
    if (va_arg(args, const char *) != NULL) _exit(122);
    va_end(args);
    if (write(1, "focused-exec-argv=pass\n", 23) != 23) _exit(123);
    _exit(0);
}
#define open fake_open
#define fstat fake_fstat
#define execl fake_execl
#define KEYBOARD_MONITOR_ENABLED 1
#define KEYBOARD_MONITOR_FOCUSED 1
#include "monitor.c"
'''


def entry_check(args):
    source = args.work/'focused-entry.c'
    binary = args.work/'focused-entry'
    source.write_text(ENTRY)
    subprocess.run([args.compiler, '-std=c11', '-static', '-Wall', '-Wextra', '-Werror',
                    '-I', str(HERE), str(source), '-o', str(binary)], check=True)
    with tempfile.TemporaryDirectory(dir=args.work) as parent:
        command = [args.qemu, str(binary), 'event0', '64']
        env = {**os.environ, 'FOCUSED_FIXTURE_PARENT': parent}
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True, env=env)
        try:
            out, err = process.communicate(timeout=5)
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
            raise
        assert (process.returncode, out, err) == (0, b'focused-exec-argv=pass\n', b''), (process.returncode, out, err)
        files = Path(parent)/'keyboard-attempt'
        before = {p.name: p.read_bytes() for p in files.iterdir()}
        second = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=3)
        assert second.returncode == 2
        assert before == {p.name: p.read_bytes() for p in files.iterdir()}
    print('focused-production-entry-and-once-only-claim=pass', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--qemu', required=True)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    entry_check(args)
    os.environ.update(MONITOR_TEST_CC=args.compiler, MONITOR_TEST_QEMU=args.qemu,
                      MONITOR_TEST_WORK_ROOT=str(args.work/'full-focused-monitor'),
                      MONITOR_TEST_FOCUSED='1', MONITOR_TEST_FULL_DURATION='1',
                      MONITOR_TEST_FIXTURE_ONLY='0')
    module = runpy.run_path(str(HERE/'test-monitor.py'))
    cls = module['MonitorTests']
    cls.run_case.__globals__['OUTER_SECONDS'] = 50
    case = cls()
    try:
        cls.setUpClass()
        case.setUp()
        code, out, err, fields = case.run_case('ignore')
        assert code == 2 and err == b''
        assert b'fixture-observation-boundary=32000\n' in out
        assert fields['reaped'] == '1' and fields['identity_lost'] == '0' and fields['late'] == '0'
        assert 39000 <= int(fields['term_ms']) <= 40000
        assert 43000 <= int(fields['kill_ms']) <= 44000
        assert int(fields['reap_ms']) <= 45000 and int(fields['signal']) == signal.SIGKILL
        print('focused-production-32s-observation-45s-cleanup=pass', flush=True)
    finally:
        case.doCleanups()
        cls.doClassCleanups()


if __name__ == '__main__':
    main()
