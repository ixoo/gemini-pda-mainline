/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "hif_command.h"

int main(void)
{
	/* Literal expected words independent of the implementation's shifts. */
	static const struct {
		unsigned int port;
		enum mt6797_hif_direction direction;
		enum mt6797_hif_rx_policy policy;
		size_t payload, capacity;
		int error;
		unsigned int word;
		size_t bytes;
	} cases[] = {
		{0x34, 1, 0, 16, 16, 0, 0x90006810, 16},
		{0x34, 1, 1, 20, 20, 0, 0x90006814, 20},
		{0x50, 0, 0, 28, 28, 0, 0x1000a01c, 28},
		{0x50, 0, 1, 28, 32, 0, 0x1000a020, 32},
		{0x54, 0, 0, 1, 4, 0, 0x1000a804, 4},
		{0x54, 0, 1, 1, 8, 0, 0x1000a808, 8},
		{0x50, 0, 0, 505, 508, 0, 0x1000a1fc, 508},
		{0x50, 0, 1, 505, 512, -EMSGSIZE, 0, 0},
		{0x50, 0, 1, 508, 512, -EMSGSIZE, 0, 0},
		{0x34, 1, 0, 509, 512, 0, 0x98006801, 512},
		{0x50, 0, 1, 509, 512, 0, 0x1800a001, 512},
		{0x54, 0, 0, 513, 1024, 0, 0x1800a802, 1024},
		{0x34, 1, 1, 261632, 261632, 0, 0x980069ff, 261632},
		{0x34, 1, 0, 261633, 262144, -EMSGSIZE, 0, 0},
		{0x34, 1, 0, SIZE_MAX, SIZE_MAX, -EMSGSIZE, 0, 0},
		{0x50, 0, 0, 0, 512, -EMSGSIZE, 0, 0},
		{0x50, 0, 1, 28, 28, -EMSGSIZE, 0, 0},
		{0x34, 1, 0, 17, 19, -EMSGSIZE, 0, 0},
		{0x34, 0, 0, 16, 16, -EINVAL, 0, 0},
		{0x50, 1, 0, 16, 16, -EINVAL, 0, 0},
		{0x54, 1, 1, 16, 16, -EINVAL, 0, 0},
		{0x10, 0, 0, 4, 4, -EINVAL, 0, 0},
		{0x1ffff, 0, 0, 4, 4, -EINVAL, 0, 0},
		{0x20034, 1, 0, 16, 16, -EINVAL, 0, 0},
		{0xffffffffU, 1, 0, 16, 16, -EINVAL, 0, 0},
		{0x34, 2, 0, 16, 16, -EINVAL, 0, 0},
		{0x50, -1, 0, 16, 16, -EINVAL, 0, 0},
		{0x50, 0, 2, 16, 16, -EINVAL, 0, 0},
		{0x50, 0, -1, 16, 16, -EINVAL, 0, 0},
	};
	size_t i;
	for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
		struct mt6797_hif_command out = {0xffffffffU, SIZE_MAX};
		assert(mt6797_hif_encode_command(cases[i].port, cases[i].direction,
			cases[i].policy, cases[i].payload, cases[i].capacity, &out) == cases[i].error);
		assert(out.word == cases[i].word);
		assert(out.transfer_bytes == cases[i].bytes);
	}
	assert(mt6797_hif_encode_command(0x34, 1, 0, 16, 16, NULL) == -EINVAL);
	printf("command_cases=%zu null_output_refused=1 result=pass\n", i);
	return 0;
}
