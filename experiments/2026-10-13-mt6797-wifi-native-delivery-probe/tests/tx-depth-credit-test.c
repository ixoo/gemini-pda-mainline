/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#define MT6797_JOIN_TX_DESC_BYTES 28U
#define MT6797_HIF_WRITE 1
#define MT6797_HIF_PIO_ONLY 0
#define MT6797_NORMAL_NVRAM_SUBMITTED 7
#define MT6797_NORMAL_CONFIG_TX 5

/* Only encoder boundaries are stubbed. The actual preparation body below
 * performs every admission check and ledger/phase mutation under test.
 */
struct mt6797_hif_command { size_t transfer_bytes; };
struct mt6797_normal_transaction {
	unsigned int phase, config_return_phase, tc4_limit, tc4_free;
	unsigned int tc1_limit, tc1_free, tc1_pending;
	unsigned char *used_sequences;
};

static int mt6797_normal_abort(struct mt6797_normal_transaction *t)
{
	(void)t;
	assert(!"unexpected abort with a valid fixture ledger");
	return -EIO;
}

static bool mt6797_join_tx_data_descriptor(const unsigned char *frame,
		 size_t bytes, unsigned char wlan, unsigned char pid,
		 unsigned int lifetime, unsigned int attempts,
		 unsigned char *descriptor, unsigned int *pages)
{
	assert(frame && bytes == 342 && wlan == 1 && pid == 9);
	assert(lifetime == 500 && attempts == 3);
	memset(descriptor, 0x5a, MT6797_JOIN_TX_DESC_BYTES);
	*pages = (MT6797_JOIN_TX_DESC_BYTES + bytes + 127) / 128;
	return true;
}

static int mt6797_hif_encode_command(unsigned int address, unsigned int direction,
		 unsigned int mode, size_t bytes, size_t capacity,
		 struct mt6797_hif_command *command)
{
	assert(address == 0x34 && direction == MT6797_HIF_WRITE);
	assert(mode == MT6797_HIF_PIO_ONLY && bytes <= capacity);
	command->transfer_bytes = bytes;
	return 0;
}

#include "prepare-data-source.inc"

static int prepare(struct mt6797_normal_transaction *t)
{
	unsigned char frame[342] = {0}, output[512];
	struct mt6797_hif_command command;

	memset(output, 0xa5, sizeof(output));
	int result = mt6797_join_prepare_data(t, frame, sizeof(frame), 1, 9,
					    500, 3, output, sizeof(output), &command);
	if (result) {
		assert(!command.transfer_bytes && output[0] == 0xa5);
	} else {
		assert(command.transfer_bytes == MT6797_JOIN_TX_DESC_BYTES + sizeof(frame));
		assert(!memcmp(output + MT6797_JOIN_TX_DESC_BYTES, frame, sizeof(frame)));
	}
	return result;
}

int main(void)
{
	unsigned char history[32] = {0};
	struct mt6797_normal_transaction t = {
		.phase = MT6797_NORMAL_NVRAM_SUBMITTED,
		.tc4_limit = 26, .tc4_free = 26,
		.tc1_limit = 16, .tc1_free = 13, .tc1_pending = 1,
		.used_sequences = history,
	}, before = t;

#if CONFIG_MT6797_CCMP_TX_DEPTH == 1
	assert(prepare(&t) == -EBUSY);
	assert(!memcmp(&t, &before, sizeof(t)));
#else
	assert(!prepare(&t));
	assert(t.tc1_free == before.tc1_free - 3);
	before.tc1_free -= 3;
	before.phase = MT6797_NORMAL_CONFIG_TX;
	before.config_return_phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	assert(!memcmp(&t, &before, sizeof(t)));
#endif
	/* Whole but too small: ENOSPC at either depth, with no ledger mutation. */
	t.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	t.tc1_limit = t.tc1_free = 2;
	t.tc1_pending = 0;
	before = t;
	assert(prepare(&t) == -ENOSPC);
	assert(!memcmp(&t, &before, sizeof(t)));
#if CONFIG_MT6797_CCMP_TX_DEPTH > 1
	/* Partially available and too small: the depth-four relaxation still
	 * refuses rather than charging more pages than are currently free.
	 */
	t.tc1_limit = 16;
	t.tc1_pending = 1;
	before = t;
	assert(prepare(&t) == -ENOSPC);
	assert(!memcmp(&t, &before, sizeof(t)));
#endif
	return 0;
}
