// SPDX-License-Identifier: GPL-2.0-only
/* Offline contract harness for Kepler's four I2C_RDWR calls. */

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned int harness_call;
static int harness_fail_call;
static uint8_t harness_posts[2];

static int harness_ioctl(int descriptor, unsigned long request, ...)
{
	struct harness_msg {
		uint16_t addr;
		uint16_t flags;
		uint16_t len;
		uint8_t *buf;
	};
	struct harness_rdwr {
		struct harness_msg *msgs;
		uint32_t nmsgs;
	};
	struct harness_rdwr *data;
	va_list arguments;
	unsigned int expected_read;
	unsigned int pair;

	if (descriptor != 73 || request != 0x0707UL)
		abort();
	va_start(arguments, request);
	data = va_arg(arguments, struct harness_rdwr *);
	va_end(arguments);
	harness_call++;
	if (data == NULL || data->nmsgs != 1U || data->msgs == NULL)
		abort();
	if (data->msgs[0].addr != 0x69U || data->msgs[0].len != 1U ||
	    data->msgs[0].buf == NULL)
		abort();
	expected_read = harness_call % 2U == 0U;
	if (data->msgs[0].flags != (expected_read ? 0x0001U : 0U))
		abort();
	pair = (harness_call - 1U) / 2U;
	if (!expected_read && data->msgs[0].buf[0] != 0x05U)
		abort();
	if (expected_read) {
		uint8_t prefill = pair == 0U ? 0xa5U : 0x5aU;

		if (data->msgs[0].buf[0] != prefill)
			abort();
		data->msgs[0].buf[0] = harness_posts[pair];
	}
	if ((int)harness_call == harness_fail_call) {
		errno = EIO;
		return -1;
	}
	return 1;
}

#define ioctl harness_ioctl
#define main kepler_unused_main
#include "../initramfs/kepler-probe.c"
#undef main
#undef ioctl

static void run_case(const char *name, uint8_t post0, uint8_t post1,
		     int fail_call, const char *wanted_class, int wanted_rc,
		     unsigned int wanted_calls, unsigned int wanted_pairs)
{
	struct kepler_observation observation;
	int result;

	harness_call = 0U;
	harness_fail_call = fail_call;
	harness_posts[0] = post0;
	harness_posts[1] = post1;
	result = run_split_pairs(73, &observation);
	if (result != wanted_rc || strcmp(observation.result_class, wanted_class) != 0 ||
	    harness_call != wanted_calls ||
	    observation.completed_pairs != wanted_pairs)
		abort();
	printf("HARNESS_PASS case=%s class=%s rc=%d calls=%u pairs=%u\n",
	       name, observation.result_class, result, harness_call,
	       observation.completed_pairs);
}

int main(void)
{
	run_case("all-equal-pre", 0xa5U, 0x5aU, 0,
		 "split-all-equal-pre", 2, 4U, 2U);
	run_case("mixed", 0xa5U, 0xd9U, 0,
		 "split-mixed-equal-pre", 2, 4U, 2U);
	run_case("stable-d9", 0xd9U, 0xd9U, 0,
		 "split-stable-d9", 0, 4U, 2U);
	run_case("stable-other", 0x33U, 0x33U, 0,
		 "split-stable-other", 2, 4U, 2U);
	run_case("unstable", 0x11U, 0x22U, 0,
		 "split-unstable", 2, 4U, 2U);
	run_case("tx-first", 0xd9U, 0xd9U, 1,
		 "tx-result-not-one", 2, 1U, 0U);
	run_case("rx-first", 0xd9U, 0xd9U, 2,
		 "rx-result-not-one", 2, 2U, 0U);
	run_case("tx-second", 0xd9U, 0xd9U, 3,
		 "tx-result-not-one", 2, 3U, 1U);
	run_case("rx-second", 0xd9U, 0xd9U, 4,
		 "rx-result-not-one", 2, 4U, 1U);
	printf("validation=kepler-offline-ioctl-contract\n");
	printf("successful_path_ioctl_calls=4\n");
	printf("each_ioctl_nmsgs=1\n");
	printf("order=tx05,rx-a5,tx05,rx-5a\n");
	return 0;
}
