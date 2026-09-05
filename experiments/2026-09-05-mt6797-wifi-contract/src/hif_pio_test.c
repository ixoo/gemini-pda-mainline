/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "hif_pio.h"

struct mock {
	unsigned int offsets[260], values[260];
	char operations[260];
	size_t calls, fail;
};
static int record(struct mock *m, char operation, unsigned int offset, unsigned int value)
{
	assert(m->calls < 260);
	m->operations[m->calls] = operation;
	m->offsets[m->calls] = offset;
	m->values[m->calls++] = value;
	return m->calls == m->fail ? -1 : 0;
}
static int write_io(void *context, unsigned int offset, unsigned int value)
{
	return record(context, 'w', offset, value);
}
static int read_io(void *context, unsigned int offset, unsigned int *value)
{
	*value = 0x87654321;
	return record(context, 'r', offset, *value);
}
int main(void)
{
	struct mock m = {0};
	struct mt6797_hif_pio_io io = {&m, write_io, read_io};
	struct mt6797_hif_pio_result result;
	unsigned char storage[1030], original[1030];
	unsigned char *unaligned = storage + 1;
	size_t i, fail;
	memset(storage, 0xa5, sizeof(storage));
	unaligned[0] = 0x11; unaligned[1] = 0x22; unaligned[2] = 0x33;
	unaligned[3] = 0x44; unaligned[4] = 0x55;
	memcpy(original, storage, sizeof(storage));
	assert(!mt6797_hif_pio_transfer(&io, 0x34, 1, unaligned, 5, 8, &result));
	assert(m.calls == 3 && !memcmp(m.operations, "www", 3));
	assert(m.offsets[0] == 0 && m.values[0] == 0x90006808);
	assert(m.offsets[1] == 0x1000 && m.values[1] == 0x44332211);
	assert(m.offsets[2] == 0x1000 && m.values[2] == 0x55);
	assert(!memcmp(storage, original, sizeof(storage)));
	assert(result.transfer_complete && result.setup_submitted && result.data_bytes == 8);

	m = (struct mock){0};
	assert(!mt6797_hif_pio_transfer(&io, 0x50, 0, unaligned, 5, 8, &result));
	assert(m.calls == 3 && !memcmp(m.operations, "wrr", 3));
	assert(m.values[0] == 0x1000a008 && m.offsets[0] == 0);
	assert(m.offsets[1] == 0x1000 && m.offsets[2] == 0x1000);
	assert(!memcmp(unaligned, "\x21\x43\x65\x87\x21\x43\x65\x87", 8));
	assert(storage[0] == 0xa5 && storage[9] == 0xa5);

	/* Block padding is zero, not stale bytes from the supplied capacity. */
	memset(storage, 0xa5, sizeof(storage)); m = (struct mock){0};
	assert(!mt6797_hif_pio_transfer(&io, 0x34, 1, unaligned, 513, 1024, &result));
	assert(m.calls == 257 && m.values[0] == 0x98006802);
	assert(m.values[129] == 0xa5);
	for (i = 130; i < m.calls; i++) assert(m.values[i] == 0);
	for (i = 1; i < m.calls; i++) assert(m.offsets[i] == 0x1000);

	/* Errors at setup/first/second data operation terminate immediately. */
	for (fail = 1; fail <= 3; fail++) {
		m = (struct mock){.fail = fail};
		memset(storage, 0xa5, sizeof(storage));
		assert(mt6797_hif_pio_transfer(&io, 0x54, 0, unaligned, 8, 8, &result) == -EIO);
		assert(m.calls == fail && !result.transfer_complete);
		assert(result.setup_submitted == (fail > 1));
		assert(result.data_bytes == (fail == 3 ? 4U : 0U));
		assert(unaligned[fail == 3 ? 4 : 0] == 0xa5);
		m = (struct mock){.fail = fail};
		assert(mt6797_hif_pio_transfer(&io, 0x34, 1, unaligned, 8, 8, &result) == -EIO);
		assert(m.calls == fail && !result.transfer_complete);
	}
	/* All invalid requests must refuse before dispatch or buffer mutation. */
	for (i = 0; i < 8; i++) {
		struct mt6797_hif_pio_io bad = io;
		m = (struct mock){0}; memcpy(original, storage, sizeof(storage));
		if (i == 5) bad.write = NULL;
		if (i == 6) bad.read = NULL;
		assert(mt6797_hif_pio_transfer(i == 7 ? NULL : &bad,
			i == 0 ? 0x34 : 0x50, i == 1 ? 2 : 0,
			i == 2 ? NULL : unaligned, i == 3 ? 0 : 8,
			i == 4 ? 7 : 8, &result) < 0);
		assert(!m.calls && !result.setup_submitted && !result.transfer_complete && !result.data_bytes);
		assert(!memcmp(storage, original, sizeof(storage)));
	}
	assert(mt6797_hif_pio_transfer(&io, 0x34, 1, unaligned, 8, 8, NULL) == -EINVAL);
	assert(!m.calls);
	puts("pio_order_endian_padding_refusal_partial_failure_no_retry=pass");
	return 0;
}
