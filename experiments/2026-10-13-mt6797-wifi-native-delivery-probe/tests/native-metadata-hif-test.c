/* SPDX-License-Identifier: GPL-2.0-only */
/* Reuse the actual-HIF fixture, including its transport and lifetime mocks. */
#ifdef TEST_REFUSED_TYPE
#include <stdint.h>
typedef uint16_t u16;
#endif
#define main baseline_main
#define check baseline_check
#include "../../2026-10-01-mt6797-pio-rx/tests/test-pio-rx.c"
#undef main
#undef check

#ifdef TEST_METADATA
#include <stdarg.h>
static unsigned int log_lines;
static char last_log[1024];
#define wiphy_dev(w) NULL
static void dev_info(void *dev, const char *format, ...) __attribute__((format(printf, 2, 3)));
static void dev_info(void *dev, const char *format, ...)
{
	va_list args;
	(void)dev;
	va_start(args, format);
	assert(vsnprintf(last_log, sizeof(last_log), format, args) > 0);
	va_end(args);
	log_lines++;
	fputs(last_log, stderr);
}
#include "metadata-hif-log.h"
#endif

static unsigned int check(unsigned int port, unsigned int length, unsigned int delta,
		  unsigned int fail_at, int expected)
{
	struct mt6797_init_transaction t = { .phase = MT6797_INIT_IDLE,
		.free_pages = 104, .start_free_pages = 104 };
	struct mt6797_hif_rx_result r;
	struct mt6797_hif_command command;
	struct mt6797_hif *h;
	u8 buffer[2352];
	int rc;

	memset(buffer, 0x5a, sizeof(buffer));
	memset(&mock, 0, sizeof(mock));
	mock.base = calloc(1, 0x1004);
	assert(mock.base);
	mock.now = 1000;
	mock.port = port;
	mock.logical = length;
	mock.header_delta = delta;
	mock.fail_at = fail_at;
	mock.copy_allowed = length >= 4 && length <= 2352;
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
	rc = mt6797_hif_receive_packet(h, port, 1000001000ULL,
				     buffer, sizeof(buffer), &r);
	assert(rc == expected);
	if (rc) {
		for (size_t i = 0; i < sizeof(buffer); i++)
			assert(buffer[i] == 0x5a);
	}
	if (rc == -EPROTO || rc == -EIO) {
		assert(h->first_error == rc);
		assert(t.phase == MT6797_INIT_POISONED);
		assert(h->normal.phase == MT6797_NORMAL_FAILED);
	}
	if (rc == -EPROTO && mock.copy_allowed) {
		/* Header mismatch exits before the post-WRPLR setup/read and before
		 * publishing a packet type or any logical caller bytes.
		 */
		assert(mock.calls == mock.words + 3);
		assert(r.rx_setup && r.rx_complete && r.staging_bytes == mock.words * 4);
		assert(!r.post_valid && !r.post_wrplr && !r.logical_bytes && !r.packet_type);
	}
#ifdef TEST_REFUSED_TYPE
	{
		bool valid = rc == -EPROTO &&
			r.protocol_refusal == MT6797_HIF_RX_REFUSAL_HEADER &&
			r.rx_setup && r.rx_complete && r.header_valid && r.staging_bytes >= 4;

		assert(r.refused_type_valid == valid);
		_Static_assert(sizeof(r.refused_type_word) == 2, "hint must be 16 bits");
		/* The fixture stages this synthetic word, not a runtime type claim. */
		assert(r.refused_type_word == (valid ? 0xe000 : 0));
	}
#endif
#ifdef TEST_METADATA
	log_lines = 0;
	logged_refusal(rc, port, r);
	assert(log_lines == (unsigned int)(rc == -EPROTO));
	if (rc == -EPROTO) {
		assert(r.pre_valid && !r.post_valid && !r.post_wrplr);
		assert(r.selected_length == length);
		assert(r.pre_wrplr == (port ? length << 16 : length));
		if (length < 4 || length > MT6797_HIF_RX_MAX_PACKET) {
			assert(strstr(last_log, "gate=wrplr-length"));
			assert(strstr(last_log, "header_valid=0 header=0"));
			assert(r.protocol_refusal == MT6797_HIF_RX_REFUSAL_LENGTH);
			assert(!r.header_valid && !r.header_length);
			assert(!r.rx_setup && !r.rx_complete && !r.staging_bytes);
		} else {
			assert(strstr(last_log, "gate=header-length"));
			assert(strstr(last_log, "header_valid=1"));
			assert(r.protocol_refusal == MT6797_HIF_RX_REFUSAL_HEADER);
			assert(r.header_valid && r.header_length == (length + delta));
			assert(r.rx_setup && r.rx_complete && r.staging_bytes);
		}
		assert(strstr(last_log, "post_valid=0 post_wrplr=0x00000000"));
#ifdef TEST_REFUSED_TYPE
		assert(strstr(last_log, r.refused_type_valid ?
			"refused_type_valid=1 refused_type_word=0xe000" :
			"refused_type_valid=0 refused_type_word=0x0000"));
#endif
	} else {
		assert(r.protocol_refusal == MT6797_HIF_RX_REFUSAL_NONE);
		assert(!r.header_valid && !r.header_length && !r.selected_length);
	}
#endif
	if (rc == -EPROTO) {
		struct mt6797_hif_rx_result again;
		unsigned int calls = mock.calls;
		int retry;

		/* Test the poisoned owner, not a radio retry: no further transport
		 * call or second refusal report can occur on this context.
		 */
		retry = mt6797_hif_receive_packet(h, port, 1000001000ULL,
						buffer, sizeof(buffer), &again);
		assert(retry == -EIO && mock.calls == calls);
		assert(!again.pre_valid && !again.rx_setup && !again.rx_complete &&
		       !again.post_valid && !again.logical_bytes && !again.packet_type);
#ifdef TEST_METADATA
		assert(!again.header_valid && again.protocol_refusal == MT6797_HIF_RX_REFUSAL_NONE);
#endif
#ifdef TEST_REFUSED_TYPE
		assert(!again.refused_type_valid && !again.refused_type_word);
#endif
		for (size_t i = 0; i < sizeof(buffer); i++)
			assert(buffer[i] == 0x5a);
#ifdef TEST_METADATA
		logged_refusal(retry, port, again);
		assert(log_lines == 1);
#endif
	}
	/* Parent/child byte-identical table proves no extra transport operations. */
	printf("port=%u length=%u delta=%u fail=%u ret=%d calls=%u setup=%u complete=%u first=%d\n",
	       port, length, delta, fail_at, rc, mock.calls, r.rx_setup,
	       r.rx_complete, h->first_error);
	mt6797_hif_free(h);
	free(mock.base);
	return mock.calls;
}

int main(void)
{
	baseline_main();
	for (unsigned int p = 0; p < 2; p++) {
		unsigned int calls;

		check(p, 0, 0, ~0U, -EAGAIN);
		check(p, 1, 0, ~0U, -EPROTO);
		check(p, 3, 0, ~0U, -EPROTO);
		check(p, 2353, 0, ~0U, -EPROTO);
		check(p, 65535, 0, ~0U, -EPROTO);
		check(p, 4, 0, ~0U, 0);
		check(p, 2352, 0, ~0U, 0);
		check(p, 20, 1, ~0U, -EPROTO);
		check(p, 20, 256, ~0U, -EPROTO);
		/* CCMP3 76/28 and ND6 80/32: synthetic staged headers, not proof
		 * of the runtime packet family or producer cause. Equality stays strict.
		 */
		check(p, 76, (unsigned int)-48, ~0U, -EPROTO);
		check(p, 80, (unsigned int)-48, ~0U, -EPROTO);
		check(p, 76, 0, ~0U, 0);
		check(p, 80, 0, ~0U, 0);
		/* CCMP4 lengths; the fixture's type word remains synthetic. */
		check(p, 449, (unsigned int)-48, ~0U, -EPROTO);
		check(p, 449, 0, ~0U, 0);
		calls = check(p, 20, 0, ~0U, 0);
		for (unsigned int f = 1; f <= calls; f++)
			check(p, 20, 0, f, -EIO);
	}
	return 0;
}
