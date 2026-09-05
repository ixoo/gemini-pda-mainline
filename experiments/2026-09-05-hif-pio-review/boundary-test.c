/* SPDX-License-Identifier: MIT */
/* Independent callback oracle for the exact project-owned PIO primitive. */
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sanitizer/asan_interface.h>
#include "hif_pio.h"
struct state { size_t calls, span, payload, fail; unsigned int setup; bool rx; };
static unsigned char pattern(size_t i) { return (unsigned char)(i * 37 + i / 7 + 0x81); }
static int write_word(void *context, unsigned int offset, unsigned int value)
{
	struct state *s = context;
	size_t call = s->calls++, first = (call - 1) * 4;
	unsigned int expected = 0;
	if (!call) {
		assert(offset == 0 && value == s->setup);
	} else {
		assert(!s->rx && offset == 0x1000 && first < s->span);
		for (size_t i = 0; i < 4; i++)
			expected += (first + i < s->payload ? (unsigned int)pattern(first + i) : 0U) * (1U << (8 * i));
		assert(value == expected);
	}
	return s->calls == s->fail ? 1 : 0;
}
static int read_word(void *context, unsigned int offset, unsigned int *value)
{
	struct state *s = context;
	assert(s->rx && s->calls && offset == 0x1000);
	size_t first = (s->calls++ - 1) * 4;
	assert(first < s->span);
	*value = (unsigned int)pattern(first) + (unsigned int)pattern(first + 1) * 256U +
		(unsigned int)pattern(first + 2) * 65536U + (unsigned int)pattern(first + 3) * 16777216U;
	return s->calls == s->fail ? 1 : 0;
}
static size_t cases;
static void check(size_t length, bool rx, unsigned int port, int capacity_delta, size_t fail)
{
	/* Independent interval description: 1..508 byte mode; 509+ blocks. */
	size_t span = length <= 508 ? ((length - 1) / 4 + 1) * 4 : ((length - 1) / 512 + 1) * 512;
	size_t capacity = span + capacity_delta;
	struct state s = {.span = span, .payload = length, .fail = fail, .rx = rx};
	s.setup = (rx ? 0U : 0x80000000U) + 0x10000000U + port * 512U +
		(length <= 508 ? (unsigned int)span : 0x08000000U + (unsigned int)(span / 512));
	unsigned char *allocation = malloc(span + 9), *buffer = allocation + 1;
	assert(allocation);
	memset(allocation, 0x6b, span + 9);
	if (!rx) for (size_t i = 0; i < length; i++) buffer[i] = pattern(i);
	/* Poison TX padding so reading and discarding it also fails. */
	if (!rx && span > length) __asan_poison_memory_region(buffer + length, span - length);
	struct mt6797_hif_pio_io io = {&s, write_word, read_word};
	struct mt6797_hif_pio_result result = {123, true, true};
	int error = mt6797_hif_pio_transfer(&io, port, rx ? MT6797_HIF_READ : MT6797_HIF_WRITE,
		buffer, length, capacity, &result);
	bool refused = length > 511U * 512U || capacity_delta < 0;
	assert(error == (refused ? -EMSGSIZE : fail ? -EIO : 0));
	size_t completed = refused || fail == 1 ? 0 : fail ? (fail - 2) * 4 : span;
	assert(s.calls == (refused ? 0 : fail ? fail : 1 + span / 4));
	assert(result.data_bytes == completed && result.setup_submitted == (!refused && fail != 1));
	assert(result.transfer_complete == (!refused && !fail));
	if (!rx && span > length) __asan_unpoison_memory_region(buffer + length, span - length);
	for (size_t i = 0; i < span; i++)
		assert(buffer[i] == (rx ? (i < completed ? pattern(i) : 0x6b) : (i < length ? pattern(i) : 0x6b)));
	assert(allocation[0] == 0x6b);
	for (size_t i = span + 1; i < span + 9; i++) assert(allocation[i] == 0x6b);
	free(allocation); cases++;
}
int main(void)
{
	for (size_t n = 1; n <= 1025; n++)
		for (int delta = -1; delta <= 1; delta++) {
			check(n, false, 0x34, delta, 0);
			check(n, true, 0x50, delta, 0);
			check(n, true, 0x54, delta, 0);
		}
	for (size_t n = 511U * 512U - 3; n <= 511U * 512U + 1; n++)
		for (int delta = -1; delta <= 1; delta++) {
			check(n, false, 0x34, delta, 0);
			check(n, true, 0x50, delta, 0);
			check(n, true, 0x54, delta, 0);
		}
	for (size_t fail = 1; fail <= 257; fail++) {
		check(513, false, 0x34, 0, fail);
		check(513, true, 0x50, 0, fail);
		check(513, true, 0x54, 0, fail);
	}
	printf("independent_pio_boundary_cases=%zu PASS\n", cases);
	return 0;
}
