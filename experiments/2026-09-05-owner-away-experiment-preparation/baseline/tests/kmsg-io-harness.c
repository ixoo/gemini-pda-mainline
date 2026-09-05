/* SPDX-License-Identifier: MIT */
/* Test-only syscall model. Never forward a modeled call to the host kernel. */
#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static int model_open(const char *, int, ...);
static int model_openat(int, const char *, int, ...);
static int model_fstat(int, struct stat *);
static int model_fstatat(int, const char *, struct stat *, int);
static int model_sigaction(int, const struct sigaction *, struct sigaction *);
static int model_clock_gettime(clockid_t, struct timespec *);
static ssize_t model_read(int, void *, size_t);
static ssize_t model_write(int, const void *, size_t);
static int model_poll(struct pollfd *, nfds_t, int);
static int model_fsync(int);
static int model_close(int);
static int model_linkat(int, const char *, int, const char *, int);
static int model_unlinkat(int, const char *, int);

/* Function-like macros do not rewrite struct sigaction or other header types.
 * The production parser, signal handler, main, write loop and seal are included
 * verbatim; there is no KMSG_CAPTURE_NO_MAIN substitution in this harness.
 */
#define open(...) model_open(__VA_ARGS__)
#define openat(...) model_openat(__VA_ARGS__)
#define fstat(...) model_fstat(__VA_ARGS__)
#define fstatat(...) model_fstatat(__VA_ARGS__)
#define sigaction(...) model_sigaction(__VA_ARGS__)
#define clock_gettime(...) model_clock_gettime(__VA_ARGS__)
#define read(...) model_read(__VA_ARGS__)
#define write(...) model_write(__VA_ARGS__)
#define poll(...) model_poll(__VA_ARGS__)
#define fsync(...) model_fsync(__VA_ARGS__)
#define close(...) model_close(__VA_ARGS__)
#define linkat(...) model_linkat(__VA_ARGS__)
#define unlinkat(...) model_unlinkat(__VA_ARGS__)
#define main capture_main
#include "kmsg-capture.c"
#undef main
#undef open
#undef openat
#undef fstat
#undef fstatat
#undef sigaction
#undef clock_gettime
#undef read
#undef write
#undef poll
#undef fsync
#undef close
#undef linkat
#undef unlinkat

enum { DIR_FD = 101, LOG_FD, STATUS_FD, KMSG_FD };
struct memory_file {
    int exists, synced;
    size_t length;
    unsigned char data[LOG_LIMIT + RECORD_LIMIT];
};
static struct {
    const char *scenario;
    struct memory_file log, partial, final;
    int opened[4];
    void (*handler[64])(int);
    unsigned int operations, reads, polls, clocks, sent, kmsg_opens;
    unsigned int log_writes, status_writes, publications;
    uint64_t now_ms;
    char trace[16384];
    size_t trace_length;
} model;

static void require(int condition, const char *reason)
{
    if (!condition) {
        fprintf(stderr, "model refusal: %s\n", reason);
        exit(90);
    }
}

static int scenario(const char *name)
{
    return strcmp(model.scenario, name) == 0;
}

static void event(const char *name)
{
    size_t length = strlen(name);
    require(++model.operations <= 1000, "operation budget");
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

static void signal_event(int number)
{
    require(number > 0 && number < 64 && model.handler[number] != NULL,
            "unregistered signal");
    event(number == SIGTERM ? "SIGNAL_TERM" : number == SIGINT ? "SIGNAL_INT" : "SIGNAL_HUP");
    model.handler[number](number);
}

static struct memory_file *named_file(const char *name)
{
    if (!strcmp(name, "kmsg.log"))
        return &model.log;
    if (!strcmp(name, "kmsg.status.partial"))
        return &model.partial;
    if (!strcmp(name, "kmsg.status"))
        return &model.final;
    require(0, "unrecognized file name");
    return NULL;
}

static int model_open(const char *path, int flags, ...)
{
    if (!strcmp(path, "/run/a53")) {
        event("OPEN_DIR");
        require(flags == (O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC), "directory open flags");
        model.opened[DIR_FD - DIR_FD] = 1;
        return DIR_FD;
    }
    require(!strcmp(path, "/dev/kmsg"), "unrecognized open path");
    event("OPEN_KMSG_READONLY");
    require(flags == (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC), "kmsg open flags");
    model.kmsg_opens++;
    if (scenario("kmsg-open-error"))
        return error(EACCES);
    model.opened[KMSG_FD - DIR_FD] = 1;
    return KMSG_FD;
}

static int model_openat(int dir, const char *name, int flags, ...)
{
    va_list arguments;
    int mode, fd;
    struct memory_file *file = named_file(name);
    require(dir == DIR_FD && model.opened[0], "openat directory");
    require(file == &model.log || file == &model.partial, "openat final receipt");
    require(flags == (O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC), "exclusive file open flags");
    va_start(arguments, flags);
    mode = va_arg(arguments, int);
    va_end(arguments);
    require(mode == 0600, "private file mode");
    event(file == &model.log ? "OPEN_LOG_EXCL" : "OPEN_PARTIAL_EXCL");
    if (file->exists)
        return error(EEXIST);
    file->exists = 1;
    fd = file == &model.log ? LOG_FD : STATUS_FD;
    model.opened[fd - DIR_FD] = 1;
    return fd;
}

static int model_fstat(int fd, struct stat *out)
{
    require(out != NULL && (fd == DIR_FD || fd == KMSG_FD), "fstat descriptor");
    memset(out, 0, sizeof(*out));
    event(fd == DIR_FD ? "STAT_DIR" : "STAT_KMSG");
    out->st_uid = fd == DIR_FD && scenario("bad-owner") ? 1234 : 0;
    out->st_mode = fd == DIR_FD ? S_IFDIR | (scenario("bad-mode") ? 0777 : 0700) :
        (scenario("non-character-device") ? S_IFREG : S_IFCHR) | 0600;
    return 0;
}

static int model_fstatat(int dir, const char *name, struct stat *out, int flags)
{
    struct memory_file *file = named_file(name);
    require(dir == DIR_FD && out != NULL && flags == AT_SYMLINK_NOFOLLOW, "fstatat arguments");
    event(file == &model.final ? "CHECK_FINAL_ABSENT" : "CHECK_PARTIAL_ABSENT");
    if (!file->exists)
        return error(ENOENT);
    memset(out, 0, sizeof(*out));
    out->st_mode = S_IFREG | 0600;
    return 0;
}

static int model_sigaction(int number, const struct sigaction *action, struct sigaction *old)
{
    require((number == SIGTERM || number == SIGINT || number == SIGHUP) &&
            action != NULL && old == NULL && action->sa_handler != NULL,
            "signal registration");
    require(sigismember(&action->sa_mask, SIGTERM) == 1 &&
            sigismember(&action->sa_mask, SIGINT) == 1 &&
            sigismember(&action->sa_mask, SIGHUP) == 1, "signal handler mask");
    event("REGISTER_SIGNAL");
    model.handler[number] = action->sa_handler;
    return 0;
}

static int model_clock_gettime(clockid_t id, struct timespec *out)
{
    require(id == CLOCK_MONOTONIC && out != NULL, "clock arguments");
    event("CLOCK");
    model.clocks++;
    if (scenario("clock-error") && model.clocks == 2)
        return error(EIO);
    if (scenario("clock-backward") && model.clocks == 3)
        model.now_ms = 999;
    out->tv_sec = (time_t)(model.now_ms / 1000);
    out->tv_nsec = (long)((model.now_ms % 1000) * 1000000);
    return 0;
}

static ssize_t record(void *data, size_t capacity, unsigned int sequence, int large)
{
    int header;
    size_t length;
    require(capacity == RECORD_LIMIT, "record read capacity");
    if (large) {
        header = snprintf(data, capacity, "6,%u,1,-;", sequence);
        require(header > 0 && (size_t)header + 1 < capacity, "fixture record header");
        memset((unsigned char *)data + header, 'x', capacity - (size_t)header - 1);
        ((unsigned char *)data)[capacity - 1] = '\n';
        length = capacity;
    } else {
        header = snprintf(data, capacity, "6,%u,1,-;record-%u\n", sequence, sequence);
        require(header > 0 && (size_t)header < capacity, "fixture record length");
        length = (size_t)header;
    }
    event("READ_RECORD");
    model.sent++;
    return (ssize_t)length;
}

static ssize_t model_read(int fd, void *data, size_t capacity)
{
    require(fd == KMSG_FD && model.opened[3] && data != NULL, "read descriptor");
    model.reads++;
    if (scenario("read-eintr") && model.reads == 1) {
        event("READ_EINTR");
        return error(EINTR);
    }
    if (scenario("initial-gap") && !model.sent)
        return record(data, capacity, 1, 0);
    if (scenario("malformed-record") && !model.sent) {
        event("READ_MALFORMED");
        memcpy(data, "bad\n", 4);
        return 4;
    }
    if (scenario("empty")) {
        event("READ_EAGAIN");
        signal_event(SIGTERM);
        return error(EAGAIN);
    }
    if (scenario("cap") || scenario("cap-exact")) {
        unsigned int count = scenario("cap") ? 33 : 32;
        if (model.sent < count)
            return record(data, capacity, model.sent, 1);
    } else if (!model.sent) {
        return record(data, capacity, 0, 0);
    }
    if (scenario("later-gap"))
        return record(data, capacity, 2, 0);
    if (scenario("duplicate"))
        return record(data, capacity, 0, 0);
    if (scenario("epipe") || (scenario("pollerr-epipe") && model.polls)) {
        event("READ_EPIPE");
        return error(EPIPE);
    }
    if (scenario("read-eio") || scenario("read-einval")) {
        event("READ_ERROR");
        return error(scenario("read-eio") ? EIO : EINVAL);
    }
    if (scenario("read-eof")) {
        event("READ_EOF");
        return 0;
    }
    if (scenario("sigterm-drain") && model.polls && model.sent < 3)
        return record(data, capacity, model.sent, 0);
    event("READ_EAGAIN");
    if (scenario("deadline") || scenario("poll-error") || scenario("poll-lost") ||
        scenario("pollerr-epipe") || ((scenario("sigterm-drain") || scenario("poll-eintr")) && !model.polls))
        return error(EAGAIN);
    if (scenario("interrupt") || scenario("interrupt-term")) {
        signal_event(SIGINT);
        if (scenario("interrupt-term"))
            signal_event(SIGTERM);
    } else if (scenario("term-interrupt")) {
        signal_event(SIGTERM);
        signal_event(SIGINT);
    } else if (scenario("hup")) {
        signal_event(SIGHUP);
    } else if (!stop_signal) {
        signal_event(SIGTERM);
    }
    return error(EAGAIN);
}

static ssize_t model_write(int fd, const void *data, size_t length)
{
    struct memory_file *file;
    unsigned int count;
    require(fd == LOG_FD || fd == STATUS_FD, "no write to kmsg or other descriptor");
    require(model.opened[fd - DIR_FD] && data != NULL && length, "write arguments");
    file = fd == LOG_FD ? &model.log : &model.partial;
    count = fd == LOG_FD ? ++model.log_writes : ++model.status_writes;
    event(fd == LOG_FD ? "WRITE_LOG" : "WRITE_PARTIAL");
    require(!model.final.exists || scenario("link-exists"), "write after publication");
    if ((fd == LOG_FD && scenario("log-eintr")) || (fd == STATUS_FD && scenario("status-eintr")))
        if (count == 1)
            return error(EINTR);
    if (fd == LOG_FD && scenario("log-zero"))
        return 0;
    if ((fd == LOG_FD && scenario("log-partial-error")) ||
        (fd == STATUS_FD && scenario("status-error")))
        if (count > 1)
            return error(ENOSPC);
    if (count == 1 && ((fd == LOG_FD && (scenario("log-partial") || scenario("log-partial-error"))) ||
                      (fd == STATUS_FD && (scenario("status-partial") || scenario("status-error")))))
        if (length > 5)
            length = 5;
    require(file->length + length <= sizeof(file->data), "memory file capacity");
    memcpy(file->data + file->length, data, length);
    file->length += length;
    file->synced = 0;
    return (ssize_t)length;
}

static int model_poll(struct pollfd *fds, nfds_t count, int timeout)
{
    require(count == 1 && fds && fds[0].fd == KMSG_FD && fds[0].events == POLLIN,
            "poll descriptor");
    require(timeout >= 0 && timeout <= 250, "bounded poll timeout");
    event("POLL");
    model.polls++;
    fds[0].revents = 0;
    if (scenario("deadline")) {
        model.now_ms = 1000 + DEADLINE_MS;
        return 0;
    }
    if (scenario("poll-error"))
        return error(EIO);
    if (scenario("poll-eintr")) {
        signal_event(SIGTERM);
        return error(EINTR);
    }
    if (scenario("poll-lost")) {
        fds[0].revents = POLLHUP;
        return 1;
    }
    if (scenario("pollerr-epipe")) {
        fds[0].revents = POLLERR;
        return 1;
    }
    require(scenario("sigterm-drain"), "unplanned poll");
    signal_event(SIGTERM);
    fds[0].revents = POLLIN;
    return 1;
}

static int model_fsync(int fd)
{
    require(fd == LOG_FD || fd == STATUS_FD || fd == DIR_FD, "sync descriptor");
    event(fd == LOG_FD ? "SYNC_LOG" : fd == STATUS_FD ? "SYNC_PARTIAL" : "SYNC_DIR");
    if ((fd == LOG_FD && scenario("log-sync-error")) ||
        (fd == STATUS_FD && scenario("status-sync-error")) ||
        (fd == DIR_FD && scenario("directory-sync-error")))
        return error(EIO);
    if (fd == LOG_FD)
        model.log.synced = 1;
    if (fd == STATUS_FD)
        model.partial.synced = 1;
    return 0;
}

static int model_close(int fd)
{
    require(fd >= DIR_FD && fd <= KMSG_FD && model.opened[fd - DIR_FD], "close descriptor");
    event(fd == KMSG_FD ? "CLOSE_KMSG" : "CLOSE_FILE");
    model.opened[fd - DIR_FD] = 0;
    if (fd == KMSG_FD && scenario("kmsg-close-error"))
        return error(EIO);
    return 0;
}

static int model_linkat(int olddir, const char *oldname, int newdir, const char *newname, int flags)
{
    require(olddir == DIR_FD && newdir == DIR_FD && flags == 0 &&
            !strcmp(oldname, "kmsg.status.partial") && !strcmp(newname, "kmsg.status"),
            "atomic publication arguments");
    event("LINK_FINAL");
    require(model.partial.exists && model.partial.synced && model.partial.length,
            "publication before complete synced status");
    if (scenario("link-error"))
        return error(EIO);
    if (scenario("link-exists")) {
        const char prior[] = "previous-receipt\n";
        model.final.exists = 1;
        memcpy(model.final.data, prior, sizeof(prior) - 1);
        model.final.length = sizeof(prior) - 1;
    }
    if (model.final.exists)
        return error(EEXIST);
    model.final = model.partial;
    model.publications++;
    event("PUBLISH_FINAL_ATOMIC");
    return 0;
}

static int model_unlinkat(int dir, const char *name, int flags)
{
    require(dir == DIR_FD && flags == 0 && !strcmp(name, "kmsg.status.partial"),
            "cleanup arguments");
    require(model.final.exists && model.partial.exists, "cleanup before publication");
    event("UNLINK_PARTIAL");
    if (scenario("unlink-error"))
        return error(EIO);
    model.partial.exists = 0;
    return 0;
}

static uint64_t fnv(const unsigned char *data, size_t length)
{
    uint64_t hash = UINT64_C(14695981039346656037);
    size_t index;
    for (index = 0; index < length; index++)
        hash = (hash ^ data[index]) * UINT64_C(1099511628211);
    return hash;
}

int main(int argc, char **argv)
{
    int result, second = -1;
    const char *const names[] = {
        "pass", "sigterm-drain", "interrupt", "interrupt-term", "term-interrupt", "hup",
        "empty", "cap", "cap-exact", "initial-gap", "later-gap", "duplicate", "malformed-record",
        "epipe", "pollerr-epipe", "read-eintr", "read-eio", "read-einval", "read-eof",
        "deadline", "clock-error", "clock-backward", "poll-error", "poll-eintr", "poll-lost",
        "log-partial", "log-eintr", "log-partial-error", "log-zero",
        "status-partial", "status-eintr", "status-error", "log-sync-error", "status-sync-error",
        "link-error", "link-exists", "unlink-error", "directory-sync-error", "kmsg-close-error",
        "log-present", "partial-present", "final-present", "second-run", "bad-owner", "bad-mode",
        "non-character-device", "kmsg-open-error"
    };
    size_t index;
    int known = 0;
    char *capture_argv[] = {"kmsg-capture", NULL};
    require(argc == 2, "one scenario argument");
    for (index = 0; index < sizeof(names) / sizeof(names[0]); index++)
        if (!strcmp(names[index], argv[1]))
            known = 1;
    require(known, "unknown scenario");
    model.scenario = argv[1];
    model.now_ms = 1000;
    if (scenario("log-present") || scenario("partial-present") || scenario("final-present")) {
        struct memory_file *file = scenario("log-present") ? &model.log :
            scenario("partial-present") ? &model.partial : &model.final;
        const char prior[] = "previous-receipt\n";
        file->exists = 1;
        file->length = sizeof(prior) - 1;
        memcpy(file->data, prior, sizeof(prior) - 1);
    }
    result = capture_main(1, capture_argv);
    if (scenario("second-run")) {
        stop_signal = 0; /* Fresh process signal state; keep its RAM files. */
        event("SECOND_INVOCATION");
        second = capture_main(1, capture_argv);
    }
    printf("return_code=%d\nsecond_return_code=%d\nreads=%u\nkmsg_opens=%u\n"
           "log_bytes=%zu\nlog_fnv64=%016" PRIx64 "\npartial_exists=%d\n"
           "final_exists=%d\npublications=%u\nstatus_begin\n",
           result, second, model.reads, model.kmsg_opens, model.log.length,
           fnv(model.log.data, model.log.length), model.partial.exists,
           model.final.exists, model.publications);
    if (model.final.exists)
        for (index = 0; index < model.final.length; index++)
            putchar(model.final.data[index]);
    printf("status_end\ntrace_begin\n%strace_end\n", model.trace);
    return 0;
}
