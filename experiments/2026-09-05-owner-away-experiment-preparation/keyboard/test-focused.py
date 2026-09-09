#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual reader under ARM64 QEMU with a real PTY and fake evdev."""
import argparse
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import subprocess
import termios
import tempfile
import threading
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
    if (fd == input_fd && request == EVIOCGKEY((KEY_MAX + 8) / 8)) {
        static int queries;
        memset(out, 0, (KEY_MAX + 8) / 8);
        if (++queries >= 3 && getenv("HELD_END")) ((unsigned char *)out)[0] = 4;
        return (KEY_MAX + 8) / 8;
    }
    if (fd == input_fd && request == EVIOCGREP) {
        if (getenv("FAIL_REPEAT")) return -1;
        ((unsigned int *)out)[0] = 250;
        ((unsigned int *)out)[1] = atoi(getenv("REPEAT_PERIOD"));
        return 0;
    }
    if (fd == console_fd && request == VT_GETSTATE) {
        ((struct vt_stat *)out)->v_active = 1; return 0;
    }
    if (fd == console_fd && request == KDGKBMODE) {
        *(int *)out = K_UNICODE; return 0;
    }
    if (fd == console_fd && request == KDGKBMETA) {
        *(int *)out = K_ESCPREFIX; return 0;
    }
    if (fd == console_fd && request == KDGKBSENT) {
        const char *const strings[] = {
            "\033[[A", "\033[[B", "\033[[C", "\033[[D", "\033[[E",
            "\033[17~", "\033[18~", "\033[19~", "\033[20~", "\033[21~"
        };
        struct kbsentry *entry = out;
        const char *value = entry->kb_func < 10 ? strings[entry->kb_func] :
            entry->kb_func == 20 ? "\033[1~" : entry->kb_func == 23 ? "\033[4~" :
            entry->kb_func == 24 ? "\033[5~" : "\033[6~";
        strcpy((char *)entry->kb_string, value); return 0;
    }
    return -1;
}
#define open fake_open
#define fstat fake_stat
#define ioctl fake_ioctl
#include "keyboard-observe.c"
'''


def packed(events):
    return b''.join(struct.pack('<qqHHi', 0, 0, *event) for event in events)


def wait_prompt(master, marker, process, timeout):
    data = b''
    deadline = time.monotonic() + timeout
    while marker not in data and time.monotonic() < deadline:
        if select.select([master], [], [], .1)[0]:
            data += os.read(master, 4096)
        if process.poll() is not None:
            break
    assert marker in data, (marker, data, process.poll())


def run(binary, qemu, name, *, first=b'', second=None, period='33',
        failure=None, cancel=False, before_console=False, legacy=False, full=False):
    master, slave = pty.openpty()
    reader, writer = os.pipe()
    before = termios.tcgetattr(slave)
    process, feeder = None, None
    errors = []
    output = tempfile.TemporaryFile(dir=binary.parent)
    try:
        process = subprocess.Popen([qemu, str(binary), '--capture' if legacy else '--diagnose',
                                    'event0', '13', '64'],
            pass_fds=(reader, slave), stdout=output, stderr=subprocess.PIPE,
            env={**os.environ, 'INPUT_FD': str(reader), 'CONSOLE_FD': str(slave),
                 'REPEAT_PERIOD': period, **({'FAIL_REPEAT': '1'} if name == 'query-failure' else {}),
                 **({'HELD_END': '1'} if name == 'held-at-end' else {})})
        if not before_console:
            wait_prompt(master, b'1/20' if legacy else b'1/2', process, 5)
            assert termios.tcgetattr(slave) != before, name

            def feed():
                try:
                    view = memoryview(first)
                    while view:
                        view = view[os.write(writer, view):]
                    if second is not None:
                        wait_prompt(master, b'2/2', process, 18 if full else 4)
                        os.write(writer, second)
                except BaseException as exc:
                    errors.append(exc)

            feeder = threading.Thread(target=feed, daemon=True)
            feeder.start()
            if cancel:
                process.send_signal(signal.SIGTERM)
        _, err = process.communicate(timeout=36 if full else 8)
        output.seek(0)
        out = output.read(98305)
        if feeder:
            feeder.join(timeout=2)
            assert not feeder.is_alive(), name
        assert not errors, (name, errors)
        assert err == b'', (name, err)
        assert process.returncode == (2 if failure else 0), (name, process.returncode, out)
        assert termios.tcgetattr(slave) == before, (name, 'console restoration')
        assert len(out) < 98304, (name, len(out))
        if failure:
            assert ('incomplete reason=' + failure).encode() in out, (name, out)
            assert b'restored=1' in out, (name, out)
        else:
            assert out.endswith(b'complete steps=2 restored=1\n'), (name, out)
            assert b'step end index=0\n' in out and b'step end index=1\n' in out
        if before_console:
            assert b'device event=' not in out, (name, out)
        print(name + '=pass', flush=True)
        return out
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        # Closing the only remaining read end releases a blocked fixture writer.
        os.close(reader)
        if feeder:
            feeder.join(timeout=2)
        for fd in (master, slave, writer):
            os.close(fd)
        output.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--qemu', required=True)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    source = args.work/'focused-fixture.c'
    source.write_text(FIXTURE)
    binaries = []
    for label, flags in [('scaled', ['-DFOCUSED_STEP_MS=1000']), ('full', [])]:
        binary = args.work/('focused-' + label)
        subprocess.run([args.compiler, '-std=c11', '-static', '-Wall', '-Wextra', '-Werror',
            '-idirafter', '/usr/aarch64-linux-gnu/include', '-I', str(HERE), *flags,
            str(source), '-o', str(binary)], check=True)
        binaries.append(binary)
    binary, full = binaries
    sync = (0, 0, 0)
    digit = [(4, 4, 0), (1, 2, 1), sync, (4, 4, 0), (1, 2, 0), sync]
    repeats = [(1, 125, 2), (0, 0, 1)] * 80
    chord = [(4, 4, 30), (1, 42, 1), sync, (4, 4, 35), (1, 125, 1), sync]
    chord += repeats + digit + [(4, 4, 35), (1, 125, 0), sync,
        (4, 4, 30), (1, 42, 0), sync, (4, 4, 21), (1, 30, 1), sync,
        (4, 4, 21), (1, 30, 0), sync]
    out = run(binary, args.qemu, 'repeat-prefix-keeps-later-edges', first=packed(digit), second=packed(chord))
    events = [tuple(map(int, match)) for match in re.findall(rb'^event (\d+) (\d+) (\d+) (-?\d+)$', out, re.M)]
    assert [event[1:] for event in events] == digit + chord
    assert all(0 <= event[0] < 1000 for event in events)
    out = run(binary, args.qemu, 'overflow-retains-first-unrecorded-event',
              first=packed([sync] * 1024 + [(1, 2, 1)]), failure='event-limit')
    assert len(re.findall(rb'^event ', out, re.M)) == 1024
    assert re.search(rb'^overflow \d+ 1 2 1$', out, re.M)
    run(binary, args.qemu, 'lost-events', first=packed([(0, 3, 0)]), failure='syn-dropped')
    run(binary, args.qemu, 'short-read', first=b'x', failure='event-read')
    run(binary, args.qemu, 'signal-restores-console', cancel=True, failure='signal')
    run(binary, args.qemu, 'held-at-end', failure='held-or-key-state-query')
    run(binary, args.qemu, 'zero-period', period='0', before_console=True, failure='repeat-query-or-capacity')
    run(binary, args.qemu, 'query-failure', before_console=True, failure='repeat-query-or-capacity')
    run(full, args.qemu, 'repeat-rate-exceeds-capacity', period='1', before_console=True,
        failure='repeat-query-or-capacity')
    out = run(binary, args.qemu, 'legacy-ceiling-and-framing', first=packed([sync] * 65),
              legacy=True, failure='capture-or-preflight')
    assert out.startswith(b'keyboard-observe version=1\n')
    assert len(re.findall(rb'^event type=', out, re.M)) == 64 and b'overflow' not in out
    out = run(full, args.qemu, 'production-duration-two-windows', first=packed(digit), second=packed(chord), full=True)
    durations = [int(value) for value in re.findall(rb'^window elapsed_ms=(\d+)', out, re.M)]
    assert len(durations) == 3 and durations[0] >= 2000 and all(d >= 15000 for d in durations[1:])


if __name__ == '__main__':
    main()
