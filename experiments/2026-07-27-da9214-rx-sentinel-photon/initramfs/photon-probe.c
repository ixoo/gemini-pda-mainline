// SPDX-License-Identifier: GPL-2.0-only
/*
 * Fixed-function receive-buffer pre/post observer for the Gemini PDA's DA9214.
 *
 * This program accepts no arguments. It finds only MT6797 I2C6 through its
 * exact OF path and issues the same six combined register-pointer/read
 * transactions as Candidate Cassini:
 *
 *     0x69:{0x05,0x06,0x47}, twice.
 *
 * The sole wire-neutral observation change is a distinct nonzero byte placed
 * in each receive buffer immediately before its ioctl. Both passes always run
 * after successful transfers so distinct prefills for the same register can
 * distinguish a stable returned byte that equals one prefill from the
 * ambiguous observation of one post-read byte matching its prefill.
 * No page, regulator, CPU, storage, watchdog, reboot, or other
 * hardware-control operation is reachable.
 */

#define _POSIX_C_SOURCE 200809L

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define PHOTON_I2C_CLASS "/sys/class/i2c-dev"
#define PHOTON_I2C_OF_SUFFIX "/i2c@1100e000"
#define PHOTON_I2C_ADDR 0x69U
#define PHOTON_I2C_RDWR 0x0707UL
#define PHOTON_I2C_M_RD 0x0001U
#define PHOTON_PASSES 2U
#define PHOTON_REGISTER_COUNT 3U
#define PHOTON_TRANSACTION_COUNT (PHOTON_PASSES * PHOTON_REGISTER_COUNT)
#define PHOTON_MESSAGE_COUNT 2U
#define PHOTON_PATH_SIZE 512U
#define PHOTON_LINE_SIZE 512U
#define PHOTON_LIST_SIZE 32U

struct photon_i2c_msg {
	uint16_t addr;
	uint16_t flags;
	uint16_t len;
	uint8_t *buf;
};

struct photon_i2c_rdwr_ioctl_data {
	struct photon_i2c_msg *msgs;
	uint32_t nmsgs;
};

static const uint8_t photon_registers[PHOTON_REGISTER_COUNT] = {
	0x05U, 0x06U, 0x47U
};

static const uint8_t photon_reference[PHOTON_TRANSACTION_COUNT] = {
	0xd9U, 0xd0U, 0xc0U, 0xd9U, 0xd0U, 0xc0U
};

static const uint8_t photon_prefills[PHOTON_TRANSACTION_COUNT] = {
	0xa1U, 0xb2U, 0xc3U, 0xd4U, 0xe5U, 0xf6U
};

static bool emit_marker(int kmsg_fd, const char *format, ...)
{
	char line[PHOTON_LINE_SIZE];
	va_list arguments;
	int length;

	va_start(arguments, format);
	length = vsnprintf(line, sizeof(line), format, arguments);
	va_end(arguments);
	if (length < 0 || (size_t)length >= sizeof(line))
		return false;

	if (kmsg_fd < 0)
		return false;
	if (dprintf(kmsg_fd, "<6>%s\n", line) != length + 4)
		return false;
	if (printf("%s\n", line) >= 0)
		(void)fflush(stdout);
	return true;
}

static void emit_stdout(const char *format, ...)
{
	va_list arguments;

	va_start(arguments, format);
	(void)vprintf(format, arguments);
	va_end(arguments);
	(void)putchar('\n');
	(void)fflush(stdout);
}

static bool has_exact_suffix(const char *value, const char *suffix)
{
	size_t value_length = strlen(value);
	size_t suffix_length = strlen(suffix);

	return value_length >= suffix_length &&
	       memcmp(value + value_length - suffix_length,
		      suffix, suffix_length) == 0;
}

static bool valid_adapter_name(const char *name)
{
	const unsigned char *cursor;

	if (strncmp(name, "i2c-", 4U) != 0 || name[4] == '\0')
		return false;
	for (cursor = (const unsigned char *)name + 4U; *cursor != '\0'; cursor++) {
		if (!isdigit(*cursor))
			return false;
	}
	return true;
}

static int find_i2c6(char *adapter_name, size_t adapter_name_size,
		     char *device_path, size_t device_path_size)
{
	DIR *directory;
	struct dirent *entry;
	unsigned int matches = 0U;
	int result = -1;

	directory = opendir(PHOTON_I2C_CLASS);
	if (directory == NULL)
		return -1;

	for (;;) {
		char link_path[PHOTON_PATH_SIZE];
		char target[PHOTON_PATH_SIZE];
		ssize_t target_length;
		int length;

		errno = 0;
		entry = readdir(directory);
		if (entry == NULL) {
			result = errno == 0 && matches == 1U ? 0 : -1;
			break;
		}
		if (!valid_adapter_name(entry->d_name))
			continue;
		length = snprintf(link_path, sizeof(link_path),
				  PHOTON_I2C_CLASS "/%s/device/of_node",
				  entry->d_name);
		if (length < 0 || (size_t)length >= sizeof(link_path)) {
			result = -1;
			goto out;
		}
		target_length = readlink(link_path, target, sizeof(target) - 1U);
		if (target_length < 0)
			continue;
		target[(size_t)target_length] = '\0';
		if (!has_exact_suffix(target, PHOTON_I2C_OF_SUFFIX))
			continue;

		matches++;
		if (matches != 1U)
			continue;
		length = snprintf(adapter_name, adapter_name_size, "%s",
				  entry->d_name);
		if (length < 0 || (size_t)length >= adapter_name_size) {
			result = -1;
			goto out;
		}
		length = snprintf(device_path, device_path_size, "/dev/%s",
				  entry->d_name);
		if (length < 0 || (size_t)length >= device_path_size) {
			result = -1;
			goto out;
		}
	}

out:
	if (closedir(directory) != 0)
		return -1;
	return result;
}

static int read_one_register(int descriptor, uint8_t reg, uint8_t *value)
{
	uint8_t pointer = reg;
	struct photon_i2c_msg messages[PHOTON_MESSAGE_COUNT] = {
		{
			.addr = PHOTON_I2C_ADDR,
			.flags = 0U,
			.len = 1U,
			.buf = &pointer,
		},
		{
			.addr = PHOTON_I2C_ADDR,
			.flags = PHOTON_I2C_M_RD,
			.len = 1U,
			.buf = value,
		},
	};
	struct photon_i2c_rdwr_ioctl_data request = {
		.msgs = messages,
		.nmsgs = PHOTON_MESSAGE_COUNT,
	};

	return ioctl(descriptor, PHOTON_I2C_RDWR, &request);
}

static bool format_byte_list(char *output, size_t output_size,
			     const uint8_t *values, unsigned int available)
{
	size_t offset = 0U;
	unsigned int index;

	for (index = 0U; index < PHOTON_TRANSACTION_COUNT; index++) {
		const char *separator = index == 0U ? "" : ",";
		int length;

		if (index < available)
			length = snprintf(output + offset, output_size - offset,
					  "%s%02x", separator, values[index]);
		else
			length = snprintf(output + offset, output_size - offset,
					  "%s--", separator);
		if (length < 0 || (size_t)length >= output_size - offset)
			return false;
		offset += (size_t)length;
	}
	return true;
}

static const char *classify_complete_post(const uint8_t *values,
					  unsigned int post_diff_mask)
{
	if (memcmp(values, photon_reference, PHOTON_TRANSACTION_COUNT) == 0)
		return "post-reference-tuple";
	if (values[0] == 0U && values[1] == 0U && values[2] == 0U &&
	    values[3] == 0U && values[4] == 0U && values[5] == 0U)
		return "post-all-zero";
	if (memcmp(values, values + PHOTON_REGISTER_COUNT,
		   PHOTON_REGISTER_COUNT) == 0)
		return "post-pass-tuples-equal-other";
	if (post_diff_mask == 0U)
		return "post-all-equal-pre";
	if (post_diff_mask != (1U << PHOTON_TRANSACTION_COUNT) - 1U)
		return "post-mixed-equal-pre";
	return "post-none-equal-pre-pass-tuples-differ";
}

int main(int argc, char *argv[])
{
	char adapter_name[64];
	char device_path[PHOTON_PATH_SIZE];
	char post_list[PHOTON_LIST_SIZE];
	const char *result_class = "not-run";
	uint8_t values[PHOTON_TRANSACTION_COUNT];
	unsigned int completed = 0U;
	unsigned int post_diff_mask = 0U;
	unsigned int transaction;
	int descriptor = -1;
	int kmsg_fd;
	int saved_errno = 0;
	int ioctl_result = 0;
	int result = 2;

	(void)argv;
	kmsg_fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
	if (argc != 1) {
		emit_stdout("GEMINI_PHOTON_RESULT class=argument-error completed=0");
		if (kmsg_fd >= 0)
			(void)close(kmsg_fd);
		return 2;
	}
	if (kmsg_fd < 0) {
		emit_stdout("GEMINI_PHOTON_RESULT class=kmsg-open-error completed=0");
		return 2;
	}

	if (find_i2c6(adapter_name, sizeof(adapter_name),
		      device_path, sizeof(device_path)) != 0) {
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_PHOTON_RESULT class=adapter-error completed=0 pre=a1,b2,c3,d4,e5,f6 post=--,--,--,--,--,-- post_diff_mask=0x00");
		(void)close(kmsg_fd);
		return 2;
	}

	descriptor = open(device_path, O_RDWR | O_CLOEXEC);
	if (descriptor < 0) {
		saved_errno = errno;
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_PHOTON_RESULT class=open-error errno=%d completed=0 pre=a1,b2,c3,d4,e5,f6 post=--,--,--,--,--,-- post_diff_mask=0x00",
			saved_errno);
		(void)close(kmsg_fd);
		return 2;
	}

	if (!emit_marker(
		    kmsg_fd,
		    "GEMINI_PHOTON_BEGIN adapter=%s of=/i2c@1100e000 address=0x69 transactions=6 registers=05,06,47,05,06,47 prefills=a1,b2,c3,d4,e5,f6",
		    adapter_name)) {
		(void)close(descriptor);
		(void)close(kmsg_fd);
		return 2;
	}

	for (transaction = 0U; transaction < PHOTON_TRANSACTION_COUNT;
	     transaction++) {
		unsigned int index = transaction % PHOTON_REGISTER_COUNT;
		unsigned int pass = transaction / PHOTON_REGISTER_COUNT;
		uint8_t prefill = photon_prefills[transaction];

		values[transaction] = prefill;
		if (!emit_marker(
			    kmsg_fd,
			    "GEMINI_PHOTON_PRE transaction=%u pass=%u register=0x%02x prefill=0x%02x address=0x69 messages=2",
			    transaction + 1U, pass + 1U,
			    photon_registers[index], prefill)) {
			result_class = "pre-marker-error";
			break;
		}

		errno = 0;
		ioctl_result = read_one_register(
			descriptor, photon_registers[index], &values[transaction]);
		if (ioctl_result != (int)PHOTON_MESSAGE_COUNT) {
			saved_errno = ioctl_result < 0 ? errno : 0;
			result_class = "ioctl-result-not-two";
			break;
		}
		completed++;
		if (values[transaction] != prefill)
			post_diff_mask |= 1U << transaction;
		emit_stdout(
			"GEMINI_PHOTON_READ transaction=%u pass=%u register=0x%02x pre=0x%02x post=0x%02x post_differs_pre=%s",
			transaction + 1U, pass + 1U, photon_registers[index],
			prefill, values[transaction],
			values[transaction] == prefill ? "no" : "yes");
	}

	if (completed == PHOTON_TRANSACTION_COUNT) {
		result_class = classify_complete_post(values, post_diff_mask);
		if (strcmp(result_class, "post-reference-tuple") == 0)
			result = 0;
	}
	if (!format_byte_list(post_list, sizeof(post_list), values, completed))
		result_class = "format-error";
	if (!emit_marker(
		    kmsg_fd,
		    "GEMINI_PHOTON_RESULT class=%s completed=%u ioctl_result=%d errno=%d pre=a1,b2,c3,d4,e5,f6 post=%s post_diff_mask=0x%02x page_con_access=none",
		    result_class, completed, ioctl_result, saved_errno, post_list,
		    post_diff_mask)) {
		result = 2;
	}

	(void)close(descriptor);
	(void)close(kmsg_fd);
	return result;
}
