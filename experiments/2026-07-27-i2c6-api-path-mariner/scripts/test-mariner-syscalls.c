// SPDX-License-Identifier: GPL-2.0-only
/* Offline contract harness for Mariner's select/write/read syscall order. */

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

enum harness_operation {
	HARNESS_SELECT = 1,
	HARNESS_WRITE06,
	HARNESS_READ06,
	HARNESS_WRITE47,
	HARNESS_READ47,
};

static unsigned int harness_operation;
static int harness_fail_operation;
static bool harness_short_result;
static uint8_t harness_posts[2];

static void require_operation(enum harness_operation wanted)
{
	harness_operation++;
	if (harness_operation != (unsigned int)wanted)
		abort();
}

static int harness_ioctl(int descriptor, unsigned long request, ...)
{
	va_list arguments;
	unsigned long address;

	require_operation(HARNESS_SELECT);
	if (descriptor != 73 || request != 0x0703UL)
		abort();
	va_start(arguments, request);
	address = va_arg(arguments, unsigned long);
	va_end(arguments);
	if (address != 0x69UL)
		abort();
	if ((int)harness_operation == harness_fail_operation) {
		errno = EBUSY;
		return -1;
	}
	return 0;
}

static ssize_t harness_write(int descriptor, const void *buffer, size_t count)
{
	enum harness_operation wanted =
		harness_operation == HARNESS_SELECT ?
		HARNESS_WRITE06 : HARNESS_WRITE47;
	uint8_t pointer = wanted == HARNESS_WRITE06 ? 0x06U : 0x47U;

	require_operation(wanted);
	if (descriptor != 73 || buffer == NULL || count != 1U ||
	    *(const uint8_t *)buffer != pointer)
		abort();
	if ((int)harness_operation == harness_fail_operation) {
		if (harness_short_result) {
			errno = 0;
			return 0;
		}
		errno = EIO;
		return -1;
	}
	return 1;
}

static ssize_t harness_read(int descriptor, void *buffer, size_t count)
{
	enum harness_operation wanted =
		harness_operation == HARNESS_WRITE06 ?
		HARNESS_READ06 : HARNESS_READ47;
	unsigned int pair = wanted == HARNESS_READ06 ? 0U : 1U;
	uint8_t prefill = pair == 0U ? 0x3cU : 0xa6U;

	require_operation(wanted);
	if (descriptor != 73 || buffer == NULL || count != 1U ||
	    *(uint8_t *)buffer != prefill)
		abort();
	if ((int)harness_operation == harness_fail_operation) {
		if (harness_short_result) {
			errno = 0;
			return 0;
		}
		errno = EIO;
		return -1;
	}
	*(uint8_t *)buffer = harness_posts[pair];
	return 1;
}

#define ioctl harness_ioctl
#define write harness_write
#define read harness_read
#define main mariner_unused_main
#include "../initramfs/mariner-probe.c"
#undef main
#undef read
#undef write
#undef ioctl

static void run_case_mode(const char *name, uint8_t post0, uint8_t post1,
			  int fail_operation, bool short_result,
			  const char *wanted_class, int wanted_rc,
			  unsigned int wanted_operations,
			  unsigned int wanted_calls,
			  unsigned int wanted_pairs, const char *wanted_stage)
{
	struct mariner_observation observation;
	int result;

	harness_operation = 0U;
	harness_fail_operation = fail_operation;
	harness_short_result = short_result;
	harness_posts[0] = post0;
	harness_posts[1] = post1;
	result = run_api_path(73, &observation);
	if (result != wanted_rc ||
	    strcmp(observation.result_class, wanted_class) != 0 ||
	    strcmp(observation.error_stage, wanted_stage) != 0 ||
	    harness_operation != wanted_operations ||
	    observation.completed_bus_calls != wanted_calls ||
	    observation.completed_pairs != wanted_pairs)
		abort();
	printf("HARNESS_PASS case=%s class=%s stage=%s rc=%d operations=%u "
	       "bus_calls=%u pairs=%u\n",
	       name, observation.result_class, observation.error_stage, result,
	       harness_operation, observation.completed_bus_calls,
	       observation.completed_pairs);
}

static void run_case(const char *name, uint8_t post0, uint8_t post1,
		     int fail_operation, const char *wanted_class, int wanted_rc,
		     unsigned int wanted_operations, unsigned int wanted_calls,
		     unsigned int wanted_pairs, const char *wanted_stage)
{
	run_case_mode(name, post0, post1, fail_operation, false, wanted_class,
		      wanted_rc, wanted_operations, wanted_calls, wanted_pairs,
		      wanted_stage);
}

static void run_short_case(const char *name, int short_operation,
			   unsigned int wanted_operations,
			   unsigned int wanted_calls,
			   unsigned int wanted_pairs, const char *wanted_stage)
{
	run_case_mode(name, 0xd0U, 0xc0U, short_operation, true, "raw-error", 3,
		      wanted_operations, wanted_calls, wanted_pairs,
		      wanted_stage);
}

int main(void)
{
	run_case("expected-live", 0xd0U, 0xc0U, 0,
		 "raw-expected-live", 0, 5U, 4U, 2U, "none");
	run_case("pointer-echo", 0x06U, 0x47U, 0,
		 "raw-pointer-echo", 2, 5U, 4U, 2U, "none");
	run_case("lag", 0x47U, 0x06U, 0,
		 "raw-lag", 2, 5U, 4U, 2U, "none");
	run_case("zero", 0x00U, 0x00U, 0,
		 "raw-zero", 2, 5U, 4U, 2U, "none");
	run_case("other", 0x3cU, 0xa6U, 0,
		 "raw-other", 2, 5U, 4U, 2U, "none");
	run_case("select-error", 0xd0U, 0xc0U, HARNESS_SELECT,
		 "raw-error", 3, 1U, 0U, 0U, "select");
	run_case("write06-error", 0xd0U, 0xc0U, HARNESS_WRITE06,
		 "raw-error", 3, 2U, 0U, 0U, "write06");
	run_case("read06-error", 0xd0U, 0xc0U, HARNESS_READ06,
		 "raw-error", 3, 3U, 1U, 0U, "read06");
	run_case("write47-error", 0xd0U, 0xc0U, HARNESS_WRITE47,
		 "raw-error", 3, 4U, 2U, 1U, "write47");
	run_case("read47-error", 0xd0U, 0xc0U, HARNESS_READ47,
		 "raw-error", 3, 5U, 3U, 1U, "read47");
	run_short_case("write06-short", HARNESS_WRITE06, 2U, 0U, 0U,
		       "write06");
	run_short_case("read06-short", HARNESS_READ06, 3U, 1U, 0U,
		       "read06");
	run_short_case("write47-short", HARNESS_WRITE47, 4U, 2U, 1U,
		       "write47");
	run_short_case("read47-short", HARNESS_READ47, 5U, 3U, 1U,
		       "read47");
	printf("validation=mariner-offline-syscall-contract\n");
	printf("successful_path_operations=select,write06,read06,write47,read47\n");
	printf("selection_ioctls=1\nbus_syscalls=4\n");
	return 0;
}
