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
    {
        input_fd = dup(atoi(getenv("INPUT_FD")));
        if (input_fd >= 0) fcntl(input_fd, F_SETFL, O_NONBLOCK);
        return input_fd;
    }
    if (!strcmp(path, "/dev/tty1")) {
        console_fd = dup(atoi(getenv("CONSOLE_FD")));
        if (console_fd >= 0) fcntl(console_fd, F_SETFL, O_NONBLOCK);
        return console_fd;
    }
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
        memset(out, 0, 96);
        if (getenv("STATE_CASE")) ((unsigned char *)out)[56 / 8] = 1;
        return 96;
    }
    if (fd == console_fd && request == VT_GETSTATE) {
        ((struct vt_stat *)out)->v_active = 1; return 0;
    }
    if (fd == console_fd && request == KDGKBMODE) {
        *(int *)out = K_UNICODE; return 0;
    }
    if (fd == console_fd && request == TIOCLINUX) {
        if (*(unsigned char *)out != 6) abort();
        *(unsigned char *)out = 8; return 0;
    }
    if (fd == console_fd && request == KDGKBLED) {
        *(unsigned char *)out = 0; return 0;
    }
    if (fd == console_fd && request == KDGKBMETA) {
        *(int *)out = K_ESCPREFIX; return 0;
    }
    if (fd == console_fd && request == KDGKBENT) {
        if (getenv("STATE_CASE") && !strcmp(getenv("STATE_CASE"), "failure")) return -1;
        struct kbentry *entry = out;
        if (entry->kb_index != KEY_SPACE || entry->kb_table > 15) abort();
        entry->kb_value = 32; return 0;
    }
    if (fd == console_fd && request == TIOCGETD) {
        if (getenv("WRONG_LDISC")) { *(int *)out = 1; return 0; }
        return ioctl(fd, request, out);
    }
    if (fd == console_fd && request == TIOCSETD) {
        static int calls;
        if (++calls != 1 || *(int *)out != 0) abort();
        if (getenv("REFUSE_REQUEUE")) return -1;
        int result = ioctl(fd, request, out);
        if (!result && getenv("REQUEUE_FD"))
            if (write(atoi(getenv("REQUEUE_FD")), "queued", 6) != 6) abort();
        return result;
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
            pass_fds=(reader, slave, master), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, 'INPUT_FD': str(reader), 'CONSOLE_FD': str(slave),
                 **({'REQUEUE_FD': str(master)} if name == 'queued-prefix-before-space' else {})})
        prompt = b''
        deadline = time.monotonic() + 4
        while b'This screen waits' not in prompt and time.monotonic() < deadline:
            if select.select([master], [], [], .1)[0]:
                prompt += os.read(master, 4096)
            if process.poll() is not None:
                break
        assert b'Press and release SPACE' in prompt, (name, prompt)
        assert termios.tcgetattr(slave) != before, name
        if name == 'escape-preserves-pending-space':
            process.send_signal(signal.SIGSTOP)
            os.waitpid(process.pid, os.WUNTRACED)
        if events:
            os.write(writer, b''.join(struct.pack('<qqHHi', 0, 0, *event) for event in events))
        if text:
            os.write(master, text)
        if name == 'escape-preserves-pending-space':
            process.send_signal(signal.SIGCONT)
        if cancel:
            process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=4)
        assert process.returncode == expected, (name, process.returncode, out, err)
        assert err == b'', (name, err)
        lines = out.splitlines(keepends=True)
        reports = [line for line in lines if line == b'space-ready=waiting\n']
        assert len(reports) <= 10, (name, out)
        prefix, separator, rest = out.partition(b'space-ready=preflight-complete\n')
        assert separator, (name, out)
        assert prefix.startswith(b'console-drain requeue=accepted ldisc=0\n'), (name, out)
        if name == 'queued-prefix-before-space':
            assert b'console-drain bytes=6 hex=717565756564\n' in prefix, out
            assert prefix.endswith(b'console-drain empty=1 bytes=6\n'), out
        else:
            assert prefix.endswith(b'console-drain empty=1 bytes=0\n'), out
        final = b''.join(line for line in rest.splitlines(keepends=True)
                         if line != b'space-ready=waiting\n')
        if expected == 0:
            assert final == b'space-ready=passed released=1 restored=1\n', (name, out)
        else:
            assert final.startswith(b'space-ready=failed reason=') and b' restored=1 ' in final, (name, out)
        if name == 'escape-preserves-pending-space':
            assert b'console-read bytes=2 hex=1b20\n' in out, out
            assert b'pending type=1 code=57 value=1\n' in out, out
            assert b'pending type=1 code=57 value=0\n' in out, out
            assert len(out) <= 1024, out
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


def state_case(binary, qemu, failure=False):
    master, slave = pty.openpty()
    reader, writer = os.pipe()
    try:
        before = termios.tcgetattr(slave)
        os.write(writer, b'event-untouched')
        result = subprocess.run([qemu, str(binary), '--state', 'event0', '64'],
            pass_fds=(reader, slave), capture_output=True, timeout=3,
            env={**os.environ, 'INPUT_FD': str(reader), 'CONSOLE_FD': str(slave),
                 'STATE_CASE': 'failure' if failure else 'success'})
        assert result.returncode == (2 if failure else 0), result
        assert result.stderr == b'', result
        assert result.stdout.startswith(b'console-state version=1 shift=8 leds=0 meta=4 held=56,\n'), result
        assert (b'complete=1' in result.stdout) == (not failure), result
        assert termios.tcgetattr(slave) == before
        assert not select.select([master], [], [], 0)[0], 'unexpected console output'
        assert select.select([reader], [], [], 0)[0], 'event consumed'
        assert os.read(reader, 15) == b'event-untouched', 'event consumed'
        print(('state-query-failure' if failure else 'state-query-read-only') + '=pass')
    finally:
        for fd in (master, slave, reader, writer):
            os.close(fd)


def drain_case(binary, qemu):
    master, slave = pty.openpty()
    reader, writer = os.pipe()
    try:
        before = termios.tcgetattr(slave)
        os.write(master, b'n' * 64)
        # Observe the echo to establish delivery to the line discipline.
        echoed = b''
        while len(echoed) < 64:
            assert select.select([master], [], [], 1)[0]
            echoed += os.read(master, 4096)
        result = subprocess.run([qemu, str(binary), '--drain-console', 'event0', '64'],
            pass_fds=(reader, slave), capture_output=True, timeout=3,
            env={**os.environ, 'INPUT_FD': str(reader), 'CONSOLE_FD': str(slave)})
        assert result.returncode == 0 and result.stderr == b'', result
        lines = result.stdout.splitlines()
        saved = b''.join(bytes.fromhex(line.split(b'hex=')[1].decode()) for line in lines if b'hex=' in line)
        assert saved == b'n' * 64, result
        assert b'console-drain empty=1 bytes=64' in lines, result
        assert lines[-1] == b'console-drain complete=1 restored=1', result
        assert termios.tcgetattr(slave) == before
        assert not select.select([master], [], [], 0)[0]
        print('console-drain-preserves-and-restores=pass')
    finally:
        for fd in (master, slave, reader, writer):
            os.close(fd)


def requeue_case(binary, qemu, fault=None):
    master, slave = pty.openpty()
    reader, writer = os.pipe()
    try:
        before = termios.tcgetattr(slave)
        result = subprocess.run([qemu, str(binary), '--drain-console', 'event0', '64'],
            pass_fds=(reader, slave, master), capture_output=True, timeout=3,
            env={**os.environ, 'INPUT_FD': str(reader), 'CONSOLE_FD': str(slave),
                 'REQUEUE_FD': str(master), **({fault: '1'} if fault else {})})
        assert result.returncode == (2 if fault else 0) and result.stderr == b'', result
        if fault:
            assert result.stdout == (b'console-drain requeue=refused\n'
                                     b'console-drain complete=0 restored=1\n'), result
        else:
            assert result.stdout == (b'console-drain requeue=accepted ldisc=0\n'
                b'console-drain bytes=6 hex=717565756564\n'
                b'console-drain empty=1 bytes=6\n'
                b'console-drain complete=1 restored=1\n'), result
        assert termios.tcgetattr(slave) == before
        assert not select.select([master], [], [], 0)[0]
        print('console-drain-' + (fault or 'injected-after-requeue') + '=pass')
    finally:
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
    run_case(binary, args.qemu, 'queued-prefix-before-space', [press, sync, release, sync], b' ', expected=0)
    run_case(binary, args.qemu, 'held-space-does-not-start', [press, sync], b' ')
    run_case(binary, args.qemu, 'wrong-key', [(1, 30, 1), sync], b'a')
    run_case(binary, args.qemu, 'release-without-press', [release, sync], b' ')
    run_case(binary, args.qemu, 'lost-events', [(0, 3, 0)])
    run_case(binary, args.qemu, 'timeout')
    run_case(binary, args.qemu, 'signal-restores-console', cancel=True)
    run_case(binary, args.qemu, 'escape-preserves-pending-space', [(4, 4, 36), press, sync, release, sync], b'\x1b ')
    state_case(binary, args.qemu)
    state_case(binary, args.qemu, failure=True)
    drain_case(binary, args.qemu)
    requeue_case(binary, args.qemu)
    requeue_case(binary, args.qemu, 'WRONG_LDISC')
    requeue_case(binary, args.qemu, 'REFUSE_REQUEUE')


if __name__ == '__main__':
    main()
