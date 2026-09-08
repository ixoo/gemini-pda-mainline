/* SPDX-License-Identifier: MIT */
/* Fixed, read-only preservation helper for the disconnect attempt. */
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#ifndef PRESERVER_BASE
#define PRESERVER_BASE "/a53-keyboard-disconnect"
#endif
#ifndef PRESERVER_OWNER_UID
#define PRESERVER_OWNER_UID 0
#endif

#define OUTPUT_LIMIT 524288U
#define FILE_COUNT 4U

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

static int write_all(const void *buffer, size_t length)
{
	const unsigned char *cursor = buffer;

	while (length) {
		ssize_t written = write(STDOUT_FILENO, cursor, length);
		if (written < 0 && errno == EINTR)
			continue;
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

int main(int argc, char **argv)
{
	int root = -1, run = -1, attempt = -1;

	(void)argv;
	if (argc != 1)
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
	if (text("__PRESERVE_FILES_END__\n__PRESERVE_END__\n"))
		return 2;
	close(attempt);
	close(run);
	close(root);
	return 0;
}
