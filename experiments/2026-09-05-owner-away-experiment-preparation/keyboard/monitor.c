/* SPDX-License-Identifier: MIT */
/* One fixed observer child. Production admission/delivery is not enabled. */
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/syscall.h>
#endif

#define FILE_LIMIT 98304
#if defined(MONITOR_FIXTURE) && !defined(MONITOR_FULL_DURATION)
#define TERM_MS 300
#define KILL_MS 380
#define END_MS 500
#define GRACE_MS 80
#define REAP_MS 120
#define TICK_MS 2
static void fixture_child(void);
static void fixture_after_status(void);
static void fixture_after_defaults(void);
#else
#define TERM_MS 210000
#define KILL_MS 214000
#define END_MS 215000
#define GRACE_MS 4000
#define REAP_MS 1000
#define TICK_MS 20
#endif
#if defined(MONITOR_FIXTURE) && defined(MONITOR_FULL_DURATION)
static void fixture_child(void);
static void fixture_after_status(void);
static void fixture_after_defaults(void);
#endif

static volatile sig_atomic_t cancelled;
static void cancel(int sig) { if (!cancelled) cancelled = sig; }
static int64_t milliseconds(void)
{
	struct timespec t;
	return clock_gettime(CLOCK_MONOTONIC, &t) ? -1 :
		(int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static int store(int fd, const char *s, size_t n)
{
	while (n) {
		ssize_t k = write(fd, s, n);
		if (k < 0 && errno == EINTR) continue;
		if (k <= 0) return -1;
		s += k; n -= (size_t)k;
	}
	return 0;
}
static int exclusive(int dir, const char *name)
{
	return openat(dir, name, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
}
static int file_size(int fd, off_t *size)
{
	struct stat s;
	if (fstat(fd, &s) || !S_ISREG(s.st_mode) || s.st_nlink != 1 ||
	    s.st_uid != getuid() || (s.st_mode & 0777) != 0600 ||
	    s.st_size < 0 || s.st_size > FILE_LIMIT) return -1;
	*size = s.st_size;
	return 0;
}
static int forward(int fd, off_t size, off_t *sent)
{
	char b[4096];
	if (*sent > size) return -1;
	if (*sent == size) return 0;
	size_t n = size - *sent < (off_t)sizeof(b) ? (size_t)(size - *sent) : sizeof(b);
	ssize_t got = pread(fd, b, n, *sent);
	if (got < 0 && errno == EINTR) return 0;
	if (got <= 0) return -1;
	ssize_t wrote = write(STDOUT_FILENO, b, (size_t)got);
	if (wrote < 0 && errno == EINTR) return 0;
	/* EAGAIN is an explicit stalled-forwarding refusal, never a blocking retry. */
	if (wrote <= 0) return -1;
	*sent += wrote;
	return 0;
}
static int close_extra(void)
{
#ifdef __linux__
	/* Use the platform header's syscall number; no handwritten ABI layout.
	 * Unsupported close_range refuses before exec, rather than leaking fds. */
	return syscall(SYS_close_range, 3U, ~0U, 0U) < 0 ? -1 : 0;
#elif defined(MONITOR_FIXTURE)
	/* Fixture runner admits only fds below 1024 on this non-Linux host. */
	for (int fd = 3; fd < 1024; ++fd) close(fd);
	return 0;
#else
	return -1;
#endif
}
static bool canonical_number(const char *s, unsigned int max)
{
	unsigned int n = 0;
	if (!s || !*s || (s[0] == '0' && s[1])) return false;
	for (; *s; ++s) {
		if (*s < '0' || *s > '9' || n > max / 10) return false;
		n = n * 10 + (unsigned int)(*s - '0');
		if (n > max) return false;
	}
	return true;
}

/* Caller must already own and verify the private RAM parent and real admission.
 * No caller is wired in production. This engine never manufactures those facts.
 * Keep this symbol in a size-test link with -Wl,-u,keyboard_monitor_run. */
int keyboard_monitor_run(int parent, const char *event, const char *minor)
{
	int dir = -1, out = -1, err = -1, statusfd = -1, child_status = 0;
	pid_t child = -1;
	bool reaped = false, terminal = false, identity_lost = false, late = false;
	const char *reason = NULL;
	off_t out_size = 0, err_size = 0, sent = 0;
	int term_error = 0, kill_error = 0;
	int64_t start = milliseconds(), term_time = -1, kill_time = -1, reap_time = -1;
	int64_t kill_at = start + KILL_MS, end_at = start + END_MS;
	struct sigaction action = { .sa_handler = cancel }, ordinary = { .sa_handler = SIG_DFL };
	sigset_t blocked, original;
	bool mask_held = false;
#define FAIL(why) do { if (!reason) reason = (why); } while (0)
	if (start < 0 || !event || strncmp(event, "event", 5) ||
	    !canonical_number(event + 5, 255) || !canonical_number(minor, 1048575)) return 2;
	for (int fd = 0; fd < 3; ++fd) if (fcntl(fd, F_GETFD) < 0) return 2;
	sigemptyset(&action.sa_mask); sigemptyset(&ordinary.sa_mask); sigemptyset(&blocked);
	const int signals[] = { SIGINT, SIGTERM, SIGHUP, SIGPIPE, SIGXFSZ };
	for (size_t i = 0; i < sizeof(signals) / sizeof(signals[0]); ++i) {
		if (sigaction(signals[i], &action, NULL)) return 2;
		sigaddset(&blocked, signals[i]);
	}
	if (sigaction(SIGCHLD, &ordinary, NULL)) return 2;
	/* mkdir is the once-only claim, retained on every following failure. */
	if (mkdirat(parent, "keyboard-attempt", 0700)) return 2;
	dir = openat(parent, "keyboard-attempt", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (dir < 0) return 2;
	out = exclusive(dir, "observer.stdout"); err = exclusive(dir, "observer.stderr");
	statusfd = exclusive(dir, "monitor.status");
	int flags = fcntl(STDOUT_FILENO, F_GETFL);
	if (out < 0 || err < 0 || statusfd < 0 || flags < 0 ||
	    fcntl(STDOUT_FILENO, F_SETFL, flags | O_NONBLOCK) || fsync(dir) || fsync(parent)) {
		FAIL("setup"); goto finish;
	}
	if (sigprocmask(SIG_BLOCK, &blocked, &original)) { FAIL("signal-mask"); goto finish; }
	mask_held = true;
	for (size_t i = 0; i < sizeof(signals) / sizeof(signals[0]); ++i)
		if (sigismember(&original, signals[i])) { FAIL("inherited-blocked-signal"); goto finish; }
	if (cancelled) { FAIL("cancelled-before-fork"); goto finish; }
	child = fork();
	if (child < 0) { FAIL("fork"); goto finish; }
	if (!child) {
		struct rlimit limit;
		if (getrlimit(RLIMIT_FSIZE, &limit)) _exit(125);
		if (limit.rlim_cur > FILE_LIMIT) limit.rlim_cur = FILE_LIMIT;
		limit.rlim_max = limit.rlim_cur; /* Never raise even an inherited soft limit. */
		int null = open("/dev/null", O_RDONLY | O_CLOEXEC);
		if (null < 0 || dup2(null, 0) < 0 || dup2(out, 1) < 0 || dup2(err, 2) < 0 ||
		    setrlimit(RLIMIT_FSIZE, &limit) || close_extra()) _exit(125);
		for (size_t i = 0; i < sizeof(signals) / sizeof(signals[0]); ++i)
			if (sigaction(signals[i], &ordinary, NULL)) _exit(125);
		if (sigprocmask(SIG_SETMASK, &original, NULL)) _exit(125);
#ifdef MONITOR_FIXTURE
		(void)event; (void)minor; fixture_child();
#else
		execl("/bin/keyboard-observe", "keyboard-observe", "--capture", event, "13", minor, (char *)NULL);
#endif
		_exit(126);
	}
	if (sigprocmask(SIG_SETMASK, &original, NULL)) FAIL("signal-unmask");
	mask_held = false;
	for (;;) {
		int64_t now = milliseconds();
		if (now < 0) { FAIL("clock"); now = end_at; }
		siginfo_t info = {0};
		if (waitid(P_PID, (id_t)child, &info, WEXITED | WNOHANG | WNOWAIT)) {
			if (errno == EINTR) continue;
			/* ECHILD could mean someone else reaped it: never signal a reused PID. */
			identity_lost = true; FAIL("waitid-identity"); break;
		}
		terminal = info.si_pid == child;
		if (file_size(out, &out_size) || file_size(err, &err_size)) FAIL("retained-file");
		if (err_size) FAIL("observer-stderr");
		if (cancelled) FAIL("cancelled");
		if (!reason && forward(out, out_size, &sent)) FAIL("forward-close-or-stall");
		if (now >= start + TERM_MS && !terminal) FAIL("deadline");
		if (now >= end_at) { late = true; FAIL("reap-deadline"); }
		if (terminal && (reason || sent == out_size)) {
			pid_t got = waitpid(child, &child_status, WNOHANG);
			if (got == child) { reaped = true; reap_time = milliseconds() - start; break; }
			if (got < 0 && errno != EINTR) { identity_lost = true; FAIL("reap-identity"); break; }
		}
		if (reason && !terminal && term_time < 0) {
			term_time = milliseconds() - start;
			if (kill(child, SIGTERM)) term_error = errno;
			if (now + GRACE_MS < kill_at) kill_at = now + GRACE_MS;
			if (kill_at + REAP_MS < end_at) end_at = kill_at + REAP_MS;
		}
		if (!terminal && now >= kill_at && kill_time < 0) {
			kill_time = milliseconds() - start;
			if (kill(child, SIGKILL)) kill_error = errno;
		}
		if (now >= end_at) break;
		int64_t next = end_at;
		if (term_time < 0 && start + TERM_MS < next) next = start + TERM_MS;
		if (kill_time < 0 && kill_at < next) next = kill_at;
		int delay = next - now < TICK_MS ? (int)(next - now) : TICK_MS;
		if (delay > 0 && poll(NULL, 0, delay) < 0 && errno != EINTR) FAIL("poll");
	}
	if (!reaped || !WIFEXITED(child_status) || WEXITSTATUS(child_status)) FAIL("observer-exit");
	if (reap_time > end_at - start || term_time > TERM_MS || kill_time > KILL_MS) late = true;
finish:
	if (mask_held && sigprocmask(SIG_SETMASK, &original, NULL)) FAIL("signal-unmask");
	if (out >= 0 && fsync(out)) FAIL("stdout-sync");
	if (err >= 0 && fsync(err)) FAIL("stderr-sync");
	if (cancelled) FAIL("cancelled");
	if (milliseconds() > end_at) { late = true; FAIL("finish-deadline"); }
	if (statusfd >= 0) {
		char record[1024];
		int n = snprintf(record, sizeof(record),
			"schema=keyboard-monitor-v1\nreason=%s\nreaped=%d\nidentity_lost=%d\n"
			"exit=%d\nsignal=%d\ncancel=%d\nterm_ms=%lld\nkill_ms=%lld\nreap_ms=%lld\n"
			"term_errno=%d\nkill_errno=%d\nlate=%d\nstdout_bytes=%lld\nstderr_bytes=%lld\nforwarded_bytes=%lld\n",
			reason ? reason : "normal-lifecycle-only", reaped, identity_lost,
			reaped && WIFEXITED(child_status) ? WEXITSTATUS(child_status) : -1,
			reaped && WIFSIGNALED(child_status) ? WTERMSIG(child_status) : 0, (int)cancelled,
			(long long)term_time, (long long)kill_time, (long long)reap_time,
			term_error, kill_error, late, (long long)out_size, (long long)err_size, (long long)sent);
		if (n < 0 || (size_t)n >= sizeof(record) || store(statusfd, record, (size_t)n) || fsync(statusfd)) FAIL("status-sync");
	}
	if (out >= 0) close(out);
	if (err >= 0) close(err);
	if (statusfd >= 0) close(statusfd);
	if (fsync(dir)) FAIL("directory-sync");
	close(dir);
#ifdef MONITOR_FIXTURE
	fixture_after_status();
#endif
	/* After the last cancellation check, a signal must still make the process
	 * nonzero. Restore defaults first: late signals then terminate it instead
	 * of setting a flag after the return condition has already been evaluated. */
	for (size_t i = 0; i < sizeof(signals) / sizeof(signals[0]); ++i)
		if (sigaction(signals[i], &ordinary, NULL)) FAIL("final-signal-disposition");
#ifdef MONITOR_FIXTURE
	fixture_after_defaults();
#endif
	int64_t finished = milliseconds();
	if (finished < 0 || finished > end_at) late = true;
	/* RAM status alone never grants acceptance: require this process status too. */
	return reason || cancelled || late ? 2 : 0;
#undef FAIL
}

#ifndef MONITOR_FIXTURE
#ifndef KEYBOARD_MONITOR_ENABLED
#define KEYBOARD_MONITOR_ENABLED 0
#endif
int main(int argc, char **argv)
{
#if KEYBOARD_MONITOR_ENABLED
	/* Only the reviewed host admission adapter may deliver an enabled build.
	 * The target entry still accepts no command, parent path or helper override. */
	if (argc != 3) return 2;
	int parent = open("/a53-keyboard-delivery", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	struct stat st;
	if (parent < 0 || fstat(parent, &st) || st.st_uid != 0 ||
	    (st.st_mode & 0777) != 0700) return 2;
	int result = keyboard_monitor_run(parent, argv[1], argv[2]);
	close(parent);
	return result;
#else
	(void)argc; (void)argv;
	static const char refusal[] = "refused: target-admission-disabled\n";
	(void)store(2, refusal, sizeof(refusal) - 1);
	return 2;
#endif
}
#endif
