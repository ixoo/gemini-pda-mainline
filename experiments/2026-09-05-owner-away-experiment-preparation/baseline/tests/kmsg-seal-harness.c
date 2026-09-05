/* SPDX-License-Identifier: MIT */
/* Model-only pidfd and /proc behavior. No real file opens or signals. */
#define _GNU_SOURCE
#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

/* Non-Linux host builds need model-only dispatch tags, never syscall numbers
 * passed to a real kernel. Every syscall call is replaced below and audited.
 */
#ifndef SYS_pidfd_open
#define SYS_pidfd_open 900001L
#endif
#ifndef SYS_pidfd_send_signal
#define SYS_pidfd_send_signal 900002L
#endif
static int seal_open(const char *, int, ...);
static int seal_openat(int, const char *, int, ...);
static int seal_fstat(int, struct stat *);
static ssize_t seal_read(int, void *, size_t);
static int seal_close(int);
static long seal_syscall(long, ...);
#define open(...) seal_open(__VA_ARGS__)
#define openat(...) seal_openat(__VA_ARGS__)
#define fstat(...) seal_fstat(__VA_ARGS__)
#define read(...) seal_read(__VA_ARGS__)
#define close(...) seal_close(__VA_ARGS__)
#define syscall(...) seal_syscall(__VA_ARGS__)
#define main seal_main
#include "kmsg-seal.c"
#undef main
#undef open
#undef openat
#undef fstat
#undef read
#undef close
#undef syscall

enum { DIRECTORY = 201, PID_FILE, CANDIDATE, PROCESS_EXE, PROCESS_FD };
static struct {
    const char *scenario, *pid_text;
    int opened[5];
    size_t offset;
    unsigned int reads, pidfd_opens, proc_opens, signal_attempts, delivered, operations;
    char trace[4096];
    size_t trace_length;
} model;

static void require(int ok, const char *reason)
{
    if (!ok) {
        fprintf(stderr, "seal model refusal: %s\n", reason);
        exit(90);
    }
}

static int scenario(const char *name)
{
    return !strcmp(model.scenario, name);
}

static void event(const char *name)
{
    size_t length = strlen(name);
    require(++model.operations <= 100, "operation budget");
    require(model.trace_length + length + 2 < sizeof(model.trace), "trace budget");
    memcpy(model.trace + model.trace_length, name, length);
    model.trace_length += length;
    model.trace[model.trace_length++] = '\n';
    model.trace[model.trace_length] = 0;
}

static int error(int number)
{
    errno = number;
    return -1;
}

static int opened(int fd)
{
    require(fd >= DIRECTORY && fd <= PROCESS_FD, "unknown descriptor");
    model.opened[fd - DIRECTORY] = 1;
    return fd;
}

static int seal_open(const char *path, int flags, ...)
{
    if (!strcmp(path, "/run/a53")) {
        event("OPEN_DIRECTORY");
        require(flags == (O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC), "directory flags");
        return opened(DIRECTORY);
    }
    if (!strcmp(path, "/bin/kmsg-capture")) {
        event("OPEN_CANDIDATE");
        require(flags == (O_RDONLY | O_NOFOLLOW | O_CLOEXEC), "candidate flags");
        return opened(CANDIDATE);
    }
    require(!strcmp(path, "/proc/1234/exe"), "fixed numeric process path");
    require(flags == (O_RDONLY | O_CLOEXEC), "process executable flags");
    require(model.opened[PROCESS_FD - DIRECTORY], "pidfd held before proc lookup");
    event("OPEN_PROCESS_EXE");
    model.proc_opens++;
    if (scenario("proc-missing"))
        return error(ENOENT);
    return opened(PROCESS_EXE);
}

static int seal_openat(int dir, const char *name, int flags, ...)
{
    require(dir == DIRECTORY && model.opened[0] && !strcmp(name, "kmsg-pid"), "fixed PID file");
    require(flags == (O_RDONLY | O_NOFOLLOW | O_CLOEXEC), "PID file flags");
    event("OPEN_PID_FILE");
    if (scenario("pid-symlink"))
        return error(ELOOP);
    return opened(PID_FILE);
}

static int seal_fstat(int fd, struct stat *out)
{
    require(fd >= DIRECTORY && fd <= PROCESS_EXE && model.opened[fd - DIRECTORY] && out,
            "stat descriptor");
    memset(out, 0, sizeof(*out));
    out->st_uid = 0;
    out->st_mode = (fd == DIRECTORY ? S_IFDIR : S_IFREG) | 0700;
    out->st_dev = 7;
    out->st_ino = 123;
    if (fd == DIRECTORY) {
        event("STAT_DIRECTORY");
        if (scenario("directory-owner")) out->st_uid = 1234;
        if (scenario("directory-mode")) out->st_mode |= 0020;
    } else if (fd == PID_FILE) {
        event("STAT_PID_FILE");
        out->st_size = (off_t)strlen(model.pid_text);
        if (scenario("pid-changed-size")) out->st_size++;
        if (scenario("pid-not-regular")) out->st_mode = S_IFCHR | 0600;
        if (scenario("pid-owner")) out->st_uid = 1234;
        if (scenario("pid-mode")) out->st_mode |= 0002;
    } else if (fd == CANDIDATE) {
        event("STAT_CANDIDATE");
        if (scenario("candidate-not-regular")) out->st_mode = S_IFCHR | 0700;
        if (scenario("candidate-owner")) out->st_uid = 1234;
        if (scenario("candidate-mode")) out->st_mode |= 0020;
    } else {
        event("STAT_PROCESS_EXE");
        if (scenario("wrong-inode")) out->st_ino++;
        if (scenario("wrong-device")) out->st_dev++;
        if (scenario("proc-not-regular")) out->st_mode = S_IFDIR | 0700;
    }
    return 0;
}

static ssize_t seal_read(int fd, void *data, size_t capacity)
{
    size_t remaining;
    require(fd == PID_FILE && model.opened[1] && data && capacity <= 13, "bounded PID read");
    event("READ_PID");
    model.reads++;
    if (scenario("read-error"))
        return error(EIO);
    if (scenario("eintr-storm") || (scenario("read-eintr") && model.reads == 1))
        return error(EINTR);
    remaining = strlen(model.pid_text) - model.offset;
    if (remaining > capacity) remaining = capacity;
    if (scenario("short-reads") && remaining > 1) remaining = 1;
    memcpy(data, model.pid_text + model.offset, remaining);
    model.offset += remaining;
    return (ssize_t)remaining;
}

static long seal_syscall(long number, ...)
{
    va_list arguments;
    va_start(arguments, number);
    if (number == SYS_pidfd_open) {
        pid_t pid = va_arg(arguments, pid_t);
        unsigned int flags = va_arg(arguments, unsigned int);
        require(pid == 1234 && flags == 0, "fixed pidfd open arguments");
        event("PIDFD_OPEN");
        model.pidfd_opens++;
        va_end(arguments);
        if (scenario("pidfd-unsupported")) return error(ENOSYS);
        if (scenario("process-gone")) return error(ESRCH);
        return opened(PROCESS_FD);
    }
    if (number == SYS_pidfd_send_signal) {
        int fd = va_arg(arguments, int);
        int signal_number = va_arg(arguments, int);
        void *info = va_arg(arguments, void *);
        unsigned int flags = va_arg(arguments, unsigned int);
        require(fd == PROCESS_FD && model.opened[4] && model.opened[3] && model.opened[2],
                "held pidfd and executable references");
        require(signal_number == SIGTERM && info == NULL && flags == 0,
                "only pidfd SIGTERM permitted");
        event("PIDFD_SEND_TERM");
        require(++model.signal_attempts == 1, "signal retry forbidden");
        va_end(arguments);
        /* /proc may now name a reused PID running the same file. The held
         * pidfd still refers to the old, dead process and returns ESRCH.
         */
        if (scenario("pid-reused")) return error(ESRCH);
        if (scenario("send-unsupported")) return error(ENOSYS);
        if (scenario("send-denied")) return error(EPERM);
        if (scenario("send-unexpected-result")) return 1;
        model.delivered++;
        event("SIGNAL_DELIVERED");
        return 0;
    }
    va_end(arguments);
    require(0, "unreviewed syscall; numeric kill prohibited");
    return -1;
}

static int seal_close(int fd)
{
    require(fd >= DIRECTORY && fd <= PROCESS_FD && model.opened[fd - DIRECTORY], "close descriptor");
    event(fd == PROCESS_FD ? "CLOSE_PIDFD" : "CLOSE_FILE");
    model.opened[fd - DIRECTORY] = 0;
    return 0;
}

int main(int argc, char **argv)
{
    const char *const names[] = {
        "pass", "short-reads", "read-eintr", "read-error", "eintr-storm", "pid-reused",
        "pidfd-unsupported", "process-gone", "send-unsupported", "send-denied", "send-unexpected-result",
        "wrong-inode", "wrong-device", "proc-not-regular", "proc-missing",
        "directory-owner", "directory-mode", "pid-symlink", "pid-not-regular", "pid-owner", "pid-mode",
        "candidate-not-regular", "candidate-owner", "candidate-mode", "pid-changed-size",
        "pid-zero", "pid-init", "pid-negative", "pid-leading-zero", "pid-extra-line", "pid-overflow",
        "pid-no-newline", "pid-whitespace", "pid-empty", "arguments"
    };
    char *helper_argv[] = {"kmsg-seal", "unrequested", NULL};
    size_t index;
    int known = 0, result;
    require(argc == 2, "one scenario argument");
    for (index = 0; index < sizeof(names) / sizeof(names[0]); index++)
        if (!strcmp(names[index], argv[1])) known = 1;
    require(known, "known scenario");
    model.scenario = argv[1];
    model.pid_text = "1234\n";
    if (scenario("pid-zero")) model.pid_text = "0\n";
    if (scenario("pid-init")) model.pid_text = "1\n";
    if (scenario("pid-negative")) model.pid_text = "-1234\n";
    if (scenario("pid-leading-zero")) model.pid_text = "01234\n";
    if (scenario("pid-extra-line")) model.pid_text = "1234\n5\n";
    if (scenario("pid-overflow")) model.pid_text = "2147483648\n";
    if (scenario("pid-no-newline")) model.pid_text = "1234";
    if (scenario("pid-whitespace")) model.pid_text = "1234 \n";
    if (scenario("pid-empty")) model.pid_text = "";
    result = seal_main(scenario("arguments") ? 2 : 1, helper_argv);
    for (index = 0; index < 5; index++) require(!model.opened[index], "descriptor leaked");
    printf("return_code=%d\npidfd_opens=%u\nproc_opens=%u\nsignal_attempts=%u\n"
           "delivered=%u\nreads=%u\ntrace_begin\n%strace_end\n",
           result, model.pidfd_opens, model.proc_opens, model.signal_attempts,
           model.delivered, model.reads, model.trace);
    return 0;
}
