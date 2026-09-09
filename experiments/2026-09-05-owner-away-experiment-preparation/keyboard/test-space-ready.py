#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ARM64 helper with a real PTY and injected evdev/VT metadata; no device access."""
import argparse
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import termios
import time

HERE = Path(__file__).resolve().parent
FIXTURE = r'''
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <sys/sysmacros.h>
#include <linux/input.h>
#include <linux/kd.h>
#include <linux/vt.h>
#include <unistd.h>
static int input_fd = -1, console_fd = -1;
static int fake_open(const char *path, int flags, ...)
{
    (void)flags;
    if (!strcmp(path, "/dev/input/event0"))
        return input_fd = dup(atoi(getenv("INPUT_FD")));
    if (!strcmp(path, "/dev/tty1"))
        return console_fd = dup(atoi(getenv("CONSOLE_FD")));
    return -1;
}
static int fake_stat(int fd, struct stat *s)
{
    if (fstat(fd, s)) return -1;
    s->st_mode = S_IFCHR | 0600;
    s->st_rdev = fd == input_fd ? makedev(13, 64) : makedev(4, 1);
    return 0;
}
static int fake_ioctl(int fd, unsigned long request, ...)
{
    va_list args;
    va_start(args, request);
    void *out = va_arg(args, void *);
    va_end(args);
    if (fd == input_fd && request == EVIOCGNAME(127)) {
        strcpy(out, "keyboard-matrix"); return 16;
    }
    if (fd == input_fd && request == EVIOCGKEY(96)) {
        memset(out, 0, 96); return 96;
    }
    if (fd == console_fd && request == VT_GETSTATE) {
        ((struct vt_stat *)out)->v_active = 1; return 0;
    }
    if (fd == console_fd && request == KDGKBMODE) {
        *(int *)out = K_UNICODE; return 0;
    }
    return -1;
}
#define open fake_open
#define fstat fake_stat
#define ioctl fake_ioctl
#define WAIT_MS 2000
#define WAIT_REPORT_MS 200
#include "space-ready.c"
'''


def run_case(binary, qemu, name, events=None, text=b'', cancel=False, expected=2):
    master, slave = pty.openpty()
    reader, writer = os.pipe()
    before = termios.tcgetattr(slave)
    process = None
    try:
        process = subprocess.Popen([qemu, str(binary), 'event0', '64'],
            pass_fds=(reader, slave), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, 'INPUT_FD': str(reader), 'CONSOLE_FD': str(slave)})
        prompt = b''
        deadline = time.monotonic() + 3
        while b'This screen waits' not in prompt and time.monotonic() < deadline:
            if select.select([master], [], [], .1)[0]:
                prompt += os.read(master, 4096)
            if process.poll() is not None:
                break
        assert b'Press and release SPACE' in prompt, (name, prompt)
        assert termios.tcgetattr(slave) != before, name
        if events:
            os.write(writer, b''.join(struct.pack('<qqHHi', 0, 0, *event) for event in events))
        if text:
            os.write(master, text)
        if cancel:
            process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=4)
        assert process.returncode == expected, (name, process.returncode, out, err)
        assert err == b'', (name, err)
        lines = out.splitlines(keepends=True)
        reports = [line for line in lines if line == b'space-ready=waiting\n']
        assert len(reports) <= 10, (name, out)
        final = b''.join(line for line in lines if line != b'space-ready=waiting\n')
        if expected == 0:
            assert final == b'space-ready=passed released=1 restored=1\n', (name, out)
        else:
            assert final.startswith(b'space-ready=failed reason=') and b' restored=1 ' in final, (name, out)
        if name == 'timeout':
            assert reports, 'waiting must emit channel activity'
        assert termios.tcgetattr(slave) == before, (name, 'termios not restored')
        print(name + '=pass')
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        for fd in (master, slave, reader, writer):
            os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--qemu', required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    source = args.work/'space-fixture.c'
    source.write_text(FIXTURE)
    binary = args.work/'space-fixture'
    subprocess.run([args.compiler, '-std=c11', '-static', '-Wall', '-Wextra', '-Werror',
        '-idirafter', '/usr/aarch64-linux-gnu/include', '-I', str(HERE), str(source), '-o', str(binary)], check=True)
    press, release, sync = (1, 57, 1), (1, 57, 0), (0, 0, 0)
    run_case(binary, args.qemu, 'press-release', [press, sync, release, sync], b' ', expected=0)
    run_case(binary, args.qemu, 'held-space-does-not-start', [press, sync], b' ')
    run_case(binary, args.qemu, 'wrong-key', [(1, 30, 1), sync], b'a')
    run_case(binary, args.qemu, 'release-without-press', [release, sync], b' ')
    run_case(binary, args.qemu, 'lost-events', [(0, 3, 0)])
    run_case(binary, args.qemu, 'timeout')
    run_case(binary, args.qemu, 'signal-restores-console', cancel=True)


if __name__ == '__main__':
    main()
