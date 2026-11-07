// SPDX-License-Identifier: MIT
/*
 * Measure the clock of one CPU. A chain of dependent integer adds retires one
 * add per cycle on a Cortex-A53, so adds per microsecond is the clock in MHz.
 * Time comes from the architected timer (CLOCK_MONOTONIC_RAW), which does not
 * follow the CPU clock. Prints the best of RUNS samples of about 20 ms each.
 *
 * With "hash", it instead fills 32 MiB from a fixed seed and hashes it four
 * times on that CPU. The result never depends on the CPU or its clock, so any
 * difference from another run is a fault.
 *
 * Build: aarch64-linux-gnu-gcc -O2 -static -o cpu-mhz cpu-mhz.c
 * Usage: cpu-mhz CPU [RUNS]
 *        cpu-mhz CPU hash
 */
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define ADDS_PER_LOOP 64

static double now_ns(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
	return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static void chain(unsigned long loops)
{
	unsigned long x = 0;

	asm volatile(
		"1:\n"
		".rept 64\n"
		"add %[x], %[x], #1\n"
		".endr\n"
		"subs %[n], %[n], #1\n"
		"b.ne 1b\n"
		: [x] "+r" (x), [n] "+r" (loops) : : "cc");
}

static int hash(void)
{
	const size_t words = (32u << 20) / sizeof(uint64_t);
	uint64_t *buf = malloc(words * sizeof(*buf));
	uint64_t x = 0x9e3779b97f4a7c15ull, h = 0xcbf29ce484222325ull;
	double t = now_ns();
	size_t i;
	int pass;

	if (!buf) {
		perror("malloc");
		return 1;
	}
	for (i = 0; i < words; i++) {
		x ^= x << 13;
		x ^= x >> 7;
		x ^= x << 17;
		buf[i] = x;
	}
	for (pass = 0; pass < 4; pass++)
		for (i = 0; i < words; i++)
			h = (h ^ buf[i]) * 0x100000001b3ull;
	printf("hash %016llx ms %.0f\n", (unsigned long long)h,
	       (now_ns() - t) / 1e6);
	free(buf);
	return 0;
}

int main(int argc, char **argv)
{
	unsigned long loops = 20000;
	double best = 0;
	cpu_set_t set;
	int cpu, runs, i;

	if (argc < 2) {
		fprintf(stderr, "usage: %s CPU [RUNS]\n", argv[0]);
		return 2;
	}
	cpu = atoi(argv[1]);
	runs = argc > 2 ? atoi(argv[2]) : 5;
	if (runs < 1)
		runs = 5;
	CPU_ZERO(&set);
	CPU_SET(cpu, &set);
	if (sched_setaffinity(0, sizeof(set), &set)) {
		perror("sched_setaffinity");
		return 1;
	}

	if (argc > 2 && !strcmp(argv[2], "hash"))
		return hash();

	chain(loops);
	for (i = 0; i < runs; i++) {
		double t = now_ns();
		double mhz;

		chain(loops);
		t = now_ns() - t;
		mhz = loops * (double)ADDS_PER_LOOP / t * 1e3;
		if (mhz > best)
			best = mhz;
		/* Aim each sample at about 20 ms. */
		loops = (unsigned long)(loops * 20e6 / t) + 1;
	}

	printf("cpu %d mhz %.0f\n", cpu, best);
	return 0;
}
