/* SPDX-License-Identifier: MIT */
/* One RAM-only /dev/kmsg capture; no device writes, restart or log clearing.
 * ABI: https://www.kernel.org/doc/Documentation/ABI/testing/dev-kmsg
 * Native parser fixtures do not establish Linux device-I/O behavior.
 */
#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define LOG_LIMIT (2U * 1024U * 1024U)
#define RECORD_LIMIT 65536U
#define DEADLINE_MS UINT64_C(600000)

struct capture {
    uint64_t first;
    uint64_t last;
    uint64_t records;
    size_t bytes;
};

static int decimal(const unsigned char **cursor, const unsigned char *end,
                   uint64_t *value)
{
    const unsigned char *p = *cursor;
    uint64_t number = 0;
    if (p == end || *p < '0' || *p > '9')
        return -1;
    while (p < end && *p >= '0' && *p <= '9') {
        unsigned int digit = *p++ - '0';
        if (number > (UINT64_MAX - digit) / 10)
            return -1;
        number = number * 10 + digit;
    }
    if (p == end || *p++ != ',')
        return -1;
    *cursor = p;
    *value = number;
    return 0;
}

/* Validate one complete read(), not individual lines: metadata continuation
 * lines belong to their preceding record and do not carry new sequence IDs.
 * Preserve unknown printable header extensions as required by the ABI.
 */
static const char *accept_record(struct capture *state,
                                 const unsigned char *data, size_t length)
{
    const unsigned char *cursor = data, *end = data + length, *header;
    uint64_t priority, sequence, timestamp;
    if (!length || length > RECORD_LIMIT || data[length - 1] != '\n' ||
        memchr(data, '\0', length))
        return "malformed-record";
    header = memchr(data, ';', length);
    if (!header || decimal(&cursor, header, &priority) || priority > 2047 ||
        decimal(&cursor, header, &sequence) ||
        decimal(&cursor, header, &timestamp))
        return "malformed-header";
    (void)timestamp;
    if (cursor == header || *cursor == ',')
        return "missing-flags";
    for (; cursor < header; cursor++)
        if (*cursor < 0x21 || *cursor > 0x7e)
            return "malformed-flags-or-extension";
    if (header + 1 == end)
        return "missing-message";
    if (!state->records && sequence != 0)
        return "initial-sequence-gap";
    if (state->records && (state->last == UINT64_MAX || sequence != state->last + 1))
        return "sequence-gap";
    if (state->bytes > LOG_LIMIT || length > LOG_LIMIT - state->bytes)
        return "byte-cap";
    if (!state->records)
        state->first = sequence;
    state->last = sequence;
    state->records++;
    state->bytes += length;
    return NULL;
}

#ifndef KMSG_CAPTURE_NO_MAIN
static volatile sig_atomic_t stop_signal;

static void request_stop(int signal_number)
{
    /* An interrupt cannot later be promoted to success by SIGTERM. */
    if (!stop_signal || signal_number != SIGTERM)
        stop_signal = signal_number;
}

static int monotonic_ms(uint64_t *value)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) < 0 || now.tv_sec < 0)
        return -1;
    *value = (uint64_t)now.tv_sec * 1000 + (uint64_t)now.tv_nsec / 1000000;
    return 0;
}

static int write_all(int fd, const void *data, size_t length, size_t *written)
{
    const unsigned char *cursor = data;
    *written = 0;
    while (*written < length) {
        ssize_t count = write(fd, cursor + *written, length - *written);
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0)
            return -1;
        *written += (size_t)count;
    }
    return 0;
}

static int absent_at(int dir, const char *name)
{
    struct stat st;
    if (fstatat(dir, name, &st, AT_SYMLINK_NOFOLLOW) == 0)
        return 0;
    return errno == ENOENT;
}

static int seal(int dir, int log, int status, const struct capture *state,
                uint64_t elapsed, const char *reason)
{
    char buffer[512];
    size_t written;
    int length, success = strcmp(reason, "sealed-on-sigterm") == 0;
    if (fsync(log) < 0) {
        reason = "log-sync-failed";
        success = 0;
    }
    length = snprintf(buffer, sizeof(buffer),
        "schema=gemini-kmsg-v1\nsealed=yes\nresult=%s\nreason=%s\n"
        "first_seq=%" PRIu64 "\nlast_seq=%" PRIu64 "\nrecords=%" PRIu64 "\n"
        "bytes=%zu\nelapsed_ms=%" PRIu64 "\nbyte_limit=%u\n"
        "deadline_ms=%" PRIu64 "\n",
        success ? "pass" : "failed", reason, state->first, state->last,
        state->records, state->bytes, elapsed, LOG_LIMIT, DEADLINE_MS);
    if (length < 0 || (size_t)length >= sizeof(buffer) ||
        write_all(status, buffer, (size_t)length, &written) || fsync(status) < 0)
        return -1;
    /* Linking publishes a complete status atomically without replacing any
     * prior receipt. Log O_EXCL serializes this one-attempt lifecycle.
     */
    if (linkat(dir, "kmsg.status.partial", dir, "kmsg.status", 0) < 0)
        return -1;
    if (unlinkat(dir, "kmsg.status.partial", 0) < 0 || fsync(dir) < 0)
        return -1;
    return success ? 0 : 1;
}

int main(int argc, char **argv)
{
    struct capture state = {0};
    struct sigaction action;
    struct pollfd pollfd;
    struct stat directory_stat, device_stat;
    unsigned char record[RECORD_LIMIT];
    uint64_t start = 0, now = 0;
    const char *reason = "initialization-failed";
    int dir = -1, log = -1, status = -1, kmsg = -1, outcome = 1;
    (void)argv;
    /* No options that widen limits or redirect output/device paths. */
    if (argc != 1) {
        fprintf(stderr, "kmsg-capture takes no arguments\n");
        return 2;
    }
    memset(&action, 0, sizeof(action));
    action.sa_handler = request_stop;
    if (sigemptyset(&action.sa_mask) ||
        sigaddset(&action.sa_mask, SIGTERM) ||
        sigaddset(&action.sa_mask, SIGINT) ||
        sigaddset(&action.sa_mask, SIGHUP) ||
        sigaction(SIGTERM, &action, NULL) ||
        sigaction(SIGINT, &action, NULL) ||
        sigaction(SIGHUP, &action, NULL))
        goto done;
    dir = open("/run/a53", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (dir < 0 || fstat(dir, &directory_stat) < 0 ||
        directory_stat.st_uid != 0 || (directory_stat.st_mode & 0022) ||
        !absent_at(dir, "kmsg.status") || !absent_at(dir, "kmsg.status.partial"))
        goto done;
    log = openat(dir, "kmsg.log", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (log < 0)
        goto done;
    status = openat(dir, "kmsg.status.partial", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (status < 0)
        goto done;
    if (monotonic_ms(&start) < 0) {
        reason = "monotonic-clock-failed";
        goto finish;
    }
    now = start;
    /* The ABI starts each new reader at the oldest retained record. Requiring
     * sequence zero additionally detects loss before this process opened it.
     */
    kmsg = open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (kmsg < 0) {
        reason = "kmsg-open-failed";
        goto finish;
    }
    if (fstat(kmsg, &device_stat) < 0 || !S_ISCHR(device_stat.st_mode)) {
        reason = "kmsg-not-character-device";
        goto finish;
    }
    pollfd.fd = kmsg;
    pollfd.events = POLLIN;
    for (;;) {
        struct capture next = state;
        ssize_t length;
        size_t written;
        if (monotonic_ms(&now) < 0 || now < start) {
            reason = "monotonic-clock-failed";
            break;
        }
        if (now - start >= DEADLINE_MS) {
            reason = "deadline-expired";
            break;
        }
        length = read(kmsg, record, sizeof(record));
        if (length > 0) {
            reason = accept_record(&next, record, (size_t)length);
            if (reason)
                break;
            if (write_all(log, record, (size_t)length, &written)) {
                state.bytes += written;
                reason = "log-write-failed";
                break;
            }
            state = next;
            continue;
        }
        if (length == 0) {
            reason = "unexpected-eof";
            break;
        }
        if (errno == EINTR)
            continue;
        if (errno == EPIPE) {
            reason = "ring-overrun";
            break;
        }
        if (errno != EAGAIN) {
            reason = "kmsg-read-failed";
            break;
        }
        /* Drain through EAGAIN before SIGTERM seals success. A signal does
         * not make already-pending messages disappear from the final log.
         */
        if (stop_signal) {
            reason = stop_signal != SIGTERM ? "interrupted" :
                !state.records ? "empty-log" : "sealed-on-sigterm";
            break;
        }
        {
            uint64_t remaining = DEADLINE_MS - (now - start);
            int timeout = remaining < 250 ? (int)remaining : 250;
            int ready = poll(&pollfd, 1, timeout);
            if (ready < 0 && errno != EINTR) {
                reason = "poll-failed";
                break;
            }
            if (ready > 0 && (pollfd.revents & (POLLHUP | POLLNVAL))) {
                reason = "poll-device-lost";
                break;
            }
            /* POLLERR can report overwritten records; next read captures
             * the required EPIPE classification, rather than skipping it.
             */
        }
    }
finish:
    if (kmsg >= 0) {
        if (close(kmsg) < 0)
            reason = "kmsg-close-failed";
        kmsg = -1;
    }
    outcome = seal(dir, log, status, &state, now >= start ? now - start : 0, reason);
    if (outcome < 0)
        fprintf(stderr, "kmsg status could not be sealed; capture is inconclusive\n");
done:
    if (kmsg >= 0)
        close(kmsg);
    if (status >= 0)
        close(status);
    if (log >= 0)
        close(log);
    if (dir >= 0)
        close(dir);
    /* Failed/partial evidence remains in RAM and prevents restart. A missing
     * final receipt always means inconclusive, never an implicit success.
     */
    return outcome == 0 ? 0 : 1;
}
#endif
