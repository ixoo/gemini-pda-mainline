/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual HIF and existing transport mock; no FIFO-pop model is asserted. */
#include <stdint.h>
typedef uint16_t u16;
#define main baseline_main
#include "../../2026-10-01-mt6797-pio-rx/tests/test-pio-rx.c"
#undef main

static unsigned int trial(bool runtime, unsigned int port, unsigned int length,
			  size_t capacity, unsigned int delta, unsigned int fail)
{
	struct mt6797_init_transaction t = { .phase = MT6797_INIT_IDLE,
		.free_pages = 104, .start_free_pages = 104 };
	struct mt6797_hif_rx_result r;
	struct mt6797_hif_command command;
	struct mt6797_hif *h;
	u8 out[2352];
	bool no_post = false;
	unsigned int calls;
	int rc;

#ifdef RUNTIME_CHILD
	no_post = runtime;
#endif
	memset(&mock, 0, sizeof(mock));
	mock.base = calloc(1, 0x1004);
	assert(mock.base);
	mock.now = 1000;
	mock.port = port;
	mock.logical = length;
	mock.header_delta = delta;
	mock.fail_at = fail;
	mock.post = 0x12340056; /* Must survive unchanged for boot callers. */
	mock.copy_allowed = length >= 4 && length <= 2352 && capacity >= length;
	if (mock.copy_allowed) {
		assert(!mt6797_hif_encode_command(port ? 0x54 : 0x50,
			MT6797_HIF_READ, MT6797_HIF_PIO_ONLY, length + 4, 2560, &command));
		mock.words = command.transfer_bytes / 4;
	}
	h = mt6797_hif_alloc(mock.base, 0x1004, &t);
	assert(!IS_ERR(h));
	h->firmware_ready = true;
	h->capability_complete = true;
	h->normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	memset(out, 0xa5, sizeof(out));
#ifdef RUNTIME_CHILD
	if (runtime)
		rc = mt6797_hif_receive_runtime_packet(h, port, 1000001000ULL,
						     out, capacity, &r);
	else
#endif
		rc = mt6797_hif_receive_packet(h, port, 1000001000ULL, out, capacity, &r);
	if (fail) {
		assert(rc == -EIO && mock.calls == fail);
	} else if (!length) {
		assert(rc == -EAGAIN && mock.calls == 2);
	} else if (length < 4 || length > 2352 || delta) {
		assert(rc == -EPROTO && mock.calls == (delta ? mock.words + 3 : 2));
	} else if (capacity < length) {
		assert(rc == -ENOSPC && mock.calls == 2);
	} else {
		assert(!rc && mock.calls == mock.words + (no_post ? 3 : 5));
		assert(r.pre_valid && r.rx_setup && r.rx_complete);
		assert(r.staging_bytes == mock.words * 4 && r.logical_bytes == length);
		assert(r.packet_type == 0xe000 && !r.refused_type_valid);
		assert(r.post_valid == !no_post);
		assert(r.post_wrplr == (no_post ? 0 : mock.post));
		for (unsigned int i = 0; i < length; i++)
			assert(out[i] == ((word_at(i / 4) >> ((i % 4) * 8)) & 255));
	}
	if (rc) {
		assert(!r.logical_bytes && !r.packet_type && !r.post_valid);
		for (unsigned int i = 0; i < sizeof(out); i++)
			assert(out[i] == 0xa5);
	}
	if (rc == -EPROTO && delta) {
		assert(r.header_valid && r.header_length == length + delta);
		assert(r.refused_type_valid && r.refused_type_word == 0xe000);
	}
	if (rc == -EIO || rc == -EPROTO) {
		struct mt6797_hif_rx_result again;
		unsigned int before = mock.calls;

		assert(h->first_error == rc && t.phase == MT6797_INIT_POISONED);
		assert(h->normal.phase == MT6797_NORMAL_FAILED);
#ifdef RUNTIME_CHILD
		if (runtime)
			assert(mt6797_hif_receive_runtime_packet(h, port, 1000001000ULL,
				out, capacity, &again) == -EIO);
		else
#endif
			assert(mt6797_hif_receive_packet(h, port, 1000001000ULL,
				out, capacity, &again) == -EIO);
		assert(mock.calls == before && !again.pre_valid && !again.refused_type_valid);
	} else {
		assert(t.phase == MT6797_INIT_IDLE && !h->first_error);
	}
	printf("%u %u %u %zu %u %u %d %u %u %u %u %u %u %u\n",
	       runtime, port, length, capacity, delta, fail, rc, mock.calls,
	       r.pre_valid, r.rx_setup, r.rx_complete, r.post_valid,
	       r.refused_type_valid, r.logical_bytes != 0);
	calls = mock.calls;
	mt6797_hif_free(h);
	free(mock.base);
	return calls;
}

int main(void)
{
	baseline_main(); /* Boot API: original success/negative/every-I/O-fault tests. */
	for (unsigned int mode = 0; mode < 2; mode++) {
		for (unsigned int port = 0; port < 2; port++) {
			const unsigned int lengths[] = { 4, 76, 80, 449, 2352 };

			trial(mode, port, 0, 2352, 0, 0);
			trial(mode, port, 1, 2352, 0, 0);
			trial(mode, port, 2353, 2352, 0, 0);
			trial(mode, port, 80, 79, 0, 0);
			for (unsigned int i = 0; i < sizeof(lengths) / sizeof(lengths[0]); i++) {
				unsigned int n = trial(mode, port, lengths[i], 2352, 0, 0);

				for (unsigned int f = 1; f <= n; f++)
					trial(mode, port, lengths[i], 2352, 0, f);
			}
			trial(mode, port, 76, 2352, (unsigned int)-48, 0);
			trial(mode, port, 80, 2352, (unsigned int)-48, 0);
			trial(mode, port, 449, 2352, (unsigned int)-48, 0);
		}
	}
	return 0;
}
