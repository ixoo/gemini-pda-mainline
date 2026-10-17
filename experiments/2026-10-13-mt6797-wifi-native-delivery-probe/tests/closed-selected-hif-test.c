/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual HIF; original PIO fixture with an additional mock input halfword. */
#include <stdint.h>
typedef uint16_t u16;
#define main baseline_main
#include "selected-pio-baseline.inc"
#undef main

static unsigned int selected(unsigned int low, unsigned int high, size_t capacity,
			     unsigned int delta, unsigned int fail, bool expired)
{
	struct mt6797_init_transaction t = { .phase = MT6797_INIT_IDLE,
		.free_pages = 104, .start_free_pages = 104 };
	struct mt6797_hif_rx_result r, again;
	struct mt6797_hif_command command;
	struct mt6797_hif *h;
	unsigned int port = low ? 0 : 1, length = low ? low : high, calls;
	u8 out[2352];
	int rc;

	memset(&mock, 0, sizeof(mock));
	mock.base = calloc(1, 0x1004);
	assert(mock.base);
	mock.now = 1000;
	mock.port = port;
	mock.logical = length;
	mock.opposite_length = port ? low : high;
	mock.header_delta = delta;
	mock.fail_at = fail;
	mock.copy_allowed = length >= 4 && length <= 2352 && capacity >= length;
	if (mock.copy_allowed) {
		assert(!mt6797_hif_encode_command(port ? 0x54 : 0x50,
			MT6797_HIF_READ, MT6797_HIF_PIO_ONLY, length + 4, 2560, &command));
		mock.words = command.transfer_bytes / 4;
	}
	h = mt6797_hif_alloc(mock.base, 0x1004, &t);
	assert(!IS_ERR(h));
	h->firmware_ready = h->capability_complete = true;
	h->normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	memset(out, 0xa5, sizeof(out));
	rc = mt6797_hif_receive_selected(h,
			expired ? 1000 : 1000001000ULL, out, capacity, &r);
	if (expired) {
		assert(rc == -ETIMEDOUT && !mock.calls && !r.pre_valid);
	} else if (fail) {
		assert(rc == -EIO && mock.calls == fail);
	} else if (!length) {
		assert(rc == -EAGAIN && mock.calls == 2);
	} else if (length < 4 || length > 2352 || delta) {
		assert(rc == -EPROTO && mock.calls == (delta ? mock.words + 3 : 2));
	} else if (capacity < length) {
		assert(rc == -ENOSPC && mock.calls == 2);
	} else {
		assert(!rc && mock.calls == mock.words + 3);
		assert(r.pre_valid && r.rx_setup && r.rx_complete);
		assert(r.staging_bytes == mock.words * 4 && r.logical_bytes == length);
		assert(r.packet_type == 0xe000 && !r.refused_type_valid);
		for (unsigned int i = 0; i < length; i++)
			assert(out[i] == ((word_at(i / 4) >> ((i % 4) * 8)) & 255));
	}
	if (r.pre_valid) {
		assert(r.pre_wrplr == (low | high << 16));
		assert(r.selected_port_valid == (length != 0));
		assert(r.selected_port == port);
	} else {
		assert(!r.selected_port_valid && !r.selected_port);
	}
	assert(!r.post_valid && !r.post_wrplr);
	if (rc) {
		assert(!r.logical_bytes && !r.packet_type);
		for (unsigned int i = 0; i < sizeof(out); i++)
			assert(out[i] == 0xa5);
	}
	if (rc == -EPROTO && delta) {
		assert(r.header_valid && r.header_length == length + delta);
		assert(r.refused_type_valid && r.refused_type_word == 0xe000);
	}
	calls = mock.calls;
	if (rc != 0 && rc != -EAGAIN && rc != -ENOSPC) {
		assert(h->first_error == rc && t.phase == MT6797_INIT_POISONED);
		assert(h->normal.phase == MT6797_NORMAL_FAILED);
		assert(mt6797_hif_receive_selected(h, 1000001000ULL,
			out, capacity, &again) == -EIO);
		assert(mock.calls == calls && !again.pre_valid && !again.selected_port_valid);
	} else {
		assert(!h->first_error && t.phase == MT6797_INIT_IDLE);
	}
	mt6797_hif_free(h);
	free(mock.base);
	return calls;
}

int main(void)
{
	unsigned int cases = 0;
	const unsigned int lengths[] = { 4, 76, 80, 427, 449, 2352 };
	const unsigned int mismatches[][2] = { {76, 28}, {80, 32}, {449, 401}, {427, 379} };

	baseline_main();
	selected(0, 0, 2352, 0, 0, false);
	selected(80, 0, 2352, 0, 0, true);
	for (unsigned int p = 0; p < 2; p++) {
		selected(p ? 0 : 1, p ? 1 : 0, 2352, 0, 0, false);
		selected(p ? 0 : 2353, p ? 2353 : 0, 2352, 0, 0, false);
		selected(p ? 0 : 80, p ? 80 : 0, 79, 0, 0, false);
		for (unsigned int i = 0; i < sizeof(lengths) / sizeof(lengths[0]); i++) {
			unsigned int len = lengths[i];
			unsigned int n = selected(p ? 0 : len, p ? len : 0, 2352, 0, 0, false);

			for (unsigned int f = 1; f <= n; f++) {
				selected(p ? 0 : len, p ? len : 0, 2352, 0, f, false);
				cases++;
			}
		}
		for (unsigned int i = 0; i < sizeof(mismatches) / sizeof(mismatches[0]); i++) {
			unsigned int len = mismatches[i][0], delta = mismatches[i][1] - len;

			selected(p ? 0 : len, p ? len : 0, 2352, delta, 0, false);
		}
	}
	/* Both advertised: port 0 is selected from the same word. Even an invalid
	 * opposite half is neither interpreted nor silently used for this transfer.
	 */
	selected(76, 449, 2352, 0, 0, false);
	selected(80, 65535, 2352, 0, 0, false);
	selected(1, 80, 2352, 0, 0, false); /* invalid chosen half still poisons */
	printf("selected runtime: both ports, priority, empty, four mismatch pairs, "
	       "capacity, deadline, no-copy/poison; %u injected I/O faults PASS\n", cases);
	return 0;
}
