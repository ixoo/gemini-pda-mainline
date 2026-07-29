// SPDX-License-Identifier: GPL-2.0-only
/*
 * Fixed-function i2c-dev API-path observer for the Gemini PDA's DA9214.
 *
 * This program accepts no arguments. It finds exactly one I2C adapter whose
 * OF path ends in /i2c@1100e000, selects only address 0x69 once with
 * I2C_SLAVE, and then issues exactly write(06), read(1), write(47), read(1).
 * The writes contain pointer bytes only. No retry, delay, scan, register-data,
 * storage, watchdog, reboot, CPU, regulator, or raw-memory path is reachable.
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

#define MARINER_I2C_CLASS "/sys/class/i2c-dev"
#define MARINER_I2C_OF_SUFFIX "/i2c@1100e000"
#define MARINER_I2C_ADDR 0x69U
#define MARINER_I2C_SLAVE 0x0703UL
#define MARINER_PAIR_COUNT 2U
#define MARINER_PATH_SIZE 512U

struct mariner_observation {
	uint8_t post[MARINER_PAIR_COUNT];
	unsigned int completed_pairs;
	unsigned int completed_bus_calls;
	unsigned int post_diff_user_mask;
	int select_result;
	ssize_t transfer_result;
	int saved_errno;
	const char *result_class;
	const char *error_stage;
};

static const uint8_t mariner_user_prefills[MARINER_PAIR_COUNT] = {
	0x3cU, 0xa6U
};

static const uint8_t mariner_registers[MARINER_PAIR_COUNT] = {
	0x06U, 0x47U
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

	directory = opendir(MARINER_I2C_CLASS);
	if (directory == NULL)
		return -1;

	for (;;) {
		char link_path[MARINER_PATH_SIZE];
		char target[MARINER_PATH_SIZE];
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
				  MARINER_I2C_CLASS "/%s/device/of_node",
				  entry->d_name);
		if (length < 0 || (size_t)length >= sizeof(link_path)) {
			result = -1;
			goto out;
		}
		target_length = readlink(link_path, target, sizeof(target) - 1U);
		if (target_length < 0)
			continue;
		target[(size_t)target_length] = '\0';
		if (!has_exact_suffix(target, MARINER_I2C_OF_SUFFIX))
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

static const char *classify_complete(const struct mariner_observation *observation)
{
	if (observation->post[0] == 0xd0U &&
	    observation->post[1] == 0xc0U)
		return "raw-expected-live";
	if (observation->post[0] == 0x06U &&
	    observation->post[1] == 0x47U)
		return "raw-pointer-echo";
	if (observation->post[0] == 0x47U &&
	    observation->post[1] == 0x06U)
		return "raw-lag";
	if (observation->post[0] == 0x00U &&
	    observation->post[1] == 0x00U)
		return "raw-zero";
	return "raw-other";
}

static int run_api_path(int descriptor, struct mariner_observation *observation)
{
	unsigned int pair;

	memset(observation, 0, sizeof(*observation));
	observation->select_result = -1;
	observation->transfer_result = -1;
	observation->result_class = "raw-error";
	observation->error_stage = "select";

	errno = 0;
	observation->select_result =
		ioctl(descriptor, MARINER_I2C_SLAVE,
		      (unsigned long)MARINER_I2C_ADDR);
	observation->saved_errno = errno;
	printf("GEMINI_MARINER_SELECT call=1 request=I2C_SLAVE "
	       "address=0x69 result=%d errno=%d\n",
	       observation->select_result, observation->saved_errno);
	(void)fflush(stdout);
	if (observation->select_result != 0)
		return 3;

	for (pair = 0U; pair < MARINER_PAIR_COUNT; pair++) {
		uint8_t pointer = mariner_registers[pair];
		uint8_t value = mariner_user_prefills[pair];

		observation->error_stage = pair == 0U ? "write06" : "write47";
		errno = 0;
		observation->transfer_result = write(descriptor, &pointer, 1U);
		observation->saved_errno = errno;
		printf("GEMINI_MARINER_WRITE pair=%u bus_call=%u address=0x69 "
		       "len=1 pointer=0x%02x result=%zd errno=%d\n",
		       pair + 1U, pair * 2U + 1U, pointer,
		       observation->transfer_result, observation->saved_errno);
		(void)fflush(stdout);
		if (observation->transfer_result != 1)
			return 3;
		observation->completed_bus_calls++;

		observation->error_stage = pair == 0U ? "read06" : "read47";
		errno = 0;
		observation->transfer_result = read(descriptor, &value, 1U);
		observation->saved_errno = errno;
		observation->post[pair] = value;
		if (value != mariner_user_prefills[pair])
			observation->post_diff_user_mask |= 1U << pair;
		printf("GEMINI_MARINER_READ pair=%u bus_call=%u address=0x69 "
		       "len=1 user_pre=0x%02x post=0x%02x result=%zd errno=%d "
		       "post_differs_user_pre=%s\n",
		       pair + 1U, pair * 2U + 2U,
		       mariner_user_prefills[pair], value,
		       observation->transfer_result, observation->saved_errno,
		       value == mariner_user_prefills[pair] ? "no" : "yes");
		(void)fflush(stdout);
		if (observation->transfer_result != 1)
			return 3;
		observation->completed_bus_calls++;
		observation->completed_pairs++;
	}

	observation->result_class = classify_complete(observation);
	observation->error_stage = "none";
	return strcmp(observation->result_class, "raw-expected-live") == 0 ? 0 : 2;
}

static void emit_result(const struct mariner_observation *observation)
{
	printf("GEMINI_MARINER_RESULT class=%s error_stage=%s "
	       "completed_pairs=%u completed_bus_calls=%u select_result=%d "
	       "transfer_result=%zd errno=%d user_pre=3c,a6 post=%02x,%02x "
	       "post_diff_user_mask=0x%02x api=write-read page_con_access=none\n",
	       observation->result_class, observation->error_stage,
	       observation->completed_pairs, observation->completed_bus_calls,
	       observation->select_result, observation->transfer_result,
	       observation->saved_errno, observation->post[0],
	       observation->post[1], observation->post_diff_user_mask);
	(void)fflush(stdout);
}

int main(int argc, char **argv)
{
	char adapter_name[32];
	char device_path[MARINER_PATH_SIZE];
	struct mariner_observation observation;
	int descriptor;
	int result;

	(void)argv;
	if (argc != 1)
		return 3;
	if (find_i2c6(adapter_name, sizeof(adapter_name),
		      device_path, sizeof(device_path)) != 0)
		return 3;
	descriptor = open(device_path, O_RDWR | O_CLOEXEC);
	if (descriptor < 0)
		return 3;

	printf("GEMINI_MARINER_BEGIN adapter=%s of=/i2c@1100e000 "
	       "address=0x69 registers=06,47 selection_ioctls=1 "
	       "bus_syscalls=4 api=write-read\n",
	       adapter_name);
	(void)fflush(stdout);
	result = run_api_path(descriptor, &observation);
	if (close(descriptor) != 0) {
		observation.result_class = "raw-error";
		observation.error_stage = "close";
		observation.transfer_result = -1;
		observation.saved_errno = errno;
		result = 3;
	}
	emit_result(&observation);
	return result;
}
