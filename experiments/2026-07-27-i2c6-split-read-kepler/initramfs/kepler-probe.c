// SPDX-License-Identifier: GPL-2.0-only
/*
 * Fixed-function split-read observer for the Gemini PDA's DA9214.
 *
 * This program accepts no arguments. It finds exactly one I2C adapter whose
 * OF path ends in /i2c@1100e000, opens only that adapter, and performs exactly
 * two pairs at address 0x69. Each pair is deliberately split into two
 * independent I2C_RDWR calls: a one-byte pointer write of 0x05 followed by a
 * one-byte read. The STOP between those calls is a deliberate protocol
 * confound. No page, regulator, CPU, storage, watchdog, reboot, or other
 * hardware-control operation is reachable.
 */

#define _POSIX_C_SOURCE 200809L

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define KEPLER_I2C_CLASS "/sys/class/i2c-dev"
#define KEPLER_I2C_OF_SUFFIX "/i2c@1100e000"
#define KEPLER_I2C_ADDR 0x69U
#define KEPLER_I2C_RDWR 0x0707UL
#define KEPLER_I2C_M_RD 0x0001U
#define KEPLER_REGISTER 0x05U
#define KEPLER_PAIR_COUNT 2U
#define KEPLER_PATH_SIZE 512U

struct kepler_i2c_msg {
	uint16_t addr;
	uint16_t flags;
	uint16_t len;
	uint8_t *buf;
};

struct kepler_i2c_rdwr_ioctl_data {
	struct kepler_i2c_msg *msgs;
	uint32_t nmsgs;
};

struct kepler_observation {
	uint8_t post[KEPLER_PAIR_COUNT];
	unsigned int completed_pairs;
	unsigned int completed_calls;
	unsigned int post_diff_mask;
	int ioctl_result;
	int saved_errno;
	const char *result_class;
};

static const uint8_t kepler_prefills[KEPLER_PAIR_COUNT] = {
	0xa5U, 0x5aU
};

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

	directory = opendir(KEPLER_I2C_CLASS);
	if (directory == NULL)
		return -1;

	for (;;) {
		char link_path[KEPLER_PATH_SIZE];
		char target[KEPLER_PATH_SIZE];
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
				  KEPLER_I2C_CLASS "/%s/device/of_node",
				  entry->d_name);
		if (length < 0 || (size_t)length >= sizeof(link_path)) {
			result = -1;
			goto out;
		}
		target_length = readlink(link_path, target, sizeof(target) - 1U);
		if (target_length < 0)
			continue;
		target[(size_t)target_length] = '\0';
		if (!has_exact_suffix(target, KEPLER_I2C_OF_SUFFIX))
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

static int one_message_ioctl(int descriptor, uint16_t flags, uint8_t *byte)
{
	struct kepler_i2c_msg message = {
		.addr = KEPLER_I2C_ADDR,
		.flags = flags,
		.len = 1U,
		.buf = byte,
	};
	struct kepler_i2c_rdwr_ioctl_data request = {
		.msgs = &message,
		.nmsgs = 1U,
	};

	return ioctl(descriptor, KEPLER_I2C_RDWR, &request);
}

static const char *classify_complete(const struct kepler_observation *observation)
{
	if (observation->post_diff_mask == 0U)
		return "split-all-equal-pre";
	if (observation->post_diff_mask != 0x03U)
		return "split-mixed-equal-pre";
	if (observation->post[0] == observation->post[1]) {
		if (observation->post[0] == 0xd9U)
			return "split-stable-d9";
		return "split-stable-other";
	}
	return "split-unstable";
}

static int run_split_pairs(int descriptor, struct kepler_observation *observation)
{
	unsigned int pair;

	memset(observation, 0, sizeof(*observation));
	observation->ioctl_result = 1;
	observation->result_class = "split-incomplete";
	for (pair = 0U; pair < KEPLER_PAIR_COUNT; pair++) {
		uint8_t pointer = KEPLER_REGISTER;
		uint8_t value = kepler_prefills[pair];

		errno = 0;
		observation->ioctl_result =
			one_message_ioctl(descriptor, 0U, &pointer);
		observation->saved_errno = errno;
		printf("GEMINI_KEPLER_TX pair=%u call=%u address=0x69 "
		       "flags=0x0000 len=1 pointer=0x05 result=%d errno=%d\n",
		       pair + 1U, pair * 2U + 1U, observation->ioctl_result,
		       observation->saved_errno);
		(void)fflush(stdout);
		if (observation->ioctl_result != 1) {
			observation->result_class = "tx-result-not-one";
			break;
		}
		observation->completed_calls++;

		errno = 0;
		observation->ioctl_result =
			one_message_ioctl(descriptor, KEPLER_I2C_M_RD, &value);
		observation->saved_errno = errno;
		observation->post[pair] = value;
		if (value != kepler_prefills[pair])
			observation->post_diff_mask |= 1U << pair;
		printf("GEMINI_KEPLER_RX pair=%u call=%u address=0x69 "
		       "flags=0x0001 len=1 pre=0x%02x post=0x%02x "
		       "result=%d errno=%d post_differs_pre=%s\n",
		       pair + 1U, pair * 2U + 2U, kepler_prefills[pair],
		       value, observation->ioctl_result,
		       observation->saved_errno,
		       value == kepler_prefills[pair] ? "no" : "yes");
		(void)fflush(stdout);
		if (observation->ioctl_result != 1) {
			observation->result_class = "rx-result-not-one";
			break;
		}
		observation->completed_calls++;
		observation->completed_pairs++;
	}
	if (observation->completed_pairs == KEPLER_PAIR_COUNT)
		observation->result_class = classify_complete(observation);
	return strcmp(observation->result_class, "split-stable-d9") == 0 ? 0 : 2;
}

static void emit_result(const struct kepler_observation *observation)
{
	printf("GEMINI_KEPLER_RESULT class=%s completed_pairs=%u "
	       "completed_calls=%u ioctl_result=%d errno=%d pre=a5,5a "
	       "post=%02x,%02x post_diff_mask=0x%02x "
	       "stop_between_pointer_and_read=yes page_con_access=none\n",
	       observation->result_class, observation->completed_pairs,
	       observation->completed_calls, observation->ioctl_result,
	       observation->saved_errno, observation->post[0],
	       observation->post[1], observation->post_diff_mask);
	(void)fflush(stdout);
}

int main(int argc, char **argv)
{
	char adapter_name[32];
	char device_path[KEPLER_PATH_SIZE];
	struct kepler_observation observation;
	int descriptor;
	int result;

	(void)argv;
	if (argc != 1)
		return 2;
	if (find_i2c6(adapter_name, sizeof(adapter_name),
		      device_path, sizeof(device_path)) != 0)
		return 2;
	descriptor = open(device_path, O_RDWR | O_CLOEXEC);
	if (descriptor < 0)
		return 2;

	printf("GEMINI_KEPLER_BEGIN adapter=%s of=/i2c@1100e000 "
	       "address=0x69 register=0x05 pairs=2 calls=4 layout=split\n",
	       adapter_name);
	(void)fflush(stdout);
	result = run_split_pairs(descriptor, &observation);
	emit_result(&observation);
	if (close(descriptor) != 0)
		return 2;
	return result;
}
