/* SPDX-License-Identifier: MIT */
/* Seal only the fixed baseline logger. A pidfd prevents PID reuse between
 * identity inspection and signaling; there is deliberately no kill(pid, ...).
 * The caller separately verifies the candidate binary digest and final status.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

#if !defined(SYS_pidfd_open) || !defined(SYS_pidfd_send_signal)
#error "Linux pidfd syscall definitions are required; no numeric PID fallback"
#endif

static int protected_regular(int fd, struct stat *state)
{
    return fstat(fd, state) == 0 && S_ISREG(state->st_mode) &&
        state->st_uid == 0 && !(state->st_mode & 0022);
}

int main(int argc, char **argv)
{
    int directory = -1, input = -1, expected = -1, executable = -1, pidfd = -1;
    int result = 1, path_length;
    const char *reason = "initialization";
    char value[13], path[64];
    size_t used = 0, index;
    unsigned long pid = 0;
    unsigned int reads = 0;
    struct stat directory_state, pid_state, expected_state, actual_state;
    long descriptor;
    (void)argv;
    if (argc != 1) {
        fprintf(stderr, "kmsg-seal takes no arguments\n");
        return 2;
    }
    directory = open("/run/a53", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    reason = "RAM-directory-identity";
    if (directory < 0 || fstat(directory, &directory_state) < 0 ||
        directory_state.st_uid != 0 || (directory_state.st_mode & 0022))
        goto done;
    input = openat(directory, "kmsg-pid", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    reason = "PID-file-identity";
    if (input < 0 || !protected_regular(input, &pid_state) ||
        pid_state.st_size < 2 || pid_state.st_size > 11)
        goto done;
    for (;;) {
        ssize_t count;
        reason = "PID-file-read";
        if (used == sizeof(value) || ++reads > 16)
            goto done;
        count = read(input, value + used, sizeof(value) - used);
        if (count < 0 && errno == EINTR)
            continue;
        if (count < 0)
            goto done;
        if (!count)
            break;
        used += (size_t)count;
    }
    reason = "PID-format";
    if (used < 2 || used > 11 || value[0] < '1' || value[0] > '9' ||
        value[used - 1] != '\n' || used != (size_t)pid_state.st_size)
        goto done;
    for (index = 0; index + 1 < used; index++) {
        unsigned int digit;
        if (value[index] < '0' || value[index] > '9')
            goto done;
        digit = (unsigned int)(value[index] - '0');
        if (pid > ((unsigned long)INT_MAX - digit) / 10)
            goto done;
        pid = pid * 10 + digit;
    }
    if (pid <= 1)
        goto done;
    expected = open("/bin/kmsg-capture", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    reason = "candidate-executable-identity";
    if (expected < 0 || !protected_regular(expected, &expected_state))
        goto done;
    reason = "pidfd-open-refused";
    descriptor = syscall(SYS_pidfd_open, (pid_t)pid, 0U);
    if (descriptor < 0 || descriptor > INT_MAX)
        goto done;
    pidfd = (int)descriptor;
    reason = "process-executable-path";
    path_length = snprintf(path, sizeof(path), "/proc/%lu/exe", pid);
    if (path_length < 0 || path_length >= (int)sizeof(path))
        goto done;
    /* /proc/PID/exe is a kernel symlink and must be followed. Its opened file
     * is compared against the held candidate inode, never a displayed string.
     */
    executable = open(path, O_RDONLY | O_CLOEXEC);
    reason = "process-executable-mismatch";
    if (executable < 0 || fstat(executable, &actual_state) < 0 ||
        !S_ISREG(actual_state.st_mode) || actual_state.st_dev != expected_state.st_dev ||
        actual_state.st_ino != expected_state.st_ino)
        goto done;
    reason = "pidfd-signal-refused";
    if (syscall(SYS_pidfd_send_signal, pidfd, SIGTERM, NULL, 0U) != 0)
        goto done;
    result = 0;
done:
    if (executable >= 0)
        close(executable);
    if (pidfd >= 0)
        close(pidfd);
    if (expected >= 0)
        close(expected);
    if (input >= 0)
        close(input);
    if (directory >= 0)
        close(directory);
    if (result)
        fprintf(stderr, "kmsg-seal refused: %s\n", reason);
    return result;
}
