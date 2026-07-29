// SPDX-License-Identifier: GPL-2.0-only
/*
 * Fixed-function userspace observer for the Gemini PDA's legacy DA9214.
 *
 * This program accepts no arguments. It finds only MT6797 I2C6 through its
 * exact OF path and issues six combined register-pointer/read transactions:
 * 0x69:{0x05,0x06,0x47}, twice. It cannot select a different bus, address,
 * register, pass count, or operation from userspace.
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

#define CASSINI_I2C_CLASS "/sys/class/i2c-dev"
#define CASSINI_I2C_OF_SUFFIX "/i2c@1100e000"
#define CASSINI_I2C_ADDR 0x69U
#define CASSINI_I2C_RDWR 0x0707UL
#define CASSINI_I2C_M_RD 0x0001U
#define CASSINI_PASSES 2U
#define CASSINI_REGISTER_COUNT 3U
#define CASSINI_MESSAGE_COUNT 2U
#define CASSINI_PATH_SIZE 512U
#define CASSINI_LINE_SIZE 512U

struct cassini_i2c_msg {
	uint16_t addr;
	uint16_t flags;
	uint16_t len;
	uint8_t *buf;
};

struct cassini_i2c_rdwr_ioctl_data {
	struct cassini_i2c_msg *msgs;
	uint32_t nmsgs;
};

static const uint8_t cassini_registers[CASSINI_REGISTER_COUNT] = {
	0x05U, 0x06U, 0x47U
};

static const uint8_t cassini_expected[CASSINI_REGISTER_COUNT] = {
	0xd9U, 0xd0U, 0xc0U
};

static bool emit_marker(int kmsg_fd, const char *format, ...)
{
	char line[CASSINI_LINE_SIZE];
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

	directory = opendir(CASSINI_I2C_CLASS);
	if (directory == NULL)
		return -1;

	for (;;) {
		char link_path[CASSINI_PATH_SIZE];
		char target[CASSINI_PATH_SIZE];
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
				  CASSINI_I2C_CLASS "/%s/device/of_node",
				  entry->d_name);
		if (length < 0 || (size_t)length >= sizeof(link_path)) {
			result = -1;
			goto out;
		}
		target_length = readlink(link_path, target, sizeof(target) - 1U);
		if (target_length < 0)
			continue;
		target[(size_t)target_length] = '\0';
		if (!has_exact_suffix(target, CASSINI_I2C_OF_SUFFIX))
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
	struct cassini_i2c_msg messages[CASSINI_MESSAGE_COUNT] = {
		{
			.addr = CASSINI_I2C_ADDR,
			.flags = 0U,
			.len = 1U,
			.buf = &pointer,
		},
		{
			.addr = CASSINI_I2C_ADDR,
			.flags = CASSINI_I2C_M_RD,
			.len = 1U,
			.buf = value,
		},
	};
	struct cassini_i2c_rdwr_ioctl_data request = {
		.msgs = messages,
		.nmsgs = CASSINI_MESSAGE_COUNT,
	};

	return ioctl(descriptor, CASSINI_I2C_RDWR, &request);
}

int main(int argc, char *argv[])
{
	char adapter_name[64];
	char device_path[CASSINI_PATH_SIZE];
	uint8_t values[CASSINI_PASSES][CASSINI_REGISTER_COUNT] = {{0U}};
	unsigned int transaction = 0U;
	unsigned int pass;
	unsigned int index;
	int transfer_result;
	int descriptor = -1;
	int kmsg_fd;
	int saved_errno;

	(void)argv;
	kmsg_fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
	if (argc != 1) {
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_CASSINI_PROBE_FAIL stage=arguments transactions=0");
		if (kmsg_fd >= 0)
			(void)close(kmsg_fd);
		return 2;
	}
	if (kmsg_fd < 0) {
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_CASSINI_PROBE_FAIL stage=kmsg-open transactions=0");
		return 2;
	}

	if (find_i2c6(adapter_name, sizeof(adapter_name),
		      device_path, sizeof(device_path)) != 0) {
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_CASSINI_PROBE_FAIL stage=adapter transactions=0");
		(void)close(kmsg_fd);
		return 2;
	}

	descriptor = open(device_path, O_RDWR | O_CLOEXEC);
	if (descriptor < 0) {
		saved_errno = errno;
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_CASSINI_PROBE_FAIL stage=open errno=%d transactions=0",
			saved_errno);
		(void)close(kmsg_fd);
		return 2;
	}

	if (!emit_marker(
		    kmsg_fd,
		    "GEMINI_CASSINI_PROBE_BEGIN adapter=%s of=/i2c@1100e000 address=0x69 passes=2 registers=0x05,0x06,0x47",
		    adapter_name)) {
		(void)close(descriptor);
		(void)close(kmsg_fd);
		return 2;
	}
	for (pass = 0U; pass < CASSINI_PASSES; pass++) {
		for (index = 0U; index < CASSINI_REGISTER_COUNT; index++) {
			if (!emit_marker(
				    kmsg_fd,
				    "GEMINI_CASSINI_TRANSACTION_BEGIN pass=%u register=0x%02x transaction=%u address=0x69 messages=2",
				    pass + 1U, cassini_registers[index],
				    transaction + 1U)) {
				(void)close(descriptor);
				(void)close(kmsg_fd);
				return 2;
			}
			errno = 0;
			transfer_result = read_one_register(
				descriptor, cassini_registers[index],
				&values[pass][index]);
			if (transfer_result != (int)CASSINI_MESSAGE_COUNT) {
				saved_errno = transfer_result < 0 ? errno : 0;
				(void)emit_marker(
					kmsg_fd,
					"GEMINI_CASSINI_PROBE_FAIL stage=transfer pass=%u register=0x%02x result=%d errno=%d transactions=%u",
					pass + 1U, cassini_registers[index],
					transfer_result, saved_errno,
					transaction);
				(void)close(descriptor);
				(void)close(kmsg_fd);
				return 2;
			}
			transaction++;
			if (!emit_marker(
				    kmsg_fd,
				    "GEMINI_CASSINI_READ pass=%u register=0x%02x value=0x%02x transaction=%u",
				    pass + 1U, cassini_registers[index],
				    values[pass][index], transaction)) {
				(void)close(descriptor);
				(void)close(kmsg_fd);
				return 2;
			}
		}
	}

	if (close(descriptor) != 0) {
		saved_errno = errno;
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_CASSINI_PROBE_FAIL stage=close errno=%d transactions=6",
			saved_errno);
		(void)close(kmsg_fd);
		return 2;
	}
	if (memcmp(values[0], values[1], CASSINI_REGISTER_COUNT) != 0) {
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_CASSINI_PROBE_FAIL stage=unstable first=%02x,%02x,%02x second=%02x,%02x,%02x transactions=6",
			values[0][0], values[0][1], values[0][2],
			values[1][0], values[1][1], values[1][2]);
		(void)close(kmsg_fd);
		return 2;
	}
	if (memcmp(values[0], cassini_expected, CASSINI_REGISTER_COUNT) != 0) {
		(void)emit_marker(
			kmsg_fd,
			"GEMINI_CASSINI_PROBE_FAIL stage=signature first=%02x,%02x,%02x second=%02x,%02x,%02x transactions=6",
			values[0][0], values[0][1], values[0][2],
			values[1][0], values[1][1], values[1][2]);
		(void)close(kmsg_fd);
		return 2;
	}

	if (!emit_marker(
		    kmsg_fd,
		    "GEMINI_CASSINI_PROBE_PASS first=d9,d0,c0 second=d9,d0,c0 transactions=6 page_con=untouched")) {
		(void)close(kmsg_fd);
		return 2;
	}
	(void)close(kmsg_fd);
	return 0;
}
