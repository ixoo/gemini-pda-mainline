/* SPDX-License-Identifier: MIT */
/* Fixed, read-only preservation helper for the disconnect attempt. */
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE
#include <errno.h>
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#ifdef __linux__
#include <sys/sysmacros.h>
#endif
#include <time.h>
#include <unistd.h>

#ifndef PRESERVER_BASE
#define PRESERVER_BASE "/a53-keyboard-disconnect"
#endif
#ifndef PRESERVER_OWNER_UID
#define PRESERVER_OWNER_UID 0
#endif
#ifndef PRESERVER_PROC
#define PRESERVER_PROC "/proc"
#endif
#ifndef PRESERVER_DEADLINE_MS
#define PRESERVER_DEADLINE_MS 15000
#endif

#define OUTPUT_LIMIT 524288U
#define FILE_COUNT 4U
#define PROCESS_LIMIT 512U
#define DESCRIPTOR_LIMIT 4096U
#define MATCH_LIMIT 256U
#define PROC_VALUE_LIMIT 4096U

struct file_spec {
	const char *name;
	unsigned int limit;
};

static const struct file_spec files[FILE_COUNT] = {
	{ "observer.stdout", 98304U },
	{ "observer.stderr", 98304U },
	{ "monitor.status", 4096U },
	{ "outer-exit", 16U },
};

struct identity {
	dev_t dev;
	ino_t ino;
	off_t size;
};

static unsigned int output_bytes;
static int64_t deadline_ms;
static bool deadline_hit;

static int64_t monotonic_milliseconds(void)
{
	struct timespec now;

	if (clock_gettime(CLOCK_MONOTONIC, &now))
		return -1;
	return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int deadline_expired(void)
{
	int64_t now = monotonic_milliseconds();

	if (now < 0 || now >= deadline_ms)
		deadline_hit = true;
	return deadline_hit;
}

static int write_all(const void *buffer, size_t length)
{
	const unsigned char *cursor = buffer;

	while (length) {
		if (deadline_expired())
			return -1;
		ssize_t written = write(STDOUT_FILENO, cursor, length);
		if (written < 0 && errno == EINTR)
			continue;
		if (written < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
			struct pollfd output = { .fd = STDOUT_FILENO, .events = POLLOUT };
			int64_t now = monotonic_milliseconds();
			int timeout = now < 0 || now >= deadline_ms ? 0 :
				(int)(deadline_ms - now > 1000 ? 1000 : deadline_ms - now);
			if (poll(&output, 1, timeout) <= 0 || deadline_expired())
				return -1;
			continue;
		}
		if (written <= 0 || (size_t)written > length ||
			output_bytes > OUTPUT_LIMIT - (unsigned int)written)
			return -1;
		output_bytes += (unsigned int)written;
		cursor += written;
		length -= (size_t)written;
	}
	return 0;
}

static int text(const char *value)
{
	return write_all(value, strlen(value));
}

static int poll_readable(int fd)
{
	struct pollfd input = { .fd = fd, .events = POLLIN };
	int64_t now = monotonic_milliseconds();
	int timeout = now < 0 || now >= deadline_ms ? 0 :
		(int)(deadline_ms - now > 1000 ? 1000 : deadline_ms - now);

	return poll(&input, 1, timeout) > 0 && !deadline_expired() ? 0 : -1;
}

static int directory_ok(int fd)
{
	struct stat info;

	return fstat(fd, &info) == 0 && S_ISDIR(info.st_mode) &&
		info.st_uid == (uid_t)PRESERVER_OWNER_UID &&
		(info.st_mode & 07777) == 0700 && info.st_nlink >= 2;
}

static int identity_from_stat(const struct stat *info, struct identity *identity)
{
	if (!S_ISREG(info->st_mode) || info->st_uid != (uid_t)PRESERVER_OWNER_UID ||
		(info->st_mode & 07777) != 0600 || info->st_nlink != 1 ||
		info->st_size < 0)
		return -1;
	identity->dev = info->st_dev;
	identity->ino = info->st_ino;
	identity->size = info->st_size;
	return 0;
}

static int same_identity(const struct identity *left, const struct identity *right)
{
	return left->dev == right->dev && left->ino == right->ino &&
		left->size == right->size;
}

static int identity_text(const struct identity *identity, char *buffer, size_t size)
{
	int written = snprintf(buffer, size, "%llu:%llu",
		(unsigned long long)identity->dev, (unsigned long long)identity->ino);
	return written < 0 || (size_t)written >= size ? -1 : written;
}

static int number_text(off_t value, char *buffer, size_t size)
{
	int written = snprintf(buffer, size, "%lld", (long long)value);
	return written < 0 || (size_t)written >= size ? -1 : written;
}

static int emit_file(const struct file_spec *spec, const char *state,
	const struct identity *before, const struct identity *after,
	const unsigned char *data, size_t data_length, const char *read_status,
	const char *stable)
{
	char line[192];
	int written;
	char before_id[64] = "-";
	char after_id[64] = "-";
	char before_size[32] = "-";
	char after_size[32] = "-";

	if (before) {
		if (identity_text(before, before_id, sizeof(before_id)) < 0 ||
			number_text(before->size, before_size, sizeof(before_size)) < 0)
			return -1;
	}
	if (after) {
		if (identity_text(after, after_id, sizeof(after_id)) < 0 ||
			number_text(after->size, after_size, sizeof(after_size)) < 0)
			return -1;
	}
	written = snprintf(line, sizeof(line),
		"__PRESERVE_FILE_BEGIN__\nname=%s\nstate=%s\nsize_before=%s\n"
		"identity_before=%s\nlimit=%u\ndata_bytes=%zu\n"
		"__PRESERVE_DATA_BEGIN__\n", spec->name, state, before_size,
		before_id, spec->limit, data_length);
	if (written < 0 || (size_t)written >= sizeof(line) || text(line))
		return -1;
	if (data_length && write_all(data, data_length))
		return -1;
	if (text("\n__PRESERVE_META_BEGIN__\n"))
		return -1;
	written = snprintf(line, sizeof(line),
		"size_after=%s\nidentity_after=%s\nread_status=%s\n"
		"stable=%s\ncaptured_bytes=%zu\n__PRESERVE_FILE_END__\n",
		after_size, after_id, read_status, stable, data_length);
	if (written < 0 || (size_t)written >= sizeof(line) || text(line))
		return -1;
	return 0;
}

static int preserve_one(int dir, const struct file_spec *spec)
{
	unsigned char data[98304];
	struct stat path_before_stat, path_after_stat, fd_before_stat, fd_after_stat;
	struct identity path_before, path_after, before, after;
	const char *state = "open-failed";
	const char *read_status = "none";
	const char *stable = "not-applicable";
	int fd = -1;
	int path_errno;
	size_t total = 0;
	bool regular = false;

	if (fstatat(dir, spec->name, &path_before_stat, AT_SYMLINK_NOFOLLOW)) {
		if (errno == ENOENT)
			return emit_file(spec, "missing", NULL, NULL, NULL, 0, "none",
				"not-applicable");
		return emit_file(spec, "open-failed", NULL, NULL, NULL, 0, "none",
			"not-applicable");
	}
	if (S_ISLNK(path_before_stat.st_mode))
		return emit_file(spec, "symlink", NULL, NULL, NULL, 0, "none",
			"not-applicable");
	if (!S_ISREG(path_before_stat.st_mode))
		return emit_file(spec, "nonregular", NULL, NULL, NULL, 0, "none",
			"not-applicable");
	if (identity_from_stat(&path_before_stat, &path_before))
		return emit_file(spec, "unsafe", NULL, NULL, NULL, 0, "none",
			"not-applicable");

	fd = openat(dir, spec->name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
	path_errno = errno;
	if (fd < 0) {
		state = path_errno == ELOOP ? "symlink" : "open-failed";
		return emit_file(spec, state, NULL, NULL, NULL, 0, "none",
			"not-applicable");
	}
	if (fstat(fd, &fd_before_stat)) {
		(void)close(fd);
		return emit_file(spec, "read-failed", NULL, NULL, NULL, 0, "error",
			"no");
	}
	if (identity_from_stat(&fd_before_stat, &before)) {
		(void)close(fd);
		return emit_file(spec, "unsafe", NULL, NULL, NULL, 0, "none",
			"no");
	}
	if (!same_identity(&path_before, &before)) {
		(void)close(fd);
		return emit_file(spec, "changing", &before, NULL, NULL, 0, "none", "no");
	}
	if (before.size > (off_t)spec->limit) {
		(void)close(fd);
		return emit_file(spec, "oversized", &before, NULL, NULL, 0, "none", "no");
	}
	state = "regular";
	regular = true;
#ifdef PRESERVER_TEST_PAUSE_US
	{
		struct timespec pause = { PRESERVER_TEST_PAUSE_US / 1000000,
			(PRESERVER_TEST_PAUSE_US % 1000000) * 1000L };
		static const char opened[] = "__PRESERVER_TEST_OPENED__\n";
		(void)write(STDERR_FILENO, opened, sizeof(opened) - 1);
		(void)nanosleep(&pause, NULL);
	}
#endif
	while (total < (size_t)before.size) {
		if (deadline_expired()) {
			state = "read-failed";
			read_status = "deadline";
			break;
		}
		ssize_t got = read(fd, data + total, (size_t)before.size - total);
		if (got < 0 && errno == EINTR)
			continue;
		if (got < 0) {
			read_status = errno == EAGAIN ? "would-block" : "error";
			state = "read-failed";
			break;
		}
		if (got == 0) {
			state = "changing";
			read_status = "short-read";
			break;
		}
		total += (size_t)got;
	}
	if (regular && total == (size_t)before.size && !strcmp(read_status, "none"))
		read_status = "0";
	bool post_ok = !fstat(fd, &fd_after_stat) &&
		!fstatat(dir, spec->name, &path_after_stat, AT_SYMLINK_NOFOLLOW) &&
		!identity_from_stat(&fd_after_stat, &after) &&
		!identity_from_stat(&path_after_stat, &path_after) &&
		same_identity(&before, &after) && same_identity(&before, &path_after) &&
		total == (size_t)before.size;
	if (!post_ok) {
		if (!strcmp(state, "regular"))
			state = "changing";
		stable = "no";
	} else if (!strcmp(read_status, "0")) {
		state = "regular";
		stable = "yes";
	}
	if (close(fd)) {
		state = "read-failed";
		stable = "no";
	}
	return emit_file(spec, state, &before, post_ok ? &after : NULL, data, total,
		read_status, stable);
}

struct scan_result {
	unsigned int processes;
	unsigned int descriptors;
	unsigned int matches;
	unsigned int cmdline_matches;
	unsigned int exe_matches;
	unsigned int exe_deleted_matches;
	unsigned int console_matches;
	unsigned int input_matches;
	bool match_overflow;
	const char *status;
};

static int numeric_entry(const char *name)
{
	if (!name || !*name || (name[0] == '0' && name[1]))
		return 0;
	for (const char *cursor = name; *cursor; ++cursor)
		if (*cursor < '0' || *cursor > '9')
			return 0;
	return 1;
}

static int fixed_match(const unsigned char *data, size_t length,
	const char *needle)
{
	size_t needle_length = strlen(needle);

	if (!needle_length || needle_length > length)
		return 0;
	for (size_t i = 0; i + needle_length <= length; ++i)
		if (!memcmp(data + i, needle, needle_length))
			return 1;
	return 0;
}

static int read_proc_value(int fd, unsigned char *data, size_t capacity,
	size_t *length)
{
	*length = 0;
	while (*length < capacity) {
		ssize_t got;

		if (deadline_expired())
			return -2;
		got = read(fd, data + *length, capacity - *length);
		if (got < 0 && (errno == EINTR))
			continue;
		if (got < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
			if (poll_readable(fd))
				return -2;
			continue;
		}
		if (got < 0 || got == 0)
			return got == 0 ? 0 : -1;
		*length += (size_t)got;
	}
	return -1;
}

static int add_match(struct scan_result *result, unsigned int *category)
{
	if (result->matches == MATCH_LIMIT) {
		result->match_overflow = true;
		result->status = "overflow";
		return -1;
	}
	++result->matches;
	++*category;
	return 0;
}

static int scan_descriptor_dir(int fd, struct scan_result *result)
{
	DIR *directory;
	struct dirent *entry;
	struct stat before, after;

	directory = fdopendir(fd);
	if (!directory) {
		close(fd);
		return -1;
	}
	if (fstat(fd, &before)) {
		closedir(directory);
		return -1;
	}
	for (;;) {
		char target[256];
		ssize_t length;
		struct stat target_info;
		bool path_match;

		errno = 0;
		entry = readdir(directory);
		if (!entry)
			break;
		if (deadline_expired()) {
			result->status = "deadline";
			closedir(directory);
			return -2;
		}
		if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, ".."))
			continue;
		if (!numeric_entry(entry->d_name)) {
			if (entry->d_name[0] == '0' ||
				(entry->d_name[0] >= '1' && entry->d_name[0] <= '9'))
				result->status = "incomplete";
			continue;
		}
		if (result->descriptors == DESCRIPTOR_LIMIT) {
			result->status = "overflow";
			closedir(directory);
			return -2;
		}
		++result->descriptors;
		length = readlinkat(dirfd(directory), entry->d_name, target,
			sizeof(target) - 1);
		if (length < 0) {
			result->status = "incomplete";
			continue;
		}
		if ((size_t)length >= sizeof(target) - 1) {
			result->status = "incomplete";
			continue;
		}
		target[length] = '\0';
		path_match = !strcmp(target, "/dev/tty0") || !strcmp(target, "/dev/tty1") ||
			!strcmp(target, "/dev/console") || !strncmp(target, "/dev/input/", 11);
		if (path_match) {
			int match_status = !strncmp(target, "/dev/input/", 11) ?
				add_match(result, &result->input_matches) :
				add_match(result, &result->console_matches);
			if (match_status) {
				closedir(directory);
				return -2;
			}
		}
		if (fstatat(dirfd(directory), entry->d_name, &target_info, 0)) {
			result->status = "incomplete";
			continue;
		}
		if (!path_match && S_ISCHR(target_info.st_mode) &&
			((major(target_info.st_rdev) == 4 &&
				(minor(target_info.st_rdev) == 0 || minor(target_info.st_rdev) == 1)) ||
			 (major(target_info.st_rdev) == 5 &&
				(minor(target_info.st_rdev) == 0 || minor(target_info.st_rdev) == 1)))) {
			if (add_match(result, &result->console_matches)) {
				closedir(directory);
				return -2;
			}
		}
		if (!path_match && S_ISCHR(target_info.st_mode) && major(target_info.st_rdev) == 13 &&
			add_match(result, &result->input_matches)) {
			closedir(directory);
			return -2;
		}
	}
	if (errno || fstat(fd, &after) || before.st_dev != after.st_dev ||
		before.st_ino != after.st_ino) {
		result->status = "incomplete";
		closedir(directory);
		return -1;
	}
	closedir(directory);
	return 0;
}

static int scan_process(int proc, const char *name, struct scan_result *result)
{
	unsigned char command[PROC_VALUE_LIMIT];
	struct stat before, after, command_before, command_after;
	size_t length;
	int process = -1, command_fd = -1, descriptors = -1;
	int status = 0;

	process = openat(proc, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (process < 0)
		return -1;
	if (fstat(process, &before) || !S_ISDIR(before.st_mode)) {
		close(process);
		return -1;
	}
	{
		char executable[256];
		static const char deleted[] = " (deleted)";
		ssize_t length = readlinkat(process, "exe", executable, sizeof(executable) - 1);
		if (length < 0 || (size_t)length >= sizeof(executable) - 1) {
			status = -1;
		} else {
			bool is_deleted = (size_t)length >= sizeof(deleted) - 1 &&
				!memcmp(executable + length - (sizeof(deleted) - 1), deleted,
					sizeof(deleted) - 1);
			size_t identity_length = is_deleted ? (size_t)length - (sizeof(deleted) - 1) :
				(size_t)length;
			executable[identity_length] = '\0';
			if ((!strcmp(executable, "/a53-keyboard-disconnect/probe") ||
				!strcmp(executable, "/bin/keyboard-observe"))) {
				if (add_match(result, &result->exe_matches))
					status = -2;
				else if (is_deleted && add_match(result, &result->exe_deleted_matches))
					status = -2;
			}
		}
	}
	if (status != -2)
		command_fd = openat(process, "cmdline", O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
	if (status != -2 && command_fd < 0) {
		status = -1;
	} else if (status != -2) {
		int read_status = fstat(command_fd, &command_before) ? -1 :
			read_proc_value(command_fd, command, sizeof(command), &length);
		if (read_status) {
			status = read_status == -2 ? -2 : -1;
		} else if (fstat(command_fd, &command_after) ||
			command_before.st_dev != command_after.st_dev ||
			command_before.st_ino != command_after.st_ino ||
			command_before.st_size != command_after.st_size) {
			status = -1;
		} else {
			static const char *const needles[] = {
				"/a53-keyboard-disconnect/probe", "/bin/keyboard-observe",
				"getty", "local-shell"
			};
			for (size_t i = 0; i < sizeof(needles) / sizeof(needles[0]); ++i)
				if (fixed_match(command, length, needles[i]) &&
					add_match(result, &result->cmdline_matches)) {
					status = -2;
					break;
				}
		}
	}
	if (status != -2) {
		descriptors = openat(process, "fd", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
		if (descriptors < 0)
			status = -1;
		else {
			if (scan_descriptor_dir(descriptors, result))
				status = result->status && (!strcmp(result->status, "overflow") ||
					!strcmp(result->status, "deadline")) ? -2 : -1;
			descriptors = -1;
		}
	}
	if (command_fd >= 0)
		close(command_fd);
	if (fstat(process, &after) || before.st_dev != after.st_dev ||
		before.st_ino != after.st_ino)
		status = status == -2 ? -2 : -1;
	if (status == -2 && deadline_hit)
		result->status = "deadline";
	if (process >= 0)
		close(process);
	return status;
}

static int emit_scan(const struct scan_result *result)
{
	char line[512];
	int written = snprintf(line, sizeof(line),
		"__PRESERVE_SCAN_BEGIN__\nprocesses=%u\ndescriptors=%u\n"
		"matches=%u\ncmdline_matches=%u\nexe_matches=%u\n"
		"exe_deleted_matches=%u\nconsole_matches=%u\ninput_matches=%u\n"
		"match_overflow=%s\nscan_status=%s\n__PRESERVE_SCAN_END__\n",
		result->processes, result->descriptors, result->matches,
		result->cmdline_matches, result->exe_matches, result->exe_deleted_matches,
		result->console_matches, result->input_matches,
		result->match_overflow ? "yes" : "no", result->status);
	return written < 0 || (size_t)written >= sizeof(line) || text(line) ? -1 : 0;
}

static int scan_proc(struct scan_result *result)
{
	DIR *directory;
	struct dirent *entry;
	int proc;

	proc = open(PRESERVER_PROC, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
	if (proc < 0) {
		result->status = "incomplete";
		return -1;
	}
	directory = fdopendir(proc);
	if (!directory) {
		close(proc);
		result->status = "incomplete";
		return -1;
	}
	for (;;) {
		int status;

		errno = 0;
		entry = readdir(directory);
		if (!entry)
			break;

		if (deadline_expired()) {
			result->status = "deadline";
			break;
		}
		if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, ".."))
			continue;
		if (!numeric_entry(entry->d_name)) {
			if (entry->d_name[0] == '0' ||
				(entry->d_name[0] >= '1' && entry->d_name[0] <= '9'))
				result->status = "incomplete";
			continue;
		}
		if (result->processes == PROCESS_LIMIT) {
			result->status = "overflow";
			break;
		}
		++result->processes;
		status = scan_process(dirfd(directory), entry->d_name, result);
		if (status == -2 || (result->status &&
			(!strcmp(result->status, "overflow") || !strcmp(result->status, "deadline"))))
			break;
		if (status)
			result->status = "incomplete";
	}
	if (!result->status || !strcmp(result->status, "passed")) {
		if (errno)
			result->status = "incomplete";
		else
			result->status = "passed";
	}
	closedir(directory);
	return !strcmp(result->status, "passed") ? 0 : -1;
}

int main(int argc, char **argv)
{
	int root = -1, run = -1, attempt = -1, flags;
	struct scan_result scan = { 0 };
	int64_t start;

	(void)argv;
	start = monotonic_milliseconds();
	if (start < 0 || PRESERVER_DEADLINE_MS <= 0)
		return 2;
	deadline_ms = start + PRESERVER_DEADLINE_MS;
	if (argc != 1)
		return 2;
	flags = fcntl(STDOUT_FILENO, F_GETFL);
	if (flags < 0 || fcntl(STDOUT_FILENO, F_SETFL, flags | O_NONBLOCK))
		return 2;
	if (text("__PRESERVE_BEGIN__\nschema=keyboard-disconnect-preservation-v1\n"
		"stage=files\n__PRESERVE_HEADER_END__\n"))
		return 2;
	root = open(PRESERVER_BASE, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (root < 0 || !directory_ok(root))
		return 2;
	run = openat(root, "run", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (run < 0 || !directory_ok(run))
		return 2;
	attempt = openat(run, "keyboard-attempt", O_RDONLY | O_DIRECTORY |
		O_NOFOLLOW | O_CLOEXEC);
	if (attempt < 0 || !directory_ok(attempt))
		return 2;
	for (size_t i = 0; i < FILE_COUNT; ++i) {
		if (preserve_one(attempt, &files[i]))
			return 2;
	}
	if (text("__PRESERVE_FILES_END__\n"))
		return 2;
	(void)scan_proc(&scan);
	if (deadline_expired())
		scan.status = "deadline";
	if (!scan.status)
		scan.status = "incomplete";
	if (emit_scan(&scan))
		return 2;
	if (text("__PRESERVE_END__\n"))
		return 2;
	close(attempt);
	close(run);
	close(root);
	return !strcmp(scan.status, "passed") && !deadline_expired() ? 0 : 2;
}
