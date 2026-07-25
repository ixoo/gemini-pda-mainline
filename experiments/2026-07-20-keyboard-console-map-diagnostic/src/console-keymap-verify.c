// SPDX-License-Identifier: GPL-2.0-or-later

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/kd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

enum {
	MAGIC_SIZE = 7,
	MAX_NR_KEYMAPS = 256,
	BKEYMAP_NR_KEYS = 128,
	KERNEL_NR_KEYS = 256,
	HEADER_SIZE = MAGIC_SIZE + MAX_NR_KEYMAPS,
	SHIFT_FN_TABLE = 3,
	K_HOLE_UAPI = 0x0200,
	K_ALLOCATED_UAPI = 0x027e,
	K_NOSUCHMAP_UAPI = 0x027f,
};

static const unsigned char bkeymap_magic[MAGIC_SIZE] = {
	'b', 'k', 'e', 'y', 'm', 'a', 'p'
};

static int is_planned_table(int table)
{
	switch (table) {
	case 0:
	case 1:
	case 2:
	case 3:
	case 4:
	case 5:
	case 8:
	case 12:
		return 1;
	default:
		return 0;
	}
}

static int is_source_table(int table)
{
	return is_planned_table(table) && table != SHIFT_FN_TABLE;
}

struct parsed_keymap {
	unsigned char flags[MAX_NR_KEYMAPS];
	uint16_t *entries;
	size_t table_count;
};

static int fail_errno(const char *operation)
{
	fprintf(stderr, "console-keymap-verify: %s: %s\n", operation,
		strerror(errno));
	return 1;
}

static int fail_format(const char *reason)
{
	fprintf(stderr, "console-keymap-verify: invalid bkeymap: %s\n", reason);
	return 1;
}

static int read_exact(int fd, unsigned char *buffer, size_t size)
{
	size_t offset = 0;

	while (offset < size) {
		ssize_t result = read(fd, buffer + offset, size - offset);

		if (result < 0) {
			if (errno == EINTR)
				continue;
			return -1;
		}
		if (result == 0) {
			errno = EIO;
			return -1;
		}
		offset += (size_t)result;
	}
	return 0;
}

static uint16_t entry_value(const struct parsed_keymap *keymap,
			    int wanted_table, int wanted_index)
{
	size_t offset = 0;
	int table;

	for (table = 0; table < MAX_NR_KEYMAPS; ++table) {
		if (!keymap->flags[table])
			continue;
		if (table == wanted_table)
			return keymap->entries[offset + (size_t)wanted_index];
		offset += BKEYMAP_NR_KEYS;
	}
	return K_NOSUCHMAP_UAPI;
}

static int parse_keymap(const char *path, struct parsed_keymap *keymap)
{
	struct stat before;
	struct stat after;
	unsigned char extra;
	unsigned char *data = NULL;
	size_t expected_size;
	size_t offset;
	size_t table_count = 0;
	ssize_t result;
	int fd = -1;
	int status = 1;
	int table;

	memset(keymap, 0, sizeof(*keymap));
	fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (fd < 0)
		return fail_errno("open keymap");
	if (fstat(fd, &before) < 0) {
		fail_errno("fstat keymap");
		goto out;
	}
	if (!S_ISREG(before.st_mode)) {
		fail_format("input is not a regular non-symlink file");
		goto out;
	}
	if (before.st_size < HEADER_SIZE) {
		fail_format("file is shorter than its header");
		goto out;
	}
	if ((uintmax_t)before.st_size > SIZE_MAX) {
		fail_format("file is too large");
		goto out;
	}
	data = malloc((size_t)before.st_size);
	if (data == NULL) {
		fail_errno("allocate keymap buffer");
		goto out;
	}
	if (read_exact(fd, data, (size_t)before.st_size) < 0) {
		fail_errno("read keymap");
		goto out;
	}
	do {
		result = read(fd, &extra, 1);
	} while (result < 0 && errno == EINTR);
	if (result < 0) {
		fail_errno("check keymap end");
		goto out;
	}
	if (result != 0) {
		fail_format("file grew while being read");
		goto out;
	}
	if (fstat(fd, &after) < 0) {
		fail_errno("repeat fstat keymap");
		goto out;
	}
	if (before.st_dev != after.st_dev || before.st_ino != after.st_ino ||
	    before.st_size != after.st_size ||
	    before.st_mtim.tv_sec != after.st_mtim.tv_sec ||
	    before.st_mtim.tv_nsec != after.st_mtim.tv_nsec) {
		fail_format("file changed while being read");
		goto out;
	}
	if (memcmp(data, bkeymap_magic, MAGIC_SIZE) != 0) {
		fail_format("magic is not bkeymap");
		goto out;
	}
	for (table = 0; table < MAX_NR_KEYMAPS; ++table) {
		unsigned char flag = data[MAGIC_SIZE + table];

		if (flag != 0 && flag != 1) {
			fail_format("table flag is not zero or one");
			goto out;
		}
		keymap->flags[table] = flag;
		table_count += flag;
		if ((flag != 0) != is_planned_table(table)) {
			fail_format("declared table set is not exact");
			goto out;
		}
	}
	if (table_count != 8) {
		fail_format("declared table count is not eight");
		goto out;
	}
	expected_size = HEADER_SIZE +
		table_count * BKEYMAP_NR_KEYS * sizeof(uint16_t);
	if ((size_t)before.st_size != expected_size) {
		fail_format("payload size does not match declared tables");
		goto out;
	}
	keymap->entries = calloc(table_count * BKEYMAP_NR_KEYS,
				 sizeof(*keymap->entries));
	if (keymap->entries == NULL) {
		fail_errno("allocate keymap entries");
		goto out;
	}
	offset = HEADER_SIZE;
	for (size_t index = 0; index < table_count * BKEYMAP_NR_KEYS; ++index) {
		keymap->entries[index] =
			(uint16_t)data[offset] | (uint16_t)data[offset + 1] << 8;
		offset += sizeof(uint16_t);
	}
	keymap->table_count = table_count;
	if (entry_value(keymap, SHIFT_FN_TABLE, 0) != K_HOLE_UAPI) {
		fail_format("Shift+Fn payload index zero is not K_HOLE");
		goto out;
	}
	status = 0;
out:
	free(data);
	if (close(fd) < 0 && status == 0)
		status = fail_errno("close keymap");
	if (status != 0) {
		free(keymap->entries);
		memset(keymap, 0, sizeof(*keymap));
	}
	return status;
}

static int open_unicode_tty(void)
{
	struct stat tty_stat;
	int mode = -1;
	int fd;

	fd = open("/dev/tty1", O_RDWR | O_CLOEXEC | O_NOCTTY | O_NOFOLLOW);
	if (fd < 0)
		return fail_errno("open /dev/tty1"), -1;
	if (fstat(fd, &tty_stat) < 0) {
		fail_errno("fstat /dev/tty1");
		close(fd);
		return -1;
	}
	if (!S_ISCHR(tty_stat.st_mode)) {
		fprintf(stderr, "console-keymap-verify: /dev/tty1 is not a character device\n");
		close(fd);
		return -1;
	}
	if (ioctl(fd, KDGKBMODE, &mode) < 0) {
		fail_errno("KDGKBMODE");
		close(fd);
		return -1;
	}
	if (mode != K_UNICODE) {
		fprintf(stderr,
			"console-keymap-verify: keyboard mode=%d expected=%d (K_UNICODE)\n",
			mode, K_UNICODE);
		close(fd);
		return -1;
	}
	return fd;
}

static int get_entry(int fd, int table, int index, uint16_t *value)
{
	struct kbentry entry = {
		.kb_table = (unsigned char)table,
		.kb_index = (unsigned char)index,
		.kb_value = 0,
	};

	if (ioctl(fd, KDGKBENT, &entry) < 0) {
		fprintf(stderr,
			"console-keymap-verify: KDGKBENT table=%d index=%d: %s\n",
			table, index, strerror(errno));
		return 1;
	}
	*value = entry.kb_value;
	return 0;
}

static int require_absent(int fd, int table, const char *phase)
{
	uint16_t actual;

	if (get_entry(fd, table, 0, &actual) != 0)
		return 1;
	if (actual != K_NOSUCHMAP_UAPI) {
		fprintf(stderr,
			"console-keymap-verify: %s table=%d index=0 expected=0x%04x "
			"actual=0x%04x\n",
			phase, table, K_NOSUCHMAP_UAPI, actual);
		return 1;
	}
	return 0;
}

static int preflight_keymap(void)
{
	int fd = open_unicode_tty();
	int status = 1;
	int table;

	if (fd < 0)
		return 1;
	for (table = 0; table < MAX_NR_KEYMAPS; ++table) {
		uint16_t actual;

		if (get_entry(fd, table, 0, &actual) != 0)
			goto out;
		if (is_source_table(table)) {
			if (actual == K_NOSUCHMAP_UAPI) {
				fprintf(stderr,
					"console-keymap-verify: preflight source table=%d is absent\n",
					table);
				goto out;
			}
		} else if (actual != K_NOSUCHMAP_UAPI) {
			fprintf(stderr,
				"console-keymap-verify: preflight undeclared table=%d "
				"expected=0x%04x actual=0x%04x\n",
				table, K_NOSUCHMAP_UAPI, actual);
			goto out;
		}
	}
	status = 0;
out:
	if (close(fd) < 0 && status == 0)
		status = fail_errno("close /dev/tty1");
	return status;
}

static int verify_loaded_keymap(const struct parsed_keymap *keymap)
{
	size_t entry_offset = 0;
	int fd = open_unicode_tty();
	int status = 1;
	int table;

	if (fd < 0)
		return 1;
	for (table = 0; table < MAX_NR_KEYMAPS; ++table) {
		if (!keymap->flags[table]) {
			if (require_absent(fd, table, "post-load") != 0)
				goto out;
			continue;
		}
		for (int index = 0; index < KERNEL_NR_KEYS; ++index) {
			uint16_t actual;
			uint16_t expected;

			if (index < BKEYMAP_NR_KEYS) {
				expected = keymap->entries[entry_offset++];
				if (table == SHIFT_FN_TABLE && index == 0)
					expected = K_ALLOCATED_UAPI;
			} else {
				expected = K_HOLE_UAPI;
			}

			if (get_entry(fd, table, index, &actual) != 0)
				goto out;
			/* KDGKBENT returns the UAPI value; do not apply U(x) again. */
			if (actual != expected) {
				fprintf(stderr,
					"console-keymap-verify: mismatch table=%d index=%d "
					"expected=0x%04x actual=0x%04x\n",
					table, index, expected, actual);
				goto out;
			}
		}
	}
	if (entry_offset != keymap->table_count * BKEYMAP_NR_KEYS) {
		fprintf(stderr, "console-keymap-verify: internal entry count mismatch\n");
		goto out;
	}
	status = 0;
out:
	if (close(fd) < 0 && status == 0)
		status = fail_errno("close /dev/tty1");
	return status;
}

static void usage(const char *program)
{
	fprintf(stderr, "usage: %s --check|--preflight|--verify BKEYMAP\n", program);
}

int main(int argc, char **argv)
{
	struct parsed_keymap keymap;
	int status;

	if (argc != 3 ||
	    (strcmp(argv[1], "--check") != 0 &&
	     strcmp(argv[1], "--preflight") != 0 &&
	     strcmp(argv[1], "--verify") != 0)) {
		usage(argv[0]);
		return 2;
	}
	status = parse_keymap(argv[2], &keymap);
	if (status != 0)
		return status;
	if (strcmp(argv[1], "--preflight") == 0) {
		status = preflight_keymap();
		if (status == 0)
			printf("keymap_preflight=verified source_tables=present "
			       "table3=K_NOSUCHMAP undeclared_tables=K_NOSUCHMAP "
			       "unicode_mode=K_UNICODE\n");
	} else if (strcmp(argv[1], "--verify") == 0) {
		status = verify_loaded_keymap(&keymap);
		if (status == 0)
			printf("keymap_readback=verified tables=%zu payload_entries=%zu "
			       "kernel_entries=%zu high_halves=K_HOLE "
			       "table3=K_ALLOCATED undeclared_tables=K_NOSUCHMAP "
			       "unicode_mode=K_UNICODE\n",
			       keymap.table_count,
			       keymap.table_count * BKEYMAP_NR_KEYS,
			       keymap.table_count * KERNEL_NR_KEYS);
	} else {
		printf("keymap_parser=valid tables=%zu entries=%zu "
		       "declared=0,1,2,3,4,5,8,12 table3_payload0=K_HOLE "
		       "undeclared=absent\n",
		       keymap.table_count,
		       keymap.table_count * BKEYMAP_NR_KEYS);
	}
	free(keymap.entries);
	return status;
}
